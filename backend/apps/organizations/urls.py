from django.urls import path

from .views import (
    InvitationAcceptView,
    InvitationCreateView,
    MembershipRoleView,
    OrganizationDetailView,
    OrganizationListView,
)

urlpatterns = [
    path("organizations/<uuid:pk>/members/<uuid:membership_id>/", MembershipRoleView.as_view()),
    path("organizations/<uuid:pk>/invitations/", InvitationCreateView.as_view()),
    path("invitations/accept/", InvitationAcceptView.as_view()),
    path("organizations/", OrganizationListView.as_view(), name="organizations"),
    path("organizations/<uuid:pk>/", OrganizationDetailView.as_view(), name="organization-detail"),
]
