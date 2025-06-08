from django.shortcuts import get_object_or_404
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.generics import ListAPIView, RetrieveDestroyAPIView, UpdateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..management.places import get_places_with_meta
from ..models import Group, Poll
from ..serializers import PollSerializer


class CreatePollView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Создание нового опроса в группе",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["question", "options"],
            properties={
                "question": openapi.Schema(
                    type=openapi.TYPE_STRING, description="Вопрос опроса"
                ),
            },
        ),
        responses={
            201: PollSerializer,
            400: "Неверный формат данных",
            403: "Нет прав доступа",
        },
    )
    def post(self, request, group_id):
        group = get_object_or_404(Group, id=group_id)
        if group.admin != request.user and request.user not in group.members.all():
            return Response(
                {"error": "Вы не являетесь участником этой группы."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Добавляем группу в данные запроса
        data = request.data.copy()
        data["group"] = group_id

        serializer = PollSerializer(data=data, context={"request": request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer.save(creator=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class PollDetailView(RetrieveDestroyAPIView):
    queryset = Poll.objects.all()
    serializer_class = PollSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "id"

    @swagger_auto_schema(
        operation_description="Получение информации об опросе",
        manual_parameters=[
            openapi.Parameter(
                "id",
                openapi.IN_PATH,
                description="ID опроса",
                type=openapi.TYPE_INTEGER,
                required=True,
            )
        ],
        responses={200: PollSerializer, 404: "Опрос не найден"},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Удаление опроса",
        responses={
            204: "Опрос удален",
            403: "Нет прав для удаления опроса",
            404: "Опрос не найден",
        },
    )
    def delete(self, request, *args, **kwargs):
        poll = self.get_object()
        if poll.creator != request.user and poll.group.admin != request.user:
            return Response(
                {"error": "У вас нет прав для удаления этого опроса."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().delete(request, *args, **kwargs)


class ClosePollView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Закрытие опроса",
        manual_parameters=[
            openapi.Parameter(
                "id",
                openapi.IN_PATH,
                description="ID опроса",
                type=openapi.TYPE_INTEGER,
                required=True,
            )
        ],
        responses={
            200: "Опрос успешно закрыт",
            403: "Нет прав для закрытия опроса",
            404: "Опрос не найден",
        },
    )
    def post(self, request, id):
        poll = get_object_or_404(Poll, id=id)
        if poll.creator != request.user and poll.group.admin != request.user:
            return Response(
                {"error": "У вас нет прав для закрытия этого опроса."},
                status=status.HTTP_403_FORBIDDEN,
            )

        poll.is_active = False
        poll.save()

        # Вычисляем среднюю точку
        average_point = poll.calculate_average_point()

        return Response(
            {"message": "Опрос успешно закрыт.", "average_point": average_point},
            status=status.HTTP_200_OK,
        )


class PollListView(ListAPIView):
    serializer_class = PollSerializer
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Получение списка всех опросов в группе",
        manual_parameters=[
            openapi.Parameter(
                "group_id",
                openapi.IN_PATH,
                description="ID группы",
                type=openapi.TYPE_INTEGER,
                required=True,
            )
        ],
        responses={200: PollSerializer(many=True), 404: "Группа не найдена"},
    )
    def get_queryset(self):
        group_id = self.kwargs["group_id"]
        return Poll.objects.filter(group_id=group_id)


class PollListAllView(ListAPIView):
    serializer_class = PollSerializer
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Получение списка всех опросов",
        responses={
            200: PollSerializer(many=True),
        },
    )
    def get_queryset(self):
        return Poll.objects.all()


class VotePollView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["coordinates"],
            properties={
                "coordinates": openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    required=["lat", "lon", "categories"],
                    properties={
                        "lat": openapi.Schema(
                            type=openapi.TYPE_NUMBER, description="Широта"
                        ),
                        "lon": openapi.Schema(
                            type=openapi.TYPE_NUMBER, description="Долгота"
                        ),
                        "categories": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Items(type=openapi.TYPE_STRING),
                            description="Категории (например, кафе, бар)",
                        ),
                    },
                    description="Координаты и категории пользователя",
                )
            },
        )
    )
    def post(self, request, id):
        poll = get_object_or_404(Poll, id=id)

        # Проверки
        if poll.is_expired:
            return Response({"error": "Срок опроса истек"}, status=400)
        if request.user not in poll.group.members.all():
            return Response({"error": "Вы не участник группы"}, status=403)
        if request.user in poll.voted_users.all():
            return Response({"error": "Вы уже голосовали"}, status=403)

        coordinates = request.data.get("coordinates")
        if not coordinates:
            return Response({"error": "Координаты не предоставлены"}, status=400)

        # Проверяем, что coordinates - это объект (dict), а не список
        if not isinstance(coordinates, dict):
            return Response({"error": "coordinates должно быть объектом"}, status=400)

        # Проверяем, что в объекте coordinates есть все необходимые поля
        if not all(k in coordinates for k in ("lat", "lon", "categories")):
            return Response(
                {"error": "coordinates должен содержать lat, lon и categories"},
                status=400,
            )

        # Проверяем, что lat и lon являются числами
        if not isinstance(coordinates["lat"], (int, float)) or not isinstance(
            coordinates["lon"], (int, float)
        ):
            return Response({"error": "lat и lon должны быть числами"}, status=400)

        # Проверяем, что categories - это список
        if not isinstance(coordinates["categories"], list):
            return Response({"error": "categories должен быть списком"}, status=400)

        # Проверяем, что каждый элемент в categories - это объект с нужными полями
        for category in coordinates["categories"]:
            if not isinstance(category, dict):
                return Response(
                    {"error": "Каждый элемент categories должен быть объектом (dict)"},
                    status=400,
                )

            if not all(k in category for k in ("label", "value")):
                return Response(
                    {
                        "error": "Каждый элемент categories должен содержать label и value"
                    },
                    status=400,
                )

            if not isinstance(category["label"], str) or not isinstance(
                category["value"], str
            ):
                return Response(
                    {"error": "label и value должны быть строками"}, status=400
                )

        # Голосование:
        poll.voted_users.add(request.user)

        # Сохраняем координаты
        poll.coordinates.append(coordinates)
        poll.save()

        if poll.voted_users.count() == poll.group.members.count():
            poll.is_active = False
            poll.save()

        return Response({"message": "Голос учтён"}, status=200)


