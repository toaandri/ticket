from django.urls import path

from .views import OrganizationDetailView, OrganizationListView

urlpatterns = [
    path("organizations/", OrganizationListView.as_view(), name="organizations"),
    path("organizations/<uuid:pk>/", OrganizationDetailView.as_view(), name="organization-detail"),
]
