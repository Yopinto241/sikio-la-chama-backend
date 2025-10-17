from django.contrib import admin
from .models import Ilani

@admin.register(Ilani)
class IlaniAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('title', 'description')
