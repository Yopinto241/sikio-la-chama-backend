# feeds/admin.py
from django.contrib import admin
from .models import Feed, FeedReaction

@admin.register(Feed)
class FeedAdmin(admin.ModelAdmin):
    list_display = ['description', 'posted_by', 'impressions', 'created_at']
    list_filter = ['created_at', 'posted_by']
    search_fields = ['description', 'posted_by__username']
    readonly_fields = ['impressions', 'created_at']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('posted_by')

@admin.register(FeedReaction)
class FeedReactionAdmin(admin.ModelAdmin):
    list_display = ['feed', 'reaction_type', 'user', 'get_device_id', 'created_at']
    list_filter = ['reaction_type', 'created_at']
    search_fields = ['feed__description', 'user__username', 'device_id']

    def get_device_id(self, obj):
        return obj.device_id if obj.device_id else 'N/A'
    get_device_id.short_description = 'Device ID'
    get_device_id.admin_order_field = 'device_id'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('feed', 'user')