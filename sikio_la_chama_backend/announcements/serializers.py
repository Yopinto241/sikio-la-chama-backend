from rest_framework import serializers
from .models import Announcement

class AnnouncementSerializer(serializers.ModelSerializer):
    preview = serializers.SerializerMethodField(read_only=True)
    is_truncated = serializers.SerializerMethodField(read_only=True)

    PREVIEW_LENGTH = 240
    class Meta:
        model = Announcement
        fields = ['id', 'title', 'description', 'preview', 'is_truncated', 'created_at']
        read_only_fields = ['id', 'created_at', 'preview', 'is_truncated']

    def get_preview(self, obj):
        text = (obj.description or '')
        if len(text) <= self.PREVIEW_LENGTH:
            return text
        return text[:self.PREVIEW_LENGTH].rstrip() + '\u2026'  # ellipsis

    def get_is_truncated(self, obj):
        text = (obj.description or '')
        return len(text) > self.PREVIEW_LENGTH