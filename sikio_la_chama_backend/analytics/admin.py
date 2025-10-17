from django.contrib import admin
from .models import Trend

@admin.register(Trend)
class TrendAdmin(admin.ModelAdmin):
    list_display = ('name', 'value', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name',)
