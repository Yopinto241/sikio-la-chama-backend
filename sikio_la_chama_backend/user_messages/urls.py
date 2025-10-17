from django.urls import path
from .views import (
    SendMessageView,
    MessageListView,
    ReplyMessageView,
    MessageFileView,
    ReplyFileView,
    ReplyListView,
    UpdateMessageStatusView,
    DeleteMessageView,
    InstitutionListView,
    DepartmentListView,
    MessageCountView,  # Ensure this view exists in views.py
)

urlpatterns = [
    path('send/', SendMessageView.as_view(), name='send_message'),
    path('list/', MessageListView.as_view(), name='message_list'),
    path('<int:message_id>/reply/', ReplyMessageView.as_view(), name='reply_message'),
    path('<int:message_id>/replies/', ReplyListView.as_view(), name='reply_list'),
    path('<int:message_id>/file/', MessageFileView.as_view(), name='message_file'),
    path('<int:message_id>/status/', UpdateMessageStatusView.as_view(), name='update_message_status'),
    path('<int:message_id>/', DeleteMessageView.as_view(), name='delete_message'),
    path('institutions/', InstitutionListView.as_view(), name='institution_list'),
    path('institutions/departments/', DepartmentListView.as_view(), name='department_list'),
    # per-institution detail/update for file permissions is handled by the
    # institutions app to avoid duplicate routing.
    path('count/', MessageCountView.as_view(), name='message_count'),
]