from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core import signing
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import User

VERIFY_SALT = "ticket.verify-email"


def request_verification(user):
    token = signing.dumps({"user_id": str(user.pk), "email": user.email}, salt=VERIFY_SALT)
    send_mail(
        "Verify your Ticket email",
        f"Verify your email with this token:\n{token}",
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
    )


@transaction.atomic
def verify_email(token):
    try:
        data = signing.loads(token, salt=VERIFY_SALT, max_age=86400)
        user = User.objects.select_for_update().get(pk=data["user_id"], email=data["email"], is_active=True)
    except (signing.BadSignature, User.DoesNotExist, KeyError, ValueError) as exc:
        raise ValidationError("Invalid or expired verification token.") from exc
    if user.email_verified_at is None:
        user.email_verified_at = timezone.now()
        user.save(update_fields=["email_verified_at", "updated_at"])
    return user


def request_password_reset(email):
    user = User.objects.filter(email__iexact=email.strip(), is_active=True).first()
    if user is None:
        return
    token = default_token_generator.make_token(user)
    send_mail(
        "Reset your Ticket password",
        f"Account ID: {user.pk}\nReset token: {token}",
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
    )


@transaction.atomic
def reset_password(*, user_id, token, password):
    from django.contrib.auth.password_validation import validate_password
    from django.core.exceptions import ValidationError as DjangoValidationError
    from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

    try:
        user = User.objects.select_for_update().get(pk=user_id, is_active=True)
    except (User.DoesNotExist, ValueError, DjangoValidationError) as exc:
        raise ValidationError("Invalid reset token.") from exc
    if not default_token_generator.check_token(user, token):
        raise ValidationError("Invalid or expired reset token.")
    try:
        validate_password(password, user)
    except DjangoValidationError as exc:
        raise ValidationError({"password": exc.messages}) from exc
    user.set_password(password)
    user.save(update_fields=["password", "updated_at"])
    for outstanding in OutstandingToken.objects.filter(user=user):
        BlacklistedToken.objects.get_or_create(token=outstanding)
