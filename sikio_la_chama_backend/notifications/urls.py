from django.urls import path
from .views import RegisterDeviceView, NotificationsListView, MarkNotificationReadView, MarkAllReadView


urlpatterns = [
    path('devices/register/', RegisterDeviceView.as_view(), name='register-device'),
    path('', NotificationsListView.as_view(), name='notifications-list'),
    path('<int:pk>/read/', MarkNotificationReadView.as_view(), name='notification-read'),
    path('read-all/', MarkAllReadView.as_view(), name='notifications-read-all'),
]

