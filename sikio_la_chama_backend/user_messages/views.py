import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAdminUser
from .models import Message, Reply  # removed InstitutionFilePermission import
from .serializers import MessageSerializer, ReplySerializer  # removed InstitutionFilePermissionSerializer
from users.models import User
from institutions.models import Institution, Department
from django.http import FileResponse, Http404
import mimetypes
import os
from rest_framework.pagination import PageNumberPagination

logger = logging.getLogger(__name__)

class SendMessageView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        device_id = request.data.get("device_id") or request.META.get("HTTP_DEVICE_ID")
        if not device_id:
            logger.warning("Missing device_id in SendMessageView")
            return Response({"errors": {"device_id": "Device ID is required"}}, status=status.HTTP_400_BAD_REQUEST)
        if request.user.is_authenticated:
            sender = request.user
        else:
            sender = User.objects.filter(device_id=device_id).first()
            if not sender:
                sender = User.objects.create(
                    device_id=device_id,
                    username=f"anon_{device_id[:8]}",
                    user_type="anonymous"
                )
                logger.info(f"Created anonymous user for device_id: {device_id}")

        serializer = MessageSerializer(data=request.data, context={'request': request, 'device_user': sender})
        if not serializer.is_valid():
            logger.error(f"Serializer errors in SendMessageView: {serializer.errors}")
            return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        message = serializer.save(sender=sender)
        logger.info(f"Message {message.id} created by {sender.username}")
        return Response(MessageSerializer(message, context={'request': request, 'device_user': sender}).data, status=status.HTTP_201_CREATED)


class MessageListView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        device_id = request.query_params.get("device_id") or request.META.get("HTTP_DEVICE_ID")
        user = request.user
        messages = Message.objects.all().order_by("-timestamp")

        if user.is_authenticated and user.user_type in ["admin", "department", "institution_user"]:
            if user.user_type == "department":
                messages = messages.filter(department=user.department)
            elif user.user_type == "institution_user":
                messages = messages.filter(institution=user.institution)
        else:
            if not device_id:
                logger.warning("Missing device_id in MessageListView")
                return Response({"errors": {"device_id": "Device ID required"}}, status=status.HTTP_400_BAD_REQUEST)
            sender = User.objects.filter(device_id=device_id).first()
            if not sender:
                logger.info(f"No user found for device_id: {device_id}")
                return Response([], status=status.HTTP_200_OK)
            messages = messages.filter(sender=sender)

        institution_id = request.query_params.get('institution')
        department_id = request.query_params.get('department')
        if institution_id:
            messages = messages.filter(institution__id=institution_id)
        if department_id:
            messages = messages.filter(department__id=department_id)

        device_user = None
        if not request.user.is_authenticated and device_id:
            device_user = User.objects.filter(device_id=device_id).first()

        serializer = MessageSerializer(messages, many=True, context={'request': request, 'device_user': device_user})
        logger.debug(f"Returning {len(serializer.data)} messages")
        return Response(serializer.data, status=status.HTTP_200_OK)


class ReplyMessageView(APIView):
    permission_classes = [AllowAny]
    def post(self, request, message_id):
        try:
            message = Message.objects.get(id=message_id)
        except Message.DoesNotExist:
            logger.error(f"Message {message_id} not found in ReplyMessageView")
            return Response({"errors": {"message": "Message not found"}}, status=status.HTTP_404_NOT_FOUND)

        device_id = request.data.get("device_id") or request.META.get("HTTP_DEVICE_ID")
        if request.user.is_authenticated:
            sender = request.user
        else:
            sender = User.objects.filter(device_id=device_id).first()
            if not sender:
                sender = User.objects.create(
                    device_id=device_id,
                    username=f"anon_{device_id[:8]}",
                    user_type="anonymous"
                )
                logger.info(f"Created anonymous user for device_id: {device_id}")

        if sender.user_type == "anonymous" and message.sender != sender:
            logger.warning(f"Anonymous user {sender.username} attempted to reply to message {message_id}")
            return Response({"errors": {"permission": "Cannot reply to this message"}}, status=status.HTTP_403_FORBIDDEN)

        serializer = ReplySerializer(data=request.data, context={'request': request, 'device_user': sender})
        if not serializer.is_valid():
            logger.error(f"Serializer errors in ReplyMessageView: {serializer.errors}")
            return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        reply = serializer.save(sender=sender, message=message)

        if sender.user_type == "admin" and message.status == "pending":
            message.status = "answered"
            message.save()
            logger.info(f"Message {message_id} status updated to answered by admin {sender.username}")

        logger.info(f"Reply {reply.id} created for message {message_id} by {sender.username}")
        return Response(ReplySerializer(reply, context={'request': request, 'device_user': sender}).data, status=status.HTTP_201_CREATED)


