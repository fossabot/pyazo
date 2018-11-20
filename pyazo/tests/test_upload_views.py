"""test upload views"""
import os

from django.conf import settings
from django.contrib.auth.models import User
from django.shortcuts import reverse
from django.test import TestCase, override_settings

from pyazo.models import Collection, Upload
from pyazo.tests.utils import test_auth


class UploadViewTests(TestCase):
    """Test all client upload views"""

    def setUp(self):
        super().setUp()
        with open(settings.MEDIA_ROOT + 'test2.txt', 'w') as _file:
            _file.write('updating existing upload')
        self.upload = Upload.objects.create(file=settings.MEDIA_ROOT + 'test2.txt')
        with open(settings.MEDIA_ROOT + 'test3.txt', 'w') as _file:
            _file.write('updating qwerqwerqwer upload')

    def tearDown(self):
        super().tearDown()
        os.unlink(settings.MEDIA_ROOT + 'test2.txt')
        os.unlink(settings.MEDIA_ROOT + 'test3.txt')

    def test_upload_view(self):
        """Test UploadView"""
        self.client.login(**test_auth())
        response = self.client.get(reverse('upload_view', kwargs={'file_hash': self.upload.sha512}))
        self.assertEqual(response.status_code, 200)

    def test_upload_view_post(self):
        """Test UploadView's post"""
        auth = test_auth()
        self.client.login(**auth)
        test_user = User.objects.get(username=auth.get('username'))
        test_collection = Collection.objects.create(name='test', owner=test_user)
        form_data = {
            'collection': test_collection
        }
        response = self.client.post(
            reverse('upload_view', kwargs={'file_hash': self.upload.sha512}), data=form_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse(
            'upload_view', kwargs={'file_hash': self.upload.sha512}))

    def test_claim_view(self):
        """Test ClaimView"""
        self.client.login(**test_auth())
        response = self.client.get(reverse('upload_claim', kwargs={
            'file_hash': self.upload.sha512}))
        self.assertEqual(response.status_code, 200)

    def test_claim_view_post(self):
        """Test ClaimView"""
        self.client.login(**test_auth())
        response = self.client.post(reverse('upload_claim', kwargs={
            'file_hash': self.upload.sha512}))
        self.assertEqual(response.status_code, 302)
        self.client.login(**test_auth(superuser=False))
        response = self.client.post(reverse('upload_claim', kwargs={
            'file_hash': self.upload.sha512}))
        self.assertEqual(response.status_code, 302)

    def test_delete_view(self):
        """Test DeleteView"""
        self.client.login(**test_auth())
        response = self.client.get(reverse('upload_delete', kwargs={
            'file_hash': self.upload.sha512}))
        self.assertEqual(response.status_code, 200)

    def test_delete_view_post(self):
        """Test DeleteView's post"""
        self.client.login(**test_auth())
        response = self.client.post(reverse('upload_delete', kwargs={
            'file_hash': self.upload.sha512}))
        self.assertEqual(response.status_code, 302)

    def test_delete_view_invalid(self):
        """Test DeleteView's post but with invalid permissions"""
        self.client.login(**test_auth(superuser=False))
        response = self.client.post(reverse('upload_delete', kwargs={
            'file_hash': self.upload.sha512}))
        self.assertEqual(response.status_code, 302)

    @override_settings(AUTO_CLAIM_ENABLED=True)
    def test_legacy_upload(self):
        """Test legacy upload view"""
        test_auth()
        with open(settings.MEDIA_ROOT + 'test3.txt') as _file:
            response = self.client.post(reverse('upload'), data={
                'id': 'test', 'imagedata': _file, 'username': 'superuser'})
        self.assertEqual(response.status_code, 200)

    def test_legacy_upload_exist(self):
        """Test legacy upload view with existing file"""
        self.client.logout()
        with open(self.upload.file.path) as _file:
            response = self.client.post(reverse('upload'), data={'id': 'test', 'imagedata': _file})
        self.assertEqual(response.status_code, 200)

    def test_legacy_upload_invalid(self):
        """Test legacy upload view with invalid data"""
        response = self.client.post(reverse('upload'), data={})
        self.assertEqual(response.status_code, 400)

    def test_browser_upload(self):
        """Test browser upload"""
        self.client.login(**test_auth())
        with open(settings.MEDIA_ROOT + 'test3.txt') as _file:
            response = self.client.post(reverse('upload_browser'), data={'test': _file})
        self.assertEqual(response.status_code, 204)
