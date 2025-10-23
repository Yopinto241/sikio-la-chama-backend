from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse

# Root view to avoid 404 at "/"
def root_view(request):
    return JsonResponse({
        "message": "Welcome to Sikio La Chama API 🚀",
        "endpoints": {
            "users": "/api/users/",
            "messages": "/api/messages/",
            "institutions": "/api/institutions/",
            "problem_types": "/api/problem-types/",
            "polls": "/api/polls/",
            "reports": "/api/reports/",
            "leaders": "/api/leaders/",
            "analytics": "/api/analytics/",
            "announcements": "/api/announcements/",
            "ilani": "/api/ilani/",
            "feeds": "/api/feeds/",
            "notifications": "/api/notifications/",
        }
    })

urlpatterns = [
    path('admin/', admin.site.urls),

    # Root handler
    path('', root_view, name='root'),

    # Core apps
    path('api/users/', include('users.urls')),
    path('api/messages/', include('user_messages.urls')),
    path('api/', include('institutions.urls')),
    path('api/problem-types/', include('problem_types.urls')),
    path('api/polls/', include('polls.urls')),
    path('api/reports/', include('reports.urls')),
    path('api/leaders/', include('leaders.urls')),
    path('api/analytics/', include('analytics.urls')),

    # Newly added apps
    path('api/announcements/', include('announcements.urls')),
    path('api/ilani/', include('ilani.urls')),
    path('api/feeds/', include('feeds.urls')),
    path('api/notifications/', include('notifications.urls')),
]

# Media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
