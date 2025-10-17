import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.permissions import IsAdminUser
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from .serializers import UserSerializer, RegisterSerializer
from .models import User
from django.db import utils as db_utils
from django.core.exceptions import SynchronousOnlyOperation

logger = logging.getLogger(__name__)

class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        logger.debug(f"RegisterView called with data: {request.data}")
        try:
            serializer = RegisterSerializer(data=request.data, context={'request': request})
            if serializer.is_valid():
                user = serializer.save()
                token, _ = Token.objects.get_or_create(user=user)
                logger.info(f"User {user.username} registered with device_id: {user.device_id}")
                return Response({
                    "user": UserSerializer(user).data,
                    "token": token.key
                }, status=status.HTTP_201_CREATED)
            logger.error(f"Registration failed: {serializer.errors}")
            return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        except (db_utils.OperationalError, SynchronousOnlyOperation) as e:
            logger.exception("Database error during registration")
            return Response({"errors": {"service": "Database unavailable"}}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except Exception as e:
            logger.exception("Unexpected error during registration")
            return Response({"errors": {"server": str(e)}}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        logger.debug(f"LoginView called with data: {request.data}")
        username = request.data.get('username')
        password = request.data.get('password')
        device_id = request.data.get('device_id')

        if not username and not device_id:
            logger.warning("Login attempt missing both username and device_id")
            return Response({"errors": {"credentials": "Username or device_id required"}}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = None
            if username and password:
                user = authenticate(request, username=username, password=password)
            elif device_id:
                user = User.objects.filter(device_id=device_id).first()
                if not user:
                    logger.info(f"No user found for device_id: {device_id}, creating anonymous user")
                    user = User.objects.create(
                        username=f"anon_{device_id[:8]}",
                        device_id=device_id,
                        user_type="anonymous"
                    )

            if user:
                token, _ = Token.objects.get_or_create(user=user)
                logger.info(f"User {user.username} logged in")
                return Response({
                    "user": UserSerializer(user).data,
                    "token": token.key
                }, status=status.HTTP_200_OK)
            logger.warning("Login failed: Invalid credentials")
            return Response({"errors": {"credentials": "Invalid credentials"}}, status=status.HTTP_401_UNAUTHORIZED)
        except (db_utils.OperationalError, SynchronousOnlyOperation) as e:
            logger.exception("Database error during login")
            return Response({"errors": {"service": "Database unavailable"}}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except Exception as e:
            logger.exception("Unexpected error during login")
            return Response({"errors": {"server": str(e)}}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            logger.debug(f"Fetching current user: {request.user}")
            serializer = UserSerializer(request.user)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except (db_utils.OperationalError, SynchronousOnlyOperation) as e:
            logger.exception("Database error fetching current user")
            return Response({"errors": {"service": "Database unavailable"}}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except Exception as e:
            logger.exception("Unexpected error fetching current user")
            return Response({"errors": {"server": str(e)}}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AdminCreateUserView(APIView):
    """
    Admin-only endpoint to create institution_user or department users
    """
    permission_classes = [IsAdminUser]

    def post(self, request):
        try:
            serializer = RegisterSerializer(data=request.data, context={'request': request})
            if serializer.is_valid():
                user = serializer.save()
                logger.info(f"Admin {request.user.username} created {user.user_type} {user.username}")
                return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)
            return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        except (db_utils.OperationalError, SynchronousOnlyOperation) as e:
            logger.exception("Database error during admin user creation")
            return Response({"errors": {"service": "Database unavailable"}}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except Exception as e:
            logger.exception("Unexpected error during admin user creation")
            return Response({"errors": {"server": str(e)}}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)