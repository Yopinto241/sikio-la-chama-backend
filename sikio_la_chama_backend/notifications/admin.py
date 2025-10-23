from django.contrib import admin
from .models import Notification, PushDevice


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'recipient', 'title', 'type', 'created_at', 'read_at')
    list_filter = ('type', 'created_at', 'read_at')
    search_fields = ('title', 'body', 'recipient__username')


@admin.register(PushDevice)
class PushDeviceAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'platform', 'active', 'created_at')
    list_filter = ('platform', 'active', 'created_at')
    search_fields = ('token', 'user__username')

