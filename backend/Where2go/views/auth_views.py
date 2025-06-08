import logging
import random

from django.contrib.auth import authenticate
from django.core.mail import send_mail
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..management.captcha import verify_captcha
from ..models import CustomUser

logger = logging.getLogger("django.security")


class LoginView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Аутентификация пользователя по email и паролю",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["email", "password"],
            properties={
                "email": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format="email",
                    description="Email пользователя",
                ),
                "password": openapi.Schema(
                    type=openapi.TYPE_STRING, format="password", description="Пароль"
                ),
            },
        ),
        responses={
            200: openapi.Response(
                "Успешная аутентификация",
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "access": openapi.Schema(
                            type=openapi.TYPE_STRING, description="JWT Access Token"
                        ),
                        "refresh": openapi.Schema(
                            type=openapi.TYPE_STRING, description="JWT Refresh Token"
                        ),
                    },
                ),
            ),
            401: openapi.Response(
                "Ошибка аутентификации",
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "error": openapi.Schema(
                            type=openapi.TYPE_STRING, description="Сообщение об ошибке"
                        ),
                    },
                ),
            ),
        },
    )
    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")

        ip = request.META.get("REMOTE_ADDR", "unknown")
        user = authenticate(request, email=email, password=password)

        if user is not None:
            refresh = Token.objects.get_or_create(user=user)
            return Response(
                {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                },
                status=status.HTTP_200_OK,
            )

        logger.warning(f"Login failed for email: {email} from IP: {ip}")

        return Response(
            {"error": "Неверный email или пароль"}, status=status.HTTP_401_UNAUTHORIZED
        )


class LoginView2FA(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Аутентификация пользователя",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["username", "password"],
            properties={
                "username": openapi.Schema(
                    type=openapi.TYPE_STRING, description="Имя пользователя"
                ),
                "password": openapi.Schema(
                    type=openapi.TYPE_STRING, description="Пароль"
                ),
                "code": openapi.Schema(
                    type=openapi.TYPE_STRING, description="Код 2FA (опционально)"
                ),
                "captcha": openapi.Schema(
                    type=openapi.TYPE_STRING, description="reCAPTCHA токен"
                ),
            },
        ),
        responses={
            200: openapi.Response(
                "Успешная аутентификация",
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={"token": openapi.Schema(type=openapi.TYPE_STRING)},
                ),
            ),
            400: "Неверный код 2FA / Ошибка капчи",
            401: "Неверные учетные данные",
        },
    )
    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")
        code = request.data.get("code")  # Получаем код 2FA из запроса
        captcha = request.data.get("captcha")

        user = authenticate(username=username, password=password)
        if user is not None:
            # Если код 2FA не был предоставлен, генерируем и отправляем его
            if code is None:
                if not verify_captcha(captcha):
                    return Response(
                        {"error": "Проверка капчи не пройдена"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                verification_code = random.randint(100000, 999999)
                user.verification_code = (
                    verification_code  # Сохраняем код в модели пользователя
                )
                user.save()
                # Отправка кода на почту
                send_mail(
                    "Ваш код 2FA",
                    f"Ваш код: {verification_code}",
                    "where2go-verification@yandex.ru",
                    [user.email],
                    fail_silently=False,
                )
                return Response(
                    {"message": "Код 2FA отправлен на вашу почту."},
                    status=status.HTTP_200_OK,
                )

            # Проверка кода 2FA
            if str(user.verification_code) == str(code):
                user.verification_code = None  # Сброс кода после успешной проверки
                user.save()

                # Получение или создание токена
                token, created = Token.objects.get_or_create(user=user)
                return Response(
                    {
                        "message": "Успешная аутентификация.",
                        "token": token.key,  # Возвращаем токен
                    },
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {"error": "Неверный код 2FA."}, status=status.HTTP_400_BAD_REQUEST
                )
        ip = request.META.get("REMOTE_ADDR", "unknown")
        logger.warning(f"Login failed for username: {username} from IP: {ip}")

        return Response(
            {"error": "Неверные учетные данные."}, status=status.HTTP_401_UNAUTHORIZED
        )


class Generate2FASecretView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Генерация кода 2FA",
        responses={
            200: "Код отправлен на электронную почту",
            401: "Неавторизованный доступ",
        },
    )
    def post(self, request):
        user = request.user
        # Генерация случайного кода
        verification_code = random.randint(100000, 999999)
        user.verification_code = verification_code
        user.save()

        # Отправка кода на электронную почту
        try:
            send_mail(
                "Ваш код двухфакторной аутентификации",
                f"Ваш код: {verification_code}",
                "where2go-verification@yandex.ru",
                [user.email],
                fail_silently=False,
            )
            return Response(
                {"message": "Код отправлен на вашу электронную почту."},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ActivateUserView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Активация пользователя по email и коду подтверждения",
        responses={
            200: "Аккаунт активирован",
            400: "Неверный код подтверждения",
            404: "Пользователь не найден",
        },
    )
    def post(self, request):
        email = request.data.get("email")
        code = request.data.get("code")

        try:
            user = CustomUser.objects.get(email=email)
            if user.verification_code == code:
                user.is_active = True
                user.verification_code = None
                user.save()
                return Response(
                    {"message": "Аккаунт активирован!"}, status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {"error": "Неверный код подтверждения."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except CustomUser.DoesNotExist:
            return Response(
                {"error": "Пользователь не найден."}, status=status.HTTP_404_NOT_FOUND
            )
