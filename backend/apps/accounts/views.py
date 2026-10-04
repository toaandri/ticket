from django.db import IntegrityError, transaction
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .serializers import LogoutSerializer, ProfileSerializer, RegisterSerializer


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = (AllowAny,)
    authentication_classes = ()
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "login"

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                user = serializer.save()
                refresh = RefreshToken.for_user(user)
        except IntegrityError as exc:
            raise ValidationError({"email": "An account with this email already exists."}) from exc
        return Response(
            {"user": ProfileSerializer(user).data, "access": str(refresh.access_token), "refresh": str(refresh)},
            status=status.HTTP_201_CREATED,
        )


class LoginView(TokenObtainPairView):
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "login"

    def post(self, request, *args, **kwargs):
        # Normalize the same way as registration without changing password whitespace.
        if isinstance(request.data.get("email"), str):
            data = request.data.copy()
            data["email"] = data["email"].strip().lower()
            serializer = self.get_serializer(data=data)
            serializer.is_valid(raise_exception=True)
            return Response(serializer.validated_data)
        return super().post(request, *args, **kwargs)


class RefreshView(TokenRefreshView):
    from .serializers import SecureRefreshSerializer

    serializer_class = SecureRefreshSerializer
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "login"


class LogoutView(APIView):
    serializer_class = LogoutSerializer

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            token = RefreshToken(serializer.validated_data["refresh"])
            if str(token["user_id"]) != str(request.user.pk):
                raise ValidationError("Refresh token does not belong to this account.")
            token.blacklist()
        except TokenError as exc:
            raise ValidationError("Invalid refresh token.") from exc
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = ProfileSerializer
    http_method_names = (
        "get",
        "patch",
        "head",
        "options",
    )

    def get_object(self):
        return self.request.user


class VerificationRequestView(APIView):
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "login"

    def post(self, request):
        from .services import request_verification

        request_verification(request.user)
        return Response({"message": "Verification email sent."}, status=status.HTTP_202_ACCEPTED)


class VerifyEmailView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes = ()
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "login"

    def post(self, request):
        from .serializers import TokenSerializer
        from .services import verify_email

        serializer = TokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        verify_email(serializer.validated_data["token"])
        return Response({"message": "Email verified."})


class PasswordResetRequestView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes = ()
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "login"

    def post(self, request):
        from .serializers import ResetRequestSerializer
        from .services import request_password_reset

        serializer = ResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request_password_reset(serializer.validated_data["email"])
        return Response({"message": "If this account exists, a reset email has been sent."}, status=202)


class PasswordResetConfirmView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes = ()
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "login"

    def post(self, request):
        from .serializers import ResetConfirmSerializer
        from .services import reset_password

        serializer = ResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reset_password(**serializer.validated_data)
        return Response({"message": "Password updated. Sign in again."})
