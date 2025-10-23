from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

from .models import Notification, PushDevice
from .serializers import NotificationSerializer, PushDeviceSerializer


class RegisterDeviceView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = PushDeviceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data['token']
        platform = serializer.validated_data.get('platform', 'android')
        active = serializer.validated_data.get('active', True)

        device, created = PushDevice.objects.update_or_create(
            token=token,
            defaults={'user': request.user, 'platform': platform, 'active': active},
        )
        return Response(PushDeviceSerializer(device).data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class NotificationsListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        unread_only = request.query_params.get('unread') == '1'
        qs = Notification.objects.filter(recipient=request.user)
        if unread_only:
            qs = qs.filter(read_at__isnull=True)
        serializer = NotificationSerializer(qs[:100], many=True)
        return Response(serializer.data)


class MarkNotificationReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        notif = get_object_or_404(Notification, pk=pk, recipient=request.user)
        notif.mark_read()
        return Response({'status': 'ok'})


class MarkAllReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        from django.utils import timezone
        Notification.objects.filter(recipient=request.user, read_at__isnull=True).update(read_at=timezone.now())
        return Response({'status': 'ok'})
