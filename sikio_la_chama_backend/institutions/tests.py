from django.test import TestCase
from rest_framework.test import APIClient
from user_messages.models import InstitutionFilePermission
from users.models import User
from institutions.models import Institution


class FilePermissionTests(TestCase):
	def setUp(self):
		# create admin user and institution
		self.admin = User.objects.create_user(username='admin', password='pass', user_type='admin', is_staff=True, is_superuser=True)
		self.institution = Institution.objects.create(name='Test Inst')
		self.client = APIClient()
		# create token and set header if project uses TokenAuthentication
		from rest_framework.authtoken.models import Token
		token, _ = Token.objects.get_or_create(user=self.admin)
		self.client.credentials(HTTP_AUTHORIZATION='Token ' + token.key)

	def test_patch_set_true(self):
		url = f'/api/institutions/{self.institution.id}/file-permissions/'
		resp = self.client.patch(url, {'allow_file': True}, format='json')
		self.assertEqual(resp.status_code, 200)
		perm = InstitutionFilePermission.objects.get(institution=self.institution)
		self.assertTrue(perm.allow_file)

	def test_patch_missing_flag_returns_400(self):
		url = f'/api/institutions/{self.institution.id}/file-permissions/'
		resp = self.client.patch(url, {}, format='json')
		self.assertEqual(resp.status_code, 400)

	def test_toggle_endpoint(self):
		url = f'/api/institutions/{self.institution.id}/file-permissions/toggle/'
		# initial is False
		resp = self.client.post(url, format='json')
		self.assertEqual(resp.status_code, 200)
		perm = InstitutionFilePermission.objects.get(institution=self.institution)
		self.assertTrue(perm.allow_file)
		# toggle back
		resp = self.client.post(url, format='json')
		self.assertEqual(resp.status_code, 200)
		perm.refresh_from_db()
		self.assertFalse(perm.allow_file)
