import random
import secrets
from datetime import timedelta
from django.contrib.auth import update_session_auth_hash
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.core.mail import send_mail
from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, status
from rest_framework.authentication import TokenAuthentication
from rest_framework.generics import DestroyAPIView, ListAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..management.captcha import verify_captcha
from ..models import CustomUser, TemporaryAccessLink, UserSession, Poll
from ..serializers import UserDetailSerializer, UserListSerializer, UserSerializer
from ..management.places import get_places_with_meta


class UserCreate(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Создание нового пользователя",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["username", "email", "password", "captcha"],
            properties={
                "username": openapi.Schema(type=openapi.TYPE_STRING),
                "email": openapi.Schema(type=openapi.TYPE_STRING),
                "password": openapi.Schema(type=openapi.TYPE_STRING),
                "captcha": openapi.Schema(
                    type=openapi.TYPE_STRING, description="reCAPTCHA токен"
                ),
            },
        ),
        responses={
            201: openapi.Response(
                description="Пользователь успешно создан", schema=UserSerializer
            ),
            400: openapi.Response(description="Неверные входные данные"),
        },
    )
    def post(self, request, *args, **kwargs):
        captcha_token = request.data.get("captcha")
        if not verify_captcha(captcha_token):
            return Response(
                {"error": "Проверка капчи не пройдена"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save(is_active=False)  # Создаем неактивного пользователя

        # Генерация кода подтверждения
        confirmation_code = random.randint(100000, 999999)
        user.verification_code = confirmation_code
        user.save()

        # Отправка кода на почту
        send_mail(
            "Код подтверждения",
            f"Ваш код подтверждения: {confirmation_code}",
            "where2go-verification@yandex.ru",
            [user.email],
            fail_silently=False,
        )

        return Response(
            {"message": "Пользователь создан. Проверьте вашу почту для подтверждения."},
            status=status.HTTP_201_CREATED,
        )


class UpdateUserView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Обновление данных пользователя",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "newUsername": openapi.Schema(
                    type=openapi.TYPE_STRING, description="Новое имя пользователя"
                ),
                "old_password": openapi.Schema(
                    type=openapi.TYPE_STRING, description="Текущий пароль"
                ),
                "password": openapi.Schema(
                    type=openapi.TYPE_STRING, description="Новый пароль"
                ),
            },
            required=[],
        ),
        responses={200: "Данные пользователя обновлены"},
    )
    def post(self, request):
        user = request.user
        new_username = request.data.get("newUsername")
        old_password = request.data.get("old_password")
        new_password = request.data.get("password")

        if not new_username and not new_password:
            return Response(
                {"message": "Нет данных для обновления."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if new_password:
            if not old_password:
                return Response(
                    {"error": "Необходимо указать текущий пароль для смены."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if not user.check_password(old_password):
                return Response(
                    {"error": "Неверный текущий пароль."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            user.set_password(new_password)

        if new_username:
            user.username = new_username

        try:
            user.save()
        except IntegrityError as e:
            error_message = str(e)
            if "customuser_username_key" in error_message:
                return Response(
                    {"error": "Пользователь с таким именем уже существует."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            else:
                return Response(
                    {"error": "Ошибка сохранения данных пользователя."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        update_session_auth_hash(request, user)

        return Response(
            {"message": "Данные пользователя обновлены успешно."},
            status=status.HTTP_200_OK,
        )


class UserListView(ListAPIView):
    """Получение списка всех пользователей"""

    queryset = CustomUser.objects.all()
    serializer_class = UserListSerializer
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Получить список всех пользователей",
        responses={200: UserListSerializer(many=True)},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class UserDetailView(RetrieveAPIView):
    """Получение информации о конкретном пользователе"""

    queryset = CustomUser.objects.all()
    serializer_class = UserDetailSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "id"

    @swagger_auto_schema(
        operation_description="Получить информацию о пользователе",
        responses={200: UserDetailSerializer()},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class UserDeleteView(DestroyAPIView):
    """Удаление пользователя"""

    queryset = CustomUser.objects.all()
    permission_classes = [IsAdminUser]
    lookup_field = "id"

    @swagger_auto_schema(
        operation_description="Удаление пользователя",
        responses={
            204: "Пользователь успешно удален",
            404: "Пользователь не найден",
            403: "Нет прав для удаления пользователя",
        },
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)


class UserFriendsView(APIView):
    """Получение списка друзей пользователя"""

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Получение списка друзей пользователя",
        responses={200: UserListSerializer(many=True), 404: "Пользователь не найден"},
    )
    def get(self, request, user_id):
        user = get_object_or_404(CustomUser, id=user_id)
        friends = user.friends.all()
        serializer = UserListSerializer(friends, many=True)
        return Response(serializer.data)


class GetMeView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Получение информации о текущем пользователе",
        responses={
            200: openapi.Response(
                description="Информация о пользователе",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "username": openapi.Schema(type=openapi.TYPE_STRING),
                        "email": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            )
        },
    )
    def get(self, request):
        user = request.user
        return Response(
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
            }
        )


class UserSearchView(APIView):
    """Полнотекстовый поиск пользователей"""

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Полнотекстовый поиск пользователей по username и email",
        manual_parameters=[
            openapi.Parameter(
                "q",
                openapi.IN_QUERY,
                description="Поисковый запрос",
                type=openapi.TYPE_STRING,
                required=True,
            )
        ],
        responses={200: UserListSerializer(many=True), 400: "Неверный формат запроса"},
    )
    def get(self, request):
        query = request.query_params.get("q", "").strip()

        if not query:
            return Response([])

        search_vector = SearchVector("username", "email", config="simple")
        search_query = SearchQuery(query, config="simple")

        users = (
            CustomUser.objects.annotate(rank=SearchRank(search_vector, search_query))
            .filter(
                rank__gte=0.01
            )  # Может надо убрать, потому что из-за фильтрации может быть нулевой результат
            .exclude(id=request.user.id)
            .order_by("-rank")[:20]
        )

        serializer = UserListSerializer(users, many=True)
        return Response(serializer.data)


class TemporaryAccessLinkView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Создание временной ссылки доступа",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["content_type", "content_id"],
            properties={
                "content_type": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Тип контента (например, 'profile', 'photos')",
                ),
                "content_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="ID контента"
                ),
                "duration_hours": openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description="Срок действия ссылки в часах",
                    default=24,
                ),
            },
        ),
        responses={
            201: openapi.Response(
                description="Ссылка создана",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "token": openapi.Schema(type=openapi.TYPE_STRING),
                        "expires_at": openapi.Schema(
                            type=openapi.TYPE_STRING, format="date-time"
                        ),
                        "link": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
            400: "Неверные параметры запроса",
        },
    )
    def post(self, request):
        """Создание временной ссылки доступа"""
        content_type = request.data.get("content_type")
        content_id = request.data.get("content_id")
        duration_hours = request.data.get("duration_hours", 24)  # По умолчанию 24 часа

        if not content_type or not content_id:
            return Response(
                {"error": "Необходимо указать тип контента и его ID"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Генерация уникального токена
        token = secrets.token_urlsafe(32)
        expires_at = timezone.now() + timedelta(hours=duration_hours)

        # Создание временной ссылки
        access_link = TemporaryAccessLink.objects.create(
            user=request.user,
            token=token,
            expires_at=expires_at,
            content_type=content_type,
            content_id=content_id,
        )

        return Response(
            {
                "token": access_link.token,
                "expires_at": access_link.expires_at,
                "link": f"/api/access/{access_link.token}"
            },
            status=status.HTTP_201_CREATED,
        )

    @swagger_auto_schema(
        operation_description="Отзыв временной ссылки доступа",
        responses={204: "Ссылка успешно отозвана", 404: "Ссылка не найдена"},
    )
    def delete(self, request, token):
        """Отзыв временной ссылки доступа"""
        try:
            access_link = TemporaryAccessLink.objects.get(
                token=token, user=request.user
            )
            access_link.is_active = False
            access_link.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except TemporaryAccessLink.DoesNotExist:
            return Response(
                {"error": "Ссылка не найдена"}, status=status.HTTP_404_NOT_FOUND
            )


class AccessLinkView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Проверка и использование временной ссылки доступа",
        responses={
            200: openapi.Response(
                description="Информация о контенте",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "content_type": openapi.Schema(type=openapi.TYPE_STRING),
                        "content_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "owner": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
            404: "Ссылка не найдена или неактивна",
            410: "Срок действия ссылки истек",
        },
    )
    def get(self, request, token):
        """Проверка и использование временной ссылки доступа"""
        try:
            access_link = TemporaryAccessLink.objects.get(token=token, is_active=True)

            if timezone.now() > access_link.expires_at:
                access_link.is_active = False
                access_link.save()
                return Response(
                    {"error": "Срок действия ссылки истек"}, status=status.HTTP_410_GONE
                )

            if access_link.content_type == "poll_results":
                try:
                    poll = Poll.objects.get(id=access_link.content_id)
                    results_data = poll.get_results()
                    if not results_data or not results_data.get("total_votes"):
                        return Response(
                            {
                                "poll_title": poll.question,
                                "results": {
                                    "total_votes": 0,
                                    "average_point": {
                                        "lat": 0,
                                        "lon": 0,
                                    },
                                    "most_popular_categories": [],
                                },
                                "recommended_places": [],
                                "owner": access_link.user.username,
                            }
                        )

                    categories = results_data["most_popular_categories"]
                    lat = results_data["average_point"]["lat"]
                    lon = results_data["average_point"]["lon"]

                    recommended_places = []
                    for category in categories:
                        data = get_places_with_meta(
                            base_lat=lat,
                            base_lon=lon,
                            category=category,
                            radius=1000,
                            min_rating=4.0,
                        )
                        recommended_places.append(data)

                    return Response({
                        "poll_title": poll.question,
                        "results": {**results_data, "radius": 1000, "min_rating": 4.0},
                        "recommended_places": recommended_places,
                        "owner": access_link.user.username,
                    })
                except Poll.DoesNotExist:
                    return Response({"error": "Опрос не найден"}, status=404)

            return Response(
                {
                    "content_type": access_link.content_type,
                    "content_id": access_link.content_id,
                    "owner": access_link.user.username,
                }
            )

        except TemporaryAccessLink.DoesNotExist:
            return Response(
                {"error": "Ссылка не найдена или неактивна"},
                status=status.HTTP_404_NOT_FOUND,
            )


class UserSessionView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Получение списка активных сессий пользователя",
        responses={
            200: openapi.Response(
                description="Список сессий",
                schema=openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                            "created_at": openapi.Schema(
                                type=openapi.TYPE_STRING, format="date-time"
                            ),
                            "last_activity": openapi.Schema(
                                type=openapi.TYPE_STRING, format="date-time"
                            ),
                            "ip_address": openapi.Schema(type=openapi.TYPE_STRING),
                            "user_agent": openapi.Schema(type=openapi.TYPE_STRING),
                        },
                    ),
                ),
            )
        },
    )
    def get(self, request):
        """Получение списка активных сессий пользователя"""
        sessions = UserSession.objects.filter(
            user=request.user, is_active=True
        ).order_by("-last_activity")

        return Response(
            [
                {
                    "id": session.id,
                    "created_at": session.created_at,
                    "last_activity": session.last_activity,
                    "ip_address": session.ip_address,
                    "user_agent": session.user_agent,
                }
                for session in sessions
            ]
        )

    @swagger_auto_schema(
        operation_description="Деактивация сессии(й) пользователя",
        responses={204: "Сессия(и) успешно деактивированы", 404: "Сессия не найдена"},
    )
    def delete(self, request, session_id=None):
        """Деактивация сессии(й) пользователя"""
        if session_id:
            # Деактивация конкретной сессии
            try:
                session = UserSession.objects.get(id=session_id, user=request.user)
                session.is_active = False
                session.save()
                return Response(status=status.HTTP_204_NO_CONTENT)
            except UserSession.DoesNotExist:
                return Response(
                    {"error": "Сессия не найдена"}, status=status.HTTP_404_NOT_FOUND
                )
        else:
            # Деактивация всех сессий пользователя, кроме текущей
            current_token = request.auth.key if request.auth else None
            UserSession.objects.filter(user=request.user, is_active=True).exclude(
                token=current_token
            ).update(is_active=False)

            return Response(status=status.HTTP_204_NO_CONTENT)
