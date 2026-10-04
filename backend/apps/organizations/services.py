from django.db import transaction

from apps.audit.models import AuditLog

from .models import Membership, Organization


@transaction.atomic
def create_organization(*, owner, name, slug):
    organization = Organization.objects.create(owner=owner, name=name, slug=slug)
    Membership.objects.create(organization=organization, user=owner, role=Membership.Role.OWNER)
    AuditLog.objects.create(
        actor=owner, organization=organization, action="organization.created", entity_id=organization.pk
    )
    return organization


def require_team_permission(*, actor, organization, role):
    from rest_framework.exceptions import PermissionDenied

    membership = Membership.objects.filter(user=actor, organization=organization).first()
    if membership is None:
        raise PermissionDenied("Organization membership required.")
    if membership.role == Membership.Role.OWNER and role != Membership.Role.OWNER:
        return
    if membership.role == Membership.Role.MANAGER and role in (
        Membership.Role.EDITOR,
        Membership.Role.FINANCE,
        Membership.Role.SCANNER,
    ):
        return
    raise PermissionDenied("This role cannot manage the requested staff role.")


@transaction.atomic
def invite_member(*, actor, organization, email, role):
    import hashlib
    from datetime import timedelta

    from django.utils import timezone
    from rest_framework.exceptions import ValidationError

    from .models import Invitation

    organization = Organization.objects.select_for_update().get(pk=organization.pk)
    require_team_permission(actor=actor, organization=organization, role=role)
    email = email.strip().lower()
    if Membership.objects.filter(organization=organization, user__email=email).exists():
        raise ValidationError("This account is already a member.")
    invitation = Invitation(
        organization=organization,
        email=email,
        role=role,
        invited_by=actor,
        expires_at=timezone.now() + timedelta(days=7),
    )
    token = invitation_secret(invitation)
    invitation.token_hash = hashlib.sha256(token.encode()).hexdigest()
    invitation.save()
    from apps.notifications.services import enqueue

    enqueue("team.invite", invitation.pk, key=f"invite:{invitation.pk}")
    AuditLog.objects.create(
        actor=actor, organization=organization, action="invitation.created", entity_id=invitation.pk
    )
    return invitation, token


@transaction.atomic
def accept_invitation(*, actor, token):
    import hashlib

    from django.utils import timezone
    from rest_framework.exceptions import PermissionDenied, ValidationError

    from .models import Invitation

    if actor.email_verified_at is None:
        raise PermissionDenied("Verify your email before accepting an invitation.")
    invitation = (
        Invitation.objects.select_for_update().filter(token_hash=hashlib.sha256(token.encode()).hexdigest()).first()
    )
    if invitation is None or invitation.expires_at <= timezone.now():
        raise ValidationError("Invalid or expired invitation.")
    if invitation.email != actor.email:
        raise PermissionDenied("Invitation belongs to another email address.")
    if invitation.accepted_at is not None:
        return Membership.objects.get(organization=invitation.organization, user=actor)
    organization = Organization.objects.select_for_update().get(pk=invitation.organization_id)
    # Recheck inviter's permissions at acceptance; revocation invalidates pending invitations.
    require_team_permission(actor=invitation.invited_by, organization=organization, role=invitation.role)
    membership, _ = Membership.objects.get_or_create(
        organization=organization, user=actor, defaults={"role": invitation.role}
    )
    invitation.accepted_at = timezone.now()
    invitation.save(update_fields=["accepted_at"])
    AuditLog.objects.create(
        actor=actor, organization=organization, action="invitation.accepted", entity_id=membership.pk
    )
    return membership


@transaction.atomic
def update_role(*, actor, organization, membership_id, role):
    from django.shortcuts import get_object_or_404
    from rest_framework.exceptions import PermissionDenied

    organization = Organization.objects.select_for_update().get(pk=organization.pk)
    membership = get_object_or_404(Membership.objects.select_for_update(), organization=organization, pk=membership_id)
    require_team_permission(actor=actor, organization=organization, role=role)
    require_team_permission(actor=actor, organization=organization, role=membership.role)
    if membership.user_id == organization.owner_id:
        raise PermissionDenied("The organization owner cannot be demoted.")
    membership.role = role
    membership.save(update_fields=["role"])
    AuditLog.objects.create(
        actor=actor, organization=organization, action="membership.role_changed", entity_id=membership.pk
    )
    return membership


def invitation_secret(invitation):
    import base64
    import hmac

    from django.conf import settings

    key = hmac.digest(settings.SECRET_KEY.encode(), b"ticket-invitation-v1", "sha256")
    return base64.urlsafe_b64encode(hmac.digest(key, str(invitation.pk).encode(), "sha256")).decode().rstrip("=")
