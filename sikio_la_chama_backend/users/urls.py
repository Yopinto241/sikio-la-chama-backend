from django.urls import path
from .views import CurrentUserView, RegisterView, LoginView, AdminCreateUserView

urlpatterns = [
    path('me/', CurrentUserView.as_view(), name='current_user'),
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('admin/users/', AdminCreateUserView.as_view(), name='admin_create_user'),
]