class PollResultsView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Получение результатов опроса",
        manual_parameters=[
            openapi.Parameter(
                "radius",
                openapi.IN_QUERY,
                description="Радиус поиска в метрах",
                type=openapi.TYPE_INTEGER,
                default=1000,
            ),
            openapi.Parameter(
                "min_rating",
                openapi.IN_QUERY,
                description="Минимальный рейтинг",
                type=openapi.TYPE_NUMBER,
                default=4.0,
            ),
        ],
        responses={
            200: openapi.Response(
                description="Результаты опроса и список подходящих мест",
                examples={
                    "application/json": {
                        "results": {
                            "total_votes": 5,
                            "average_point": {"lat": 55.75, "lon": 37.62},
                            "most_popular_categories": ["кафе"],
                        },
                        "recommended_places": [
                            {
                                "search_point": {
                                    "lat": 55.75,
                                    "lon": 37.62,
                                    "radius": 500,
                                },
                                "places": [
                                    {
                                        "name": "Кафе 'Вкусно'",
                                        "lat": 55.751,
                                        "lon": 37.618,
                                        "rating": 4.5,
                                    }
                                ],
                            }
                        ],
                    }
                },
            ),
            403: "Нет прав для просмотра результатов",
            404: "Опрос не найден",
        },
    )
    def get(self, request, id):
        # Параметры из запроса
        try:
            radius = int(request.GET.get("radius", 1000))
            min_rating = float(request.GET.get("min_rating", 4.0))
        except (TypeError, ValueError):
            return Response(
                {"error": "Некорректные параметры"}, status=status.HTTP_400_BAD_REQUEST
            )

        poll = get_object_or_404(Poll, id=id)

        # Проверка прав
        if not (
            poll.is_expired
            or not poll.is_active
            or request.user == poll.creator
            or request.user == poll.group.admin
        ):
            return Response(
                {"error": "Результаты будут доступны после завершения опроса."},
                status=status.HTTP_403_FORBIDDEN,
            )

        results_data = poll.get_results()
        if not results_data or not results_data.get("total_votes"):
            return Response(
                {
                    "results": {
                        "total_votes": 0,
                        "average_point": {
                            "lat": 0,
                            "lon": 0,
                        },
                        "most_popular_categories": [],
                    },
                    "recommended_places": [],
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
                radius=radius,
                min_rating=min_rating,
            )
            recommended_places.append(data)

        return Response(
            {
                "results": {**results_data, "radius": radius, "min_rating": min_rating},
                "recommended_places": recommended_places,
            }
        )


class PollUpdateView(UpdateAPIView):
    queryset = Poll.objects.all()
    serializer_class = PollSerializer
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Обновление вопроса или времени окончания опроса",
        responses={
            200: PollSerializer(),
            403: "Нет прав на редактирование опроса",
            404: "Опрос не найден",
            400: "Неверные данные",
        },
    )
    def patch(self, request, *args, **kwargs):
        poll = self.get_object()

        if poll.creator != request.user:
            return Response(
                {"error": "У вас недостаточно прав для обновления опроса."},
                status=status.HTTP_403_FORBIDDEN,
            )

        return super().patch(request, *args, **kwargs)
