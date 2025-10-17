from django.urls import path
from .views import ProblemTypeListView, ProblemTypeCreateView

urlpatterns = [
    path('', ProblemTypeListView.as_view(), name='problem_type_list'),
    path('create/', ProblemTypeCreateView.as_view(), name='problem_type_create'),
]