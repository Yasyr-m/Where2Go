from django.http import JsonResponse
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.views import APIView
from Where2go.management.places import get_places_with_meta


class NearbyPlacesView(APIView):
    @swagger_auto_schema(
        operation_description="Получение ближайших мест по координатам.",
        manual_parameters=[
            openapi.Parameter(
                "lat",
                openapi.IN_QUERY,
                description="Широта",
                type=openapi.TYPE_NUMBER,
                required=True,
            ),
            openapi.Parameter(
                "lon",
                openapi.IN_QUERY,
                description="Долгота",
                type=openapi.TYPE_NUMBER,
                required=True,
            ),
            openapi.Parameter(
                "radius",
                openapi.IN_QUERY,
                description="Радиус поиска в метрах",
                type=openapi.TYPE_INTEGER,
                default=1000,
            ),
            openapi.Parameter(
                "category",
                openapi.IN_QUERY,
                description="Категория мест",
                type=openapi.TYPE_STRING,
                default="кафе",
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
                description="Список ближайших мест",
                examples={
                    "application/json": {
                        "search_point": {
                            "lat": 55.7558,
                            "lon": 37.6173,
                            "radius": 1000,
                        },
                        "places": [
                            {
                                "name": "Кафе",
                                "address": "ул. Примерная, 1",
                                "rating": 4.5,
                                "reviews_count": 10,
                                "coordinates": {"lat": 55.7558, "lon": 37.6173},
                                "distance": 100,
                                "2gis_link": "https://2gis.ru/maps?m=37.6173%2C55.7558&q=Кафе",
                                "direction_links": {
                                    "google": "https://www.google.com/maps/dir/?api=1&origin=55.7558,37.6173&destination=55.7558,37.6173",
                                    "yandex": "https://yandex.ru/maps/?rtext=55.7558%2C37.6173~55.7558%2C37.6173&rtt=auto",
                                },
                            }
                        ],
                    }
                },
            ),
            400: "Неверные параметры",
        },
    )
    def get(self, request):
        try:
            base_lat = float(request.GET.get("lat"))
            base_lon = float(request.GET.get("lon"))
            radius = int(request.GET.get("radius", 1000))
            category = request.GET.get("category", "кафе")
            min_rating = float(request.GET.get("min_rating", 4.0))
        except (TypeError, ValueError) as e:
            return JsonResponse(
                {"error": "Invalid parameters", "details": str(e)}, status=400
            )

        return JsonResponse(
            get_places_with_meta(base_lat, base_lon, category, radius, min_rating)
        )
