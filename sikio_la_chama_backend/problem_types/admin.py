from django.contrib import admin
from .models import ProblemType

@admin.register(ProblemType)
class ProblemTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)
