import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.parsers import MultiPartParser, FormParser
from .models import Feed, FeedReaction
from .serializers import FeedSerializer, FeedReactionSerializer
from users.models import User
from .serializers import FeedShareSerializer
from .models import FeedShare

logger = logging.getLogger(__name__)

class FeedCreateView(APIView):
    permission_classes = [IsAdminUser]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        logger.debug(f"User {request.user} creating feed with data: {request.data}")
        serializer = FeedSerializer(data=request.data)
        if serializer.is_valid():
            feed = serializer.save(posted_by=request.user)
            logger.info(f"Feed {feed.id} created by {request.user.username}")
            return Response(FeedSerializer(feed).data, status=status.HTTP_201_CREATED)
        logger.error(f"Feed creation failed: {serializer.errors}")
        return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

class FeedListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        device_id = request.query_params.get('device_id') or request.META.get('HTTP_DEVICE_ID')
        feeds = Feed.objects.all().order_by('-created_at')

        # Increment impressions for authenticated or anonymous users
        if request.user.is_authenticated:
            user = request.user
        else:
            if not device_id:
                logger.warning("Missing device_id in FeedListView")
            else:
                user = User.objects.filter(device_id=device_id).first()
                if not user:
                    logger.info(f"No user found for device_id: {device_id}")
                else:
                    # Increment impressions only for feeds with no reactions from this user
                    feeds_to_update = feeds.exclude(reactions__user=user)
                    for feed in feeds_to_update:
                        feed.impressions += 1
                        feed.save()
                        FeedReaction.objects.create(
                            feed=feed,
                            user=user,
                            reaction_type='viewed'
                        )
                    logger.debug(f"Updated impressions for {feeds_to_update.count()} feeds for user {user.username}")

        institution_id = request.query_params.get('institution')
        if institution_id:
            feeds = feeds.filter(institution__id=institution_id)

        serializer = FeedSerializer(feeds, many=True)
        logger.debug(f"Returning {len(serializer.data)} feeds")
        return Response(serializer.data, status=status.HTTP_200_OK)

class FeedReactionView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, feed_id):
        try:
            feed = Feed.objects.get(id=feed_id)
        except Feed.DoesNotExist:
            logger.error(f"Feed {feed_id} not found")
            return Response({"errors": {"feed": "Feed not found"}}, status=status.HTTP_404_NOT_FOUND)

        device_id = request.data.get('device_id') or request.META.get('HTTP_DEVICE_ID')
        if request.user.is_authenticated:
            user = request.user
        else:
            if not device_id:
                logger.warning("Missing device_id in FeedReactionView")
                return Response({"errors": {"device_id": "Device ID required"}}, status=status.HTTP_400_BAD_REQUEST)
            user = User.objects.filter(device_id=device_id).first()
            if not user:
                user = User.objects.create(
                    device_id=device_id,
                    username=f"anon_{device_id[:8]}",
                    user_type="anonymous"
                )
                logger.info(f"Created anonymous user for device_id: {device_id}")

        reaction_type = request.data.get('reaction_type')
        if reaction_type not in ['like', 'love', 'cry', 'smile']:
            logger.warning(f"Invalid reaction_type {reaction_type} for feed {feed_id}")
            return Response({"errors": {"reaction_type": "Invalid reaction type"}}, status=status.HTTP_400_BAD_REQUEST)

        # Remove all existing reactions for this user on this feed
        FeedReaction.objects.filter(feed=feed, user=user).delete()

        # Create new reaction
        reaction = FeedReaction.objects.create(
            feed=feed,
            user=user,
            reaction_type=reaction_type
        )
        logger.info(f"Reaction {reaction_type} added by {user.username} to feed {feed_id}")
        return Response(FeedReactionSerializer(reaction).data, status=status.HTTP_201_CREATED)


class FeedShareView(APIView):
    """Allow users (authenticated or anonymous via device_id) to share a feed.

    Creating a share will increment any relevant counters and return the share object.
    """
    permission_classes = [AllowAny]

    def post(self, request, feed_id):
        try:
            feed = Feed.objects.get(id=feed_id)
        except Feed.DoesNotExist:
            logger.error(f"Feed {feed_id} not found for sharing")
            return Response({"errors": {"feed": "Feed not found"}}, status=status.HTTP_404_NOT_FOUND)

        device_id = request.data.get('device_id') or request.META.get('HTTP_DEVICE_ID')
        if request.user.is_authenticated:
            user = request.user
        else:
            if not device_id:
                logger.warning("Missing device_id in FeedShareView")
                return Response({"errors": {"device_id": "Device ID required"}}, status=status.HTTP_400_BAD_REQUEST)
            user = User.objects.filter(device_id=device_id).first()
            if not user:
                user = User.objects.create(
                    device_id=device_id,
                    username=f"anon_{device_id[:8]}",
                    user_type="anonymous"
                )
                logger.info(f"Created anonymous user for device_id: {device_id}")

        message = request.data.get('message')

        share = FeedShare.objects.create(
            feed=feed,
            user=user,
            message=message
        )
        logger.info(f"Feed {feed_id} shared by {user.username}")
        return Response(FeedShareSerializer(share).data, status=status.HTTP_201_CREATED)

class FeedDeleteView(APIView):
    permission_classes = [IsAdminUser]

    def delete(self, request, feed_id):
        logger.debug(f"User {request.user} attempting to delete feed {feed_id}")
        try:
            feed = Feed.objects.get(id=feed_id)
            feed.delete()
            logger.info(f"Feed {feed_id} deleted by {request.user}")
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Feed.DoesNotExist:
            logger.error(f"Feed {feed_id} not found")
            return Response({"errors": {"feed": "Feed not found"}}, status=status.HTTP_404_NOT_FOUND)