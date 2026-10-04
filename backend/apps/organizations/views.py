from django.db import IntegrityError, transaction
from rest_framework import generics
from rest_framework.exceptions import ValidationError

from .models import Organization
from .serializers import OrganizationSerializer
from .services import create_organization


class OrganizationListView(generics.ListCreateAPIView):
    serializer_class = OrganizationSerializer

    def get_queryset(self):
        return Organization.objects.filter(memberships__user=self.request.user).order_by("created_at", "id")

    def perform_create(self, serializer):
        try:
            with transaction.atomic():
                serializer.instance = create_organization(owner=self.request.user, **serializer.validated_data)
        except IntegrityError as exc:
            raise ValidationError({"slug": "This organization slug is already taken."}) from exc


class OrganizationDetailView(generics.RetrieveAPIView):
    serializer_class = OrganizationSerializer

    def get_queryset(self):
        # Scope before lookup: guessed UUIDs do not reveal another organization's existence.
        return Organization.objects.filter(memberships__user=self.request.user)


class InvitationCreateView(generics.GenericAPIView):
    from .serializers import InvitationCreateSerializer

    serializer_class = InvitationCreateSerializer

    def post(self, request, pk):
        from django.conf import settings
        from django.core.mail import send_mail
        from django.shortcuts import get_object_or_404
        from rest_framework.response import Response

        from .services import invite_member

        organization = get_object_or_404(Organization.objects.filter(memberships__user=request.user), pk=pk)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        invitation, token = invite_member(actor=request.user, organization=organization, **serializer.validated_data)
        send_mail(
            "Invitation to Ticket",
            f"Join {organization.name} using this token:\n{token}",
            settings.DEFAULT_FROM_EMAIL,
            [invitation.email],
        )
        return Response(
            {
                "id": invitation.pk,
                "email": invitation.email,
                "role": invitation.role,
                "expires_at": invitation.expires_at,
            },
            status=201,
        )


class InvitationAcceptView(generics.GenericAPIView):
    from .serializers import InvitationAcceptSerializer

    serializer_class = InvitationAcceptSerializer

    def post(self, request):
        from rest_framework.response import Response

        from .services import accept_invitation

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        membership = accept_invitation(actor=request.user, **serializer.validated_data)
        return Response({"organization_id": membership.organization_id, "role": membership.role})


class MembershipRoleView(generics.GenericAPIView):
    from .serializers import RoleSerializer

    serializer_class = RoleSerializer

    def patch(self, request, pk, membership_id):
        from django.shortcuts import get_object_or_404
        from rest_framework.response import Response

        from .services import update_role

        organization = get_object_or_404(Organization.objects.filter(memberships__user=request.user), pk=pk)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        membership = update_role(
            actor=request.user, organization=organization, membership_id=membership_id, **serializer.validated_data
        )
        return Response({"id": membership.pk, "role": membership.role})
