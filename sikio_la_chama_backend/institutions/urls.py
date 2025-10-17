# institutions/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers
from .views import InstitutionViewSet, DepartmentViewSet, InstitutionFilePermissionsView, InstitutionFilePermissionDetailView, InstitutionFilePermissionViewSet, InstitutionCreateView, DepartmentCreateView, ToggleFilePermissionView

router = DefaultRouter()
router.register(r'institutions', InstitutionViewSet, basename='institution')

institutions_router = routers.NestedDefaultRouter(router, r'institutions', lookup='institution')
institutions_router.register(r'departments', DepartmentViewSet, basename='institution-departments')
# register nested viewset for institution file permissions
institutions_router.register(r'file-permissions', InstitutionFilePermissionViewSet, basename='institution-file-permissions')

urlpatterns = [
    # Admin-only creation endpoints placed BEFORE the router includes so they
    # don't get shadowed by the router's detail lookup (e.g. 'create' being
    # interpreted as a PK and dispatched to the read-only viewset which
    # doesn't allow POST).
    path('institutions/create/', InstitutionCreateView.as_view(), name='institution_create'),
    path('institutions/<int:institution_id>/departments/create/', DepartmentCreateView.as_view(), name='department_create'),
    path('', include(router.urls)),
    # Expose institution-level file permission endpoints here BEFORE the
    # nested router include so these explicit routes take precedence when
    # matching `/api/institutions/<id>/file-permissions/`.
    path('institutions/file-permissions/', InstitutionFilePermissionsView.as_view(), name='file_permissions'),
    path('institutions/<int:institution_id>/file-permissions/', InstitutionFilePermissionDetailView.as_view(), name='update_file_permission'),
    # Backwards-compatible alias: some clients call the singular 'file-permission'
    # endpoint (without the trailing 's'). Accept that path as well to avoid 404s.
    path('institutions/<int:institution_id>/file-permission/', InstitutionFilePermissionDetailView.as_view(), name='update_file_permission_singular'),
    # convenience POST toggle for admin UIs that just flip the bit
    path('institutions/<int:institution_id>/file-permissions/toggle/', ToggleFilePermissionView.as_view(), name='toggle_file_permission'),
    path('', include(institutions_router.urls)),
]