class ReplyListView(APIView):
    permission_classes = [AllowAny]
    def get(self, request, message_id):
        try:
            message = Message.objects.get(id=message_id)
        except Message.DoesNotExist:
            return Response({"errors": {"message": "Message not found"}}, status=status.HTTP_404_NOT_FOUND)

        device_id = request.query_params.get('device_id') or request.META.get('HTTP_DEVICE_ID')
        requester = request.user if request.user.is_authenticated else None
        if not requester and device_id:
            requester = User.objects.filter(device_id=device_id).first()

        if requester == message.sender:
            from django.db.models import Q
            qs = message.replies.filter(Q(sender=message.sender) | Q(sender__user_type__in=['admin', 'institution_user', 'department']))
        elif requester and getattr(requester, 'user_type', None) in ['admin', 'institution_user', 'department']:
            if requester.user_type == 'department' and requester.department != message.department:
                return Response({"errors": {"permission": "Forbidden"}}, status=status.HTTP_403_FORBIDDEN)
            if requester.user_type == 'institution_user' and requester.institution != message.institution:
                return Response({"errors": {"permission": "Forbidden"}}, status=status.HTTP_403_FORBIDDEN)
            qs = message.replies.all()
        else:
            qs = message.replies.none()

        qs = qs.order_by('timestamp')
        paginator = PageNumberPagination()
        paginator.page_size = 20
        page = paginator.paginate_queryset(qs, request)
        serializer = ReplySerializer(page, many=True, context={'request': request, 'device_user': requester})
        return paginator.get_paginated_response(serializer.data)


class MessageFileView(APIView):
    """Serve message file: owner or staff (admin/institution_user/department in same scope)"""
    permission_classes = [AllowAny]

    def get(self, request, message_id):
        try:
            message = Message.objects.get(id=message_id)
        except Message.DoesNotExist:
            return Response({"errors": {"message": "Message not found"}}, status=status.HTTP_404_NOT_FOUND)

        device_id = request.query_params.get('device_id') or request.META.get('HTTP_DEVICE_ID')
        requester = request.user if request.user.is_authenticated else None
        if not requester and device_id:
            requester = User.objects.filter(device_id=device_id).first()

        # owner always allowed
        if requester == message.sender:
            if not message.file:
                return Response({"errors": {"file": "No file attached"}}, status=status.HTTP_404_NOT_FOUND)
            file_path = message.file.path
            if not os.path.exists(file_path):
                raise Http404
            preview = request.query_params.get('preview', 'false').lower() in ['1', 'true', 'yes']
            content_type, _ = mimetypes.guess_type(file_path)
            response = FileResponse(open(file_path, 'rb'), content_type=content_type or 'application/octet-stream')
            if preview:
                response['Content-Disposition'] = 'inline; filename="%s"' % os.path.basename(file_path)
            else:
                response['Content-Disposition'] = 'attachment; filename="%s"' % os.path.basename(file_path)
            return response

        # staff in same scope may access
        if requester and getattr(requester, 'user_type', None) in ['admin', 'institution_user', 'department']:
            if requester.user_type == 'department' and requester.department != message.department:
                return Response({"errors": {"permission": "Forbidden"}}, status=status.HTTP_403_FORBIDDEN)
            if requester.user_type == 'institution_user' and requester.institution != message.institution:
                return Response({"errors": {"permission": "Forbidden"}}, status=status.HTTP_403_FORBIDDEN)
            if not message.file:
                return Response({"errors": {"file": "No file attached"}}, status=status.HTTP_404_NOT_FOUND)
            file_path = message.file.path
            if not os.path.exists(file_path):
                raise Http404
            preview = request.query_params.get('preview', 'false').lower() in ['1', 'true', 'yes']
            content_type, _ = mimetypes.guess_type(file_path)
            response = FileResponse(open(file_path, 'rb'), content_type=content_type or 'application/octet-stream')
            if preview:
                response['Content-Disposition'] = 'inline; filename="%s"' % os.path.basename(file_path)
            else:
                response['Content-Disposition'] = 'attachment; filename="%s"' % os.path.basename(file_path)
            return response

        return Response({"errors": {"permission": "Forbidden"}}, status=status.HTTP_403_FORBIDDEN)


