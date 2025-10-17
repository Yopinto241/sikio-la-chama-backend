from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from .models import Announcement


User = get_user_model()


class AnnouncementAPITest(APITestCase):
    def setUp(self):
        # create admin user
        self.admin = User.objects.create_user(username='admin', password='adminpass', user_type='admin')
        self.client = APIClient()

    def test_preview_and_truncation(self):
        long_text = 'A' * 1024
        ann = Announcement.objects.create(title='Big', description=long_text)

        url = reverse('announcement-list')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()
        self.assertTrue(len(data) >= 1)
        item = data[0]
        # preview present and shorter than original
        self.assertIn('preview', item)
        self.assertIn('is_truncated', item)
        self.assertTrue(item['is_truncated'])
        self.assertLessEqual(len(item['preview']), 241)  # 240 + optional ellipsis

        # retrieve returns full description
        detail_url = reverse('announcement-detail', args=[ann.id])
        resp2 = self.client.get(detail_url)
        self.assertEqual(resp2.status_code, status.HTTP_200_OK)
        self.assertEqual(resp2.json().get('description'), long_text)

    def test_admin_crud_permissions(self):
        url = reverse('announcement-list')
        payload = {'title': 'New', 'description': 'x'}

        # anonymous cannot create
        resp = self.client.post(url, payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

        # admin can create
        self.client.login(username='admin', password='adminpass')
        resp2 = self.client.post(url, payload, format='json')
        self.assertEqual(resp2.status_code, status.HTTP_201_CREATED)
        ann_id = resp2.json().get('id')

        # admin can update
        detail_url = reverse('announcement-detail', args=[ann_id])
        resp3 = self.client.patch(detail_url, {'description': 'updated'}, format='json')
        self.assertEqual(resp3.status_code, status.HTTP_200_OK)

        # admin can delete
        resp4 = self.client.delete(detail_url)
        self.assertIn(resp4.status_code, (status.HTTP_204_NO_CONTENT, status.HTTP_200_OK))
