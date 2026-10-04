from django.urls import path

from .views import (
    InvitationAcceptView,
    InvitationCreateView,
    MembershipRoleView,
    OrganizationDetailView,
    OrganizationListView,
)
from .workspace import (
    EventExportView,
    EventMetricsView,
    EventStaffView,
    MembersView,
    OrganizationAuditView,
    OrganizationOrdersView,
    OrganizationTicketsView,
    StaffEventsView,
)

urlpatterns = [
    path("staff/events/", StaffEventsView.as_view()),
    path("organizations/<uuid:pk>/tickets/", OrganizationTicketsView.as_view()),
    path("organizations/<uuid:pk>/members/", MembersView.as_view()),
    path("organizations/<uuid:pk>/audit/", OrganizationAuditView.as_view()),
    path("organizations/<uuid:pk>/orders/", OrganizationOrdersView.as_view()),
    path("events/<uuid:pk>/metrics/", EventMetricsView.as_view()),
    path("events/<uuid:pk>/export/", EventExportView.as_view()),
    path("events/<uuid:pk>/staff/", EventStaffView.as_view()),
    path("organizations/<uuid:pk>/members/<uuid:membership_id>/", MembershipRoleView.as_view()),
    path("organizations/<uuid:pk>/invitations/", InvitationCreateView.as_view()),
    path("invitations/accept/", InvitationAcceptView.as_view()),
    path("organizations/", OrganizationListView.as_view(), name="organizations"),
    path("organizations/<uuid:pk>/", OrganizationDetailView.as_view(), name="organization-detail"),
]
