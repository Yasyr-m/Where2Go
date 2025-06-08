from collections import Counter
from datetime import timedelta

from django.contrib.auth.models import AbstractUser
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils import timezone

# Create your models here.


class CustomUser(AbstractUser):
    two_factor_secret = models.CharField(max_length=16, blank=True, null=True)
    verification_code = models.CharField(
        max_length=10, blank=True, null=True
    )  # Поле для хранения кода 2FA
    friends = models.ManyToManyField(
        "self", symmetrical=True, blank=True, verbose_name="Друзья"
    )
    email = models.EmailField(
        unique=True,
        max_length=254,
        verbose_name="email address",
        error_messages={
            "unique": "A user with that email already exists.",
        },
    )
    force_password_reset = models.BooleanField(
        default=False, verbose_name="Требуется сброс пароля"
    )

    def __str__(self):
        return self.username

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"


class Group(models.Model):
    name = models.CharField(max_length=100, verbose_name="Название группы")
    admin = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="admin_groups",
        verbose_name="Администратор",
    )
    members = models.ManyToManyField(
        CustomUser, related_name="member_groups", verbose_name="Участники"
    )
    created_at = models.DateTimeField(
        default=timezone.now, verbose_name="Дата создания"
    )
    description = models.TextField(blank=True, null=True, verbose_name="Описание")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Группа"
        verbose_name_plural = "Группы"
        ordering = ["-created_at"]


class PollOption(models.Model):
    text = models.CharField(max_length=200, verbose_name="Вариант ответа")
    votes = models.IntegerField(default=0, verbose_name="Количество голосов")

    def __str__(self):
        return self.text

    class Meta:
        verbose_name = "Вариант ответа"
        verbose_name_plural = "Варианты ответов"


def default_end_time():
    return timezone.now() + timedelta(days=1)


class Poll(models.Model):
    group = models.ForeignKey(
        "Group", on_delete=models.CASCADE, related_name="polls", verbose_name="Группа"
    )
    creator = models.ForeignKey(
        "CustomUser",
        on_delete=models.CASCADE,
        related_name="created_polls",
        verbose_name="Создатель",
    )
    question = models.CharField(max_length=255, verbose_name="Вопрос")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    end_time = models.DateTimeField(
        verbose_name="Время окончания", default=default_end_time, null=True, blank=True
    )
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    voted_users = models.ManyToManyField(
        "CustomUser",
        related_name="voted_polls",
        blank=True,
        verbose_name="Проголосовавшие",
    )

    coordinates = models.JSONField(default=list, blank=True, verbose_name="Координаты")
    voted_categories = ArrayField(
        models.CharField(max_length=100),
        default=list,
        blank=True,
        verbose_name="Выбранные категории",
    )

    class Meta:
        verbose_name = "Опрос"
        verbose_name_plural = "Опросы"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.question} ({self.group.name})"

    @property
    def is_expired(self):
        return self.end_time and timezone.now() >= self.end_time

    def get_results(self):
        if not self.coordinates:
            return {
                "total_votes": 0,
                "average_point": None,
                "most_popular_categories": None,
            }

        total_votes = len(self.coordinates)
        total_lat = sum(coord["lat"] for coord in self.coordinates)
        total_lon = sum(coord["lon"] for coord in self.coordinates)

        average_point = {"lat": total_lat / total_votes, "lon": total_lon / total_votes}

        categories = [
            cat["value"]
            for coord in self.coordinates
            for cat in coord.get("categories", [])
            if isinstance(cat, dict) and "value" in cat
        ]

        counter = Counter(categories)
        if counter:
            max_votes = max(counter.values())
            top_categories = sorted(
                [cat for cat, count in counter.items() if count == max_votes]
            )
        else:
            top_categories = []

        return {
            "total_votes": total_votes,
            "average_point": average_point,
            "most_popular_categories": top_categories,
        }

    def calculate_average_point(self):
        if not self.coordinates:
            return None
        total_lat = sum(coord["lat"] for coord in self.coordinates)
        total_lon = sum(coord["lon"] for coord in self.coordinates)
        count = len(self.coordinates)
        return {"lat": total_lat / count, "lon": total_lon / count}

    def most_popular_category(self):
        if not self.voted_categories:
            return None
        counter = Counter(self.voted_categories)
        return counter.most_common(1)[0][0]


class TemporaryAccessLink(models.Model):
    user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name="temporary_links"
    )
    token = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    content_type = models.CharField(
        max_length=50
    )  # Тип контента (например, 'profile', 'photos' и т.д.)
    content_id = models.IntegerField()  # ID контента, к которому предоставляется доступ

    def __str__(self):
        return f"Access link for {self.user.username} - {self.content_type}"

    class Meta:
        verbose_name = "Временная ссылка доступа"
        verbose_name_plural = "Временные ссылки доступа"


class UserSession(models.Model):
    user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name="sessions"
    )
    token = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Session for {self.user.username} - {self.created_at}"

    class Meta:
        verbose_name = "Сессия пользователя"
        verbose_name_plural = "Сессии пользователей"
