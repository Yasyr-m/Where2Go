import logging
import random

from django.contrib.auth import authenticate, update_session_auth_hash
from django.core.mail import send_mail
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, status
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import CustomUser, Group
from .serializers import GroupSerializer, UserSerializer

# Create your views here.

logger = logging.getLogger("django.security")


class LoginView(APIView):
    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")
        code = request.data.get("code")  # Получаем код 2FA из запроса
        user = authenticate(username=username, password=password)
        ip = request.META.get("REMOTE_ADDR", "unknown")

        if user is not None:
            # Если код 2FA не был предоставлен, генерируем и отправляем его
            if code is None:
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

        logger.warning(f"Login failed for email: {username} from IP: {ip}")

        return Response(
            {"error": "Неверные учетные данные."}, status=status.HTTP_401_UNAUTHORIZED
        )


class Generate2FASecretView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

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


class UserCreate(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer

    @swagger_auto_schema(
        operation_description="Создание нового пользователя",
        request_body=UserSerializer,
        responses={201: UserSerializer},
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class UpdateUserView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        new_username = request.data.get("username")
        new_password = request.data.get("password")

        if new_username:
            user.username = new_username
        if new_password:
            user.set_password(new_password)  # Устанавливаем новый пароль

        user.save()
        update_session_auth_hash(request, user)  # Обновляем сессию пользователя

        return Response(
            {"message": "Данные пользователя обновлены успешно."},
            status=status.HTTP_200_OK,
        )


class CreateGroupView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Создание новой группы",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["name"],
            properties={
                "name": openapi.Schema(
                    type=openapi.TYPE_STRING, description="Название группы"
                ),
                "members": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(type=openapi.TYPE_INTEGER),
                    description="Список ID участников группы",
                ),
                "description": openapi.Schema(
                    type=openapi.TYPE_STRING, description="Описание группы"
                ),
            },
        ),
        responses={201: GroupSerializer, 400: "Bad Request", 401: "Unauthorized"},
    )
    def post(self, request):
        serializer = GroupSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            group = serializer.save()
            return Response(GroupSerializer(group).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class JoinGroupView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, group_id):
        group = Group.objects.get(id=group_id)
        user = request.user
        group.members.add(user)
        return Response({"message": "Вы вступили в группу."}, status=status.HTTP_200_OK)


class LeaveGroupView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, group_id):
        group = Group.objects.get(id=group_id)
        user = request.user
        group.members.remove(user)
        return Response({"message": "Вы покинули группу."}, status=status.HTTP_200_OK)


class ManageGroupView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, group_id):
        group = Group.objects.get(id=group_id)
        if group.admin != request.user:
            return Response(
                {"error": "Вы не являетесь администратором этой группы."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Логика управления группой (например, изменение имени группы)
        new_name = request.data.get("name")
        if new_name:
            group.name = new_name
            group.save()
            return Response({"message": "Группа обновлена."}, status=status.HTTP_200_OK)

    def delete(self, request, group_id):
        group = Group.objects.get(id=group_id)
        if group.admin != request.user:
            return Response(
                {"error": "Вы не являетесь администратором этой группы."},
                status=status.HTTP_403_FORBIDDEN,
            )

        group.delete()
        return Response(
            {"message": "Группа расформирована."}, status=status.HTTP_200_OK
        )
