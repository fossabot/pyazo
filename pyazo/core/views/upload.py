"""pyazo upload views"""
import os
from logging import getLogger
from typing import Tuple
from urllib.parse import urljoin

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext as _
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView, View

from pyazo.core.forms.view import CollectionSelectForm
from pyazo.core.models import Collection, Upload
from pyazo.utils.files import generate_hashes, save_from_post
from pyazo.core.views.view import UploadViewFile

LOGGER = getLogger(__name__)


class UploadView(LoginRequiredMixin, TemplateView):
    """Show statistics about upload and allow user to manage it."""

    template_name = 'upload/view.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        upload = get_object_or_404(Upload, sha512=self.kwargs.get('file_hash'))
        context['upload'] = upload
        context['url_prefix'] = self.request.build_absolute_uri('/')
        context['views'] = context['upload'].uploadview_set.order_by('-viewee_date')[:10]
        context['forms'] = {
            'collection': CollectionSelectForm(
                prefix='collection',
                initial={
                    'collection': upload.collection
                },
                data=self.request.POST if any(
                    'collection' in k for k in self.request.POST.keys()) else None
            )
        }
        # Prepare Collections
        collections = Collection.objects.filter(owner=self.request.user)
        context['forms']['collection'].fields['collection'].queryset = collections
        return context

    def post(self, request: HttpRequest, file_hash: str) -> HttpResponse:
        """handle form"""
        context = self.get_context_data()
        upload = get_object_or_404(Upload, sha512=file_hash)
        form = context.get('forms').get('collection')
        if form.is_valid():
            upload.collection = form.cleaned_data.get('collection')
            upload.save()
        return redirect(reverse('upload_view', kwargs={'file_hash': file_hash}))


class ClaimUploadView(LoginRequiredMixin, TemplateView):
    """Claim an upload"""

    template_name = 'core/generic_delete.html'

    def post(self, request: HttpRequest, file_hash: str) -> HttpResponse:
        """Claim upload to user (only if upload has no owner yet or user is superuser)"""
        upload = get_object_or_404(Upload, sha512=file_hash)
        if request.user.is_superuser or not upload.user:
            upload.user = request.user
            upload.save()
            messages.success(request, _('Upload successfully claimed'))
        else:
            messages.warning(request, _('Permission denied'))
        return redirect(reverse('upload_view', kwargs={'file_hash': file_hash}))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        upload = get_object_or_404(Upload, sha512=self.kwargs.get('file_hash'))
        context['object'] = 'Upload %s' % upload.md5
        context['delete_url'] = reverse('upload_claim', kwargs={
            'file_hash': self.kwargs.get('file_hash')
        }),
        context['action'] = _('claim')
        context['primary_action'] = _('Confirm Claim')
        return context


class DeleteUploadView(LoginRequiredMixin, TemplateView):
    """Delete Upload"""

    template_name = 'core/generic_delete.html'

    def post(self, request: HttpRequest, file_hash: str) -> HttpResponse:
        """Delete upload"""
        upload = get_object_or_404(Upload, sha512=file_hash)
        if request.user.is_superuser or upload.user == request.user:
            upload.delete()
            messages.success(request, _('Upload successfully deleted'))
        else:
            messages.warning(request, _('Permission denied'))
        return redirect(reverse('index'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        upload = get_object_or_404(Upload, sha512=self.kwargs.get('file_hash'))
        context['object'] = 'Upload %s' % upload.md5
        context['delete_url'] = reverse('upload_delete', kwargs={
            'file_hash': self.kwargs.get('file_hash')
        })
        return context


@method_decorator(csrf_exempt, name='dispatch')
class LegacyUploadView(View):
    """Legacy Upload (for gyazo-based clients)"""

    def post(self, request: HttpRequest) -> HttpResponse:
        """Main upload handler. Fully gyazo compatible."""
        if 'id' in request.POST and 'imagedata' in request.FILES:
            # Instantiate BrowserUploadView to use handle_post_file
            upload_view = BrowserUploadView()
            upload, created = upload_view.handle_post_file(request.FILES['imagedata'])
            if created:
                # Run auto-claim
                if settings.AUTO_CLAIM_ENABLED and 'username' in request.POST:
                    matching = User.objects.filter(username=request.POST.get('username'))
                    if matching.exists():
                        upload.user = matching.first()
                        LOGGER.debug("Auto-claimed upload to user '%s'",
                                     request.POST.get('username'))
                upload.save()
                # Count initial view
                UploadViewFile.count_view(upload, request)
                LOGGER.info("Uploaded %s", upload.filename)
            # Generate url for client to open
            upload_prop = settings.DEFAULT_RETURN_VIEW.replace('view_', '')
            upload_hash = getattr(upload, upload_prop, 'sha256')
            url = reverse(settings.DEFAULT_RETURN_VIEW, kwargs={'file_hash': upload_hash})
            full_url = urljoin(settings.EXTERNAL_URL, url)
            return HttpResponse(full_url)
        return HttpResponse(status=400)


class BrowserUploadView(LoginRequiredMixin, TemplateView):
    """Handle uploads from browser"""

    template_name = 'upload/upload.html'

    def handle_post_file(self, post_file) -> Tuple[Upload, bool]:
        """Handle upload of a single file, computes hashes and returns existing Upload instance and
        False as tuple if file was uploaded already.
        Otherwise, new Upload instance is created and returned in a tuple with True."""
        _, ext = os.path.splitext(post_file.name)
        # Remove leading dot from extension
        ext = ext[1:] if ext.startswith('.') else ext
        # Generate hashes first to check if upload exists already
        hashes = generate_hashes(post_file)
        # Reset reading position so we can read the file again
        post_file.seek(0)
        # Check if hashes already exists
        existing = Upload.objects.filter(sha512=hashes.get('sha512'))
        if existing.exists():
            LOGGER.debug("De-duped existing upload %s", existing.first().filename)
            return existing.first(), False
        # Create new upload object
        new_upload = Upload(
            file=save_from_post(post_file.read(), extension=ext))
        new_upload.save()
        LOGGER.info("Uploaded %s", new_upload.filename)
        return new_upload, True

    def post(self, request: HttpRequest) -> HttpResponse:
        """Create Upload objects from request"""
        for __, _file in request.FILES.items():
            new_upload, _created = self.handle_post_file(_file)
            new_upload.user = request.user
            new_upload.save()
            # Count initial view
            UploadViewFile.count_view(new_upload, request)
            LOGGER.info("Uploaded %s", new_upload.filename)
        return HttpResponse(status=204)