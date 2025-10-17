from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser, AllowAny
from .models import Announcement
from .serializers import AnnouncementSerializer

class AnnouncementViewSet(viewsets.ModelViewSet):
    queryset = Announcement.objects.all().order_by('-created_at')
    serializer_class = AnnouncementSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]  # Public access for GET
        return [IsAdminUser()]  # Admin-only for POST, PUT, DELETE