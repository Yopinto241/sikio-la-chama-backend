from django.contrib import admin
from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
	list_display = ('username', 'user_type', 'institution', 'department', 'is_staff', 'is_superuser')
	list_filter = ('user_type', 'institution', 'department')
	search_fields = ('username', 'phone_number')
