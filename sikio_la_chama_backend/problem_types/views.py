from django.shortcuts import render

# Create your views here.
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAdminUser
from .models import ProblemType
from .serializers import ProblemTypeSerializer

class ProblemTypeListView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        problem_types = ProblemType.objects.all()
        serializer = ProblemTypeSerializer(problem_types, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class ProblemTypeCreateView(APIView):
    permission_classes = [IsAdminUser]
    def post(self, request):
        serializer = ProblemTypeSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response({"error": serializer.errors, "message": "Kuna tatizo, jaribu tena"}, status=status.HTTP_400_BAD_REQUEST)