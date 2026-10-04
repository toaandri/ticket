from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import User


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "display_name",
            "email_verified_at",
            "created_at",
            "is_superuser",
            "is_staff",
        )
        read_only_fields = (
            "id",
            "email",
            "email_verified_at",
            "created_at",
            "is_superuser",
            "is_staff",
        )


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    class Meta:
        model = User
        fields = (
            "email",
            "display_name",
            "password",
        )

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def validate(self, attrs):
        try:
            validate_password(
                attrs["password"], User(email=attrs["email"], display_name=attrs.get("display_name", ""))
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": exc.messages}) from exc
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class TokenSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=2048)


class ResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ResetConfirmSerializer(TokenSerializer):
    user_id = serializers.UUIDField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class SecureRefreshSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    def validate(self, attrs):
        from rest_framework.exceptions import AuthenticationFailed
        from rest_framework_simplejwt.serializers import TokenRefreshSerializer
        from rest_framework_simplejwt.settings import api_settings
        from rest_framework_simplejwt.tokens import RefreshToken
        from rest_framework_simplejwt.utils import get_md5_hash_password

        token = RefreshToken(attrs["refresh"])
        user = User.objects.filter(pk=token.get(api_settings.USER_ID_CLAIM), is_active=True).first()
        if user is None or token.get(api_settings.REVOKE_TOKEN_CLAIM) != get_md5_hash_password(user.password):
            raise AuthenticationFailed("Session revoked. Sign in again.")
        return TokenRefreshSerializer().validate(attrs)


class MessageSerializer(serializers.Serializer):
    message = serializers.CharField(read_only=True)


class RegistrationResultSerializer(serializers.Serializer):
    user = ProfileSerializer(read_only=True)
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)


class RefreshResultSerializer(serializers.Serializer):
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)
