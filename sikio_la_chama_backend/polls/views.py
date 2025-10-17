from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.shortcuts import get_object_or_404
from .models import Poll
from .serializers import PollSerializer, PollListSerializer, VoteCreateSerializer
from .permissions import IsPollAdmin
from rest_framework.pagination import PageNumberPagination
from asgiref.sync import sync_to_async

class StandardPagination(PageNumberPagination):
    page_size = 20

class PollViewSet(viewsets.ModelViewSet):
    queryset = Poll.objects.prefetch_related('options').order_by('-created_at')
    serializer_class = PollSerializer
    pagination_class = StandardPagination

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            permission_classes = [IsPollAdmin]
        else:
            permission_classes = [AllowAny]
        return [p() for p in permission_classes]

    def get_serializer_class(self):
        if self.action in ('list',):
            return PollListSerializer
        return PollSerializer

    @action(detail=True, methods=['post'], url_path='vote')
    async def vote(self, request, pk=None):
        # Run ORM and serializer operations in a thread to avoid calling
        # synchronous DB code from an async context.
        try:
            poll = await sync_to_async(get_object_or_404, thread_sensitive=True)(Poll, pk=pk)
            # serializer creation is synchronous but cheap; validation and
            # create_vote may touch the DB so wrap those calls.
            serializer = VoteCreateSerializer(data=request.data, context={'poll': poll})
            await sync_to_async(serializer.is_valid, thread_sensitive=True)(raise_exception=True)
            try:
                vote = await sync_to_async(serializer.create_vote, thread_sensitive=True)(request)
            except Exception as e:
                return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

            # Serializing the updated poll may access related objects; run in thread.
            def _serialize_poll():
                return PollListSerializer(poll, context={'request': request}).data

            poll_ser_data = await sync_to_async(_serialize_poll, thread_sensitive=True)()
            return Response({'detail': 'Vote recorded', 'poll': poll_ser_data}, status=status.HTTP_201_CREATED)
        except Exception as e:
            # surface a helpful error if async/DB boundaries are still violated
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)