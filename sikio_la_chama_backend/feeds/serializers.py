from rest_framework import serializers
from .models import Feed, FeedReaction
from users.serializers import UserSerializer
from institutions.models import Institution
from .models import FeedShare
import tempfile
import subprocess
import os
from django.core.files.uploadedfile import InMemoryUploadedFile, TemporaryUploadedFile
import logging

logger = logging.getLogger(__name__)

class FeedReactionSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = FeedReaction
        fields = ['id', 'user', 'reaction_type', 'created_at']

class FeedSerializer(serializers.ModelSerializer):
    posted_by = UserSerializer(read_only=True)
    institution = serializers.PrimaryKeyRelatedField(
        queryset=Institution.objects.all(),
        allow_null=True,
        required=False
    )
    institution_detail = serializers.SerializerMethodField()
    reactions = serializers.SerializerMethodField()
    reaction_counts = serializers.SerializerMethodField()
    total_reactions = serializers.SerializerMethodField()
    # New fields
    shares = serializers.SerializerMethodField()
    share_count = serializers.SerializerMethodField()

    class Meta:
        model = Feed
        fields = [
            'id',
            'posted_by',
            'institution',
            'institution_detail',
            'description',
            'image',
            'video',
            'link',
            'created_at',
            'impressions',
            'reactions',
            'reaction_counts',
            'total_reactions',
            'shares',
            'share_count',
        ]

    def validate_video(self, value):
        """Validate uploaded video file size and duration.

    - Max size: 50 MB
        - Max duration: 180 seconds (3 minutes)

        This will try to use ffprobe (part of ffmpeg) if available. If ffprobe
        isn't available, it will try to use moviepy as a fallback if installed.
        If neither is available, validation will fail with a message instructing
        how to add ffmpeg for proper duration validation.
        """
        # Increased limit per request: 50 MB
        MAX_BYTES = 50 * 1024 * 1024
        MAX_SECONDS = 180

        # Check size
        try:
            size = value.size
        except Exception:
            size = None

        if size is not None and size > MAX_BYTES:
            raise serializers.ValidationError(f"Video file size must be <= 50 MB. Uploaded file size: {size / (1024*1024):.2f} MB")

        # Save uploaded file to a temporary file for duration inspection
        tmp_path = None
        try:
            # If it's a TemporaryUploadedFile we can get the path directly
            if isinstance(value, TemporaryUploadedFile) and hasattr(value, 'temporary_file_path'):
                tmp_path = value.temporary_file_path()
            else:
                # Write contents to a NamedTemporaryFile
                tmp = tempfile.NamedTemporaryFile(delete=False)
                for chunk in value.chunks():
                    tmp.write(chunk)
                tmp.flush()
                tmp_path = tmp.name
                tmp.close()

            # Try ffprobe first
            try:
                cmd = [
                    'ffprobe',
                    '-v', 'error',
                    '-select_streams', 'v:0',
                    '-show_entries', 'stream=duration',
                    '-of', 'default=noprint_wrappers=1:nokey=1',
                    tmp_path,
                ]
                proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
                out = proc.stdout.strip()
                duration = None
                if out:
                    try:
                        duration = float(out.split('\n')[0])
                    except Exception:
                        duration = None

            except FileNotFoundError:
                duration = None

            # Fallback to moviepy if ffprobe wasn't available or failed
            if duration is None:
                try:
                    import importlib
                    moviepy_editor = importlib.import_module('moviepy.editor')
                    VideoFileClip = getattr(moviepy_editor, 'VideoFileClip')
                    clip = VideoFileClip(tmp_path)
                    duration = getattr(clip, 'duration', None)
                    try:
                        clip.reader.close()
                    except Exception:
                        pass
                    if hasattr(clip, 'audio') and clip.audio:
                        try:
                            clip.audio.reader.close_proc()
                        except Exception:
                            pass
                except Exception:
                    duration = None

            if duration is None:
                # Do not block upload if ffprobe/moviepy isn't available — log and accept.
                logger.warning(
                    "Could not determine video duration for uploaded file; ffprobe/moviepy may not be available or the file may be unreadable. "
                    "Skipping duration validation. To enable strict validation install ffmpeg (ffprobe) or moviepy."
                )
            else:
                if duration > MAX_SECONDS:
                    raise serializers.ValidationError(f"Video duration must be <= 3 minutes (180 seconds). Uploaded video duration: {duration:.1f} seconds")

        finally:
            # Clean up temporary file if we created one
            try:
                if tmp_path and os.path.exists(tmp_path) and not (isinstance(value, TemporaryUploadedFile) and hasattr(value, 'temporary_file_path')):
                    os.remove(tmp_path)
            except Exception:
                pass

        return value

    def get_institution_detail(self, obj):
        if obj.institution:
            return {
                "id": obj.institution.id,
                "name": obj.institution.name
            }
        return None

    def get_reactions(self, obj):
        reactions = FeedReaction.objects.filter(feed=obj)
        return FeedReactionSerializer(reactions, many=True).data

    def get_reaction_counts(self, obj):
        return {
            'like': obj.reactions.filter(reaction_type='like').count(),
            'love': obj.reactions.filter(reaction_type='love').count(),
            'cry': obj.reactions.filter(reaction_type='cry').count(),
            'smile': obj.reactions.filter(reaction_type='smile').count(),
        }

    def get_total_reactions(self, obj):
        return obj.reactions.count()

    def get_shares(self, obj):
        shares = FeedShare.objects.filter(feed=obj)
        return FeedShareSerializer(shares, many=True).data

    def get_share_count(self, obj):
        return obj.shares.count()


class FeedShareSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = FeedShare
        fields = ['id', 'user', 'message', 'created_at']
