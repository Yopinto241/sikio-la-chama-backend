from django.contrib import admin
from .models import Institution, Department

@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'created_at']  # Columns to show in list view
    search_fields = ['name', 'description']  # Searchable fields
    list_filter = ['created_at']  # Filters in sidebar
    ordering = ['name']  # Default sort
    readonly_fields = ['created_at']  # Prevent editing timestamps
    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'description')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)  # Collapsible section
        }),
    )
    empty_value_display = '-'

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'institution', 'description', 'created_at']
    search_fields = ['name', 'description']
    list_filter = ['institution', 'created_at']  # Filter by institution
    ordering = ['institution__name', 'name']  # Sort by institution then name
    readonly_fields = ['created_at']
    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'institution', 'description')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    empty_value_display = '-'