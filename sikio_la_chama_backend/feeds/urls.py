from django.urls import path
from .views import FeedCreateView, FeedListView, FeedReactionView, FeedDeleteView, FeedShareView

urlpatterns = [
    path('create/', FeedCreateView.as_view(), name='feed_create'),
    path('list/', FeedListView.as_view(), name='feed_list'),
    path('<int:feed_id>/react/', FeedReactionView.as_view(), name='feed_react'),
    path('<int:feed_id>/share/', FeedShareView.as_view(), name='feed_share'),
    path('<int:feed_id>/', FeedDeleteView.as_view(), name='feed_delete'),
]