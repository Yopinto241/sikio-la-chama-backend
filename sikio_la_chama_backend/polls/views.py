from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.shortcuts import get_object_or_404
from .models import Poll
from .serializers import PollSerializer, PollListSerializer, VoteCreateSerializer
from .permissions import IsPollAdmin
from rest_framework.pagination import PageNumberPagination

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
    def vote(self, request, pk=None):
        poll = get_object_or_404(Poll, pk=pk)
        serializer = VoteCreateSerializer(data=request.data, context={'poll': poll})
        serializer.is_valid(raise_exception=True)
        try:
            vote = serializer.create_vote(request)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        poll_ser = PollListSerializer(poll, context={'request': request})
        return Response({'detail': 'Vote recorded', 'poll': poll_ser.data}, status=status.HTTP_201_CREATED)