"""pyazo URL Configuration"""
from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin
from django.urls import path

from pyazo.views import accounts, core, download, upload, view

admin.site.index_title = 'Pyazo Admin'
admin.site.site_title = 'pyazo'

urlpatterns = [
    url(r'^$', core.IndexView.as_view(), name='index'),
    url(r'^admin/', admin.site.urls),
    url(r'^o/', include('oauth2_provider.urls', namespace='oauth2_provider')),
    url(r'^accounts/allauth/', include('allauth.urls')),
    url(r'^accounts/login/$', accounts.login, name='accounts-login'),
    url(r'^accounts/logout/$', accounts.logout, name='accounts-logout'),
    url(r'^download/win/$', download.client_windows, name='download_client_windows'),
    url(r'^download/sharex/$', download.sxcu, name='download-sxcu'),
    url(r'^download/macos/$', download.client_macos, name='download_client_macos'),
    # Legacy upload URL
    url(r'^gyazo\.php$', upload.UploadView.as_view(), name='upload'),
    url(r'^upload/$', upload.UploadView.as_view(), name='upload'),
    url(r'^upload/browser/$', upload.BrowserUploadView.as_view(), name='upload_browser'),
    url(r'^upload/(?P<file_hash>\w{128})/view/$',
        upload.UploadView.as_view(), name='upload_view'),
    url(r'^upload/(?P<file_hash>\w{128})/claim/$',
        upload.ClaimView.as_view(), name='upload_claim'),
    # All view URLs are handeled by the same Function, but we need different names
    # so the default can be changed in the settings
    url(r'^(?P<file_hash>\w{16})(\..{1,5})?$',
        view.UploadViewFile.as_view(), name='view_sha512_short'),
    url(r'^(?P<file_hash>\w{32})(\..{1,5})?$',
        view.UploadViewFile.as_view(), name='view_md5'),
    url(r'^(?P<file_hash>\w{64})(\..{1,5})?$',
        view.UploadViewFile.as_view(), name='view_sha256'),
    url(r'^(?P<file_hash>\w{128})(\..{1,5})?$',
        view.UploadViewFile.as_view(), name='view_sha512'),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns.append(path('__debug__/', include(debug_toolbar.urls)))