class ReplyFileView(APIView):
    """Serve reply file: owner or staff (admin/institution_user/department in same scope)"""
    permission_classes = [AllowAny]

    def get(self, request, reply_id):
        try:
            reply = Reply.objects.get(id=reply_id)
        except Reply.DoesNotExist:
            return Response({"errors": {"reply": "Reply not found"}}, status=status.HTTP_404_NOT_FOUND)

        device_id = request.query_params.get('device_id') or request.META.get('HTTP_DEVICE_ID')
        requester = request.user if request.user.is_authenticated else None
        if not requester and device_id:
            requester = User.objects.filter(device_id=device_id).first()

        if requester == reply.sender:
            if not reply.file:
                return Response({"errors": {"file": "No file attached"}}, status=status.HTTP_404_NOT_FOUND)
            file_path = reply.file.path
            if not os.path.exists(file_path):
                raise Http404
            preview = request.query_params.get('preview', 'false').lower() in ['1', 'true', 'yes']
            content_type, _ = mimetypes.guess_type(file_path)
            response = FileResponse(open(file_path, 'rb'), content_type=content_type or 'application/octet-stream')
            if preview:
                response['Content-Disposition'] = 'inline; filename="%s"' % os.path.basename(file_path)
            else:
                response['Content-Disposition'] = 'attachment; filename="%s"' % os.path.basename(file_path)
            return response

        # staff in same scope may access
        if requester and getattr(requester, 'user_type', None) in ['admin', 'institution_user', 'department']:
            if requester.user_type == 'department' and requester.department != reply.message.department:
                return Response({"errors": {"permission": "Forbidden"}}, status=status.HTTP_403_FORBIDDEN)
            if requester.user_type == 'institution_user' and requester.institution != reply.message.institution:
                return Response({"errors": {"permission": "Forbidden"}}, status=status.HTTP_403_FORBIDDEN)
            if not reply.file:
                return Response({"errors": {"file": "No file attached"}}, status=status.HTTP_404_NOT_FOUND)
            file_path = reply.file.path
            if not os.path.exists(file_path):
                raise Http404
            preview = request.query_params.get('preview', 'false').lower() in ['1', 'true', 'yes']
            content_type, _ = mimetypes.guess_type(file_path)
            response = FileResponse(open(file_path, 'rb'), content_type=content_type or 'application/octet-stream')
            if preview:
                response['Content-Disposition'] = 'inline; filename="%s"' % os.path.basename(file_path)
            else:
                response['Content-Disposition'] = 'attachment; filename="%s"' % os.path.basename(file_path)
            return response

        return Response({"errors": {"permission": "Forbidden"}}, status=status.HTTP_403_FORBIDDEN)


class UpdateMessageStatusView(APIView):
    permission_classes = [IsAdminUser]
    def patch(self, request, message_id):
        logger.debug(f"User {request.user} attempting to update message {message_id}")
        try:
            message = Message.objects.get(id=message_id)
        except Message.DoesNotExist:
            logger.error(f"Message {message_id} not found")
            return Response({"errors": {"message": "Message not found"}}, status=status.HTTP_404_NOT_FOUND)

        status_value = request.data.get("status")
        if status_value in ["pending", "answered", "solved", "help_received"]:
            message.status = status_value
            message.save()
            logger.info(f"Message {message_id} status updated to {status_value} by {request.user}")
            return Response(MessageSerializer(message).data, status=status.HTTP_200_OK)

        logger.warning(f"Invalid status {status_value} for message {message_id}")
        return Response({"errors": {"status": "Invalid status"}}, status=status.HTTP_400_BAD_REQUEST)


class DeleteMessageView(APIView):
    permission_classes = [IsAdminUser]
    def delete(self, request, message_id):
        logger.debug(f"User {request.user} attempting to delete message {message_id}")
        try:
            message = Message.objects.get(id=message_id)
            message.delete()
            logger.info(f"Message {message_id} deleted by {request.user}")
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Message.DoesNotExist:
            logger.error(f"Message {message_id} not found")
            return Response({"errors": {"message": "Message not found"}}, status=status.HTTP_404_NOT_FOUND)


class InstitutionListView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        institutions = Institution.objects.all()
        logger.debug(f"Returning {institutions.count()} institutions")
        return Response([{'id': inst.id, 'name': inst.name} for inst in institutions], status=status.HTTP_200_OK)


class DepartmentListView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        institution_id = request.query_params.get('institution')
        departments = Department.objects.all()
        if institution_id:
            departments = departments.filter(institution_id=institution_id)
        logger.debug(f"Returning {departments.count()} departments")
        return Response([{'id': dept.id, 'name': dept.name, 'institution_id': dept.institution.id} for dept in departments], status=status.HTTP_200_OK)


class MessageCountView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        device_id = request.query_params.get('device_id')
        if not device_id:
            logger.warning("Missing device_id in MessageCountView")
            return Response(
                {"error": "device_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = User.objects.filter(device_id=device_id).first()
        if not user:
            logger.info(f"No user found for device_id: {device_id}")
            return Response(
                {"error": "User not found for the given device_id"},
                status=status.HTTP_404_NOT_FOUND
            )

        message_count = Message.objects.filter(sender=user).count()
        logger.debug(f"Returning message count {message_count} for device_id: {device_id}")
        return Response({"count": message_count}, status=status.HTTP_200_OK)