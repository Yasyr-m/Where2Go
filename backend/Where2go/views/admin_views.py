from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
from django.core.mail import send_mail
import random

from ..models import CustomUser, Group
from ..serializers import GroupSerializer, UserSerializer


@staff_member_required
@require_http_methods(["GET", "POST"])
def admin_verify_2fa(request):
    if request.method == "POST":
        code = request.POST.get('code')
        stored_code = request.session.get('admin_2fa_code')
        
        if code == stored_code:
            request.session['admin_2fa_verified'] = True
            return redirect('admin:index')
        else:
            messages.error(request, 'Неверный код подтверждения')
    
    # Генерация нового кода
    verification_code = str(random.randint(100000, 999999))
    request.session['admin_2fa_code'] = verification_code
    
    # Отправка кода на почту
    send_mail(
        'Код подтверждения для входа в админ-панель',
        f'Ваш код подтверждения: {verification_code}',
        'where2go-verification@yandex.ru',
        [request.user.email],
        fail_silently=False,
    )
    
    return render(request, 'admin/verify_2fa.html')


class UserListView(APIView):
    permission_classes = [IsAdminUser]

    @swagger_auto_schema(
        operation_description="Получение списка всех пользователей",
        responses={
            200: UserSerializer(many=True),
            403: "Нет прав доступа"
        }
    )
    def get(self, request):
        users = CustomUser.objects.all()
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)


class UserDeleteView(APIView):
    permission_classes = [IsAdminUser]

    @swagger_auto_schema(
        operation_description="Удаление пользователя",
        responses={
            204: "Пользователь успешно удален",
            404: "Пользователь не найден",
            403: "Нет прав доступа"
        }
    )
    def delete(self, request, user_id):
        try:
            user = CustomUser.objects.get(id=user_id)
            user.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except CustomUser.DoesNotExist:
            return Response(
                {"error": "Пользователь не найден."}, status=status.HTTP_404_NOT_FOUND
            )


class UserBanView(APIView):
    permission_classes = [IsAdminUser]

    @swagger_auto_schema(
        operation_description="Блокировка пользователя",
        responses={
            200: "Пользователь успешно заблокирован",
            404: "Пользователь не найден",
            403: "Нет прав доступа"
        }
    )
    def patch(self, request, user_id):
        try:
            user = CustomUser.objects.get(id=user_id)
            user.is_active = False  # Блокируем пользователя
            user.save()
            return Response(
                {"message": "Пользователь заблокирован."}, status=status.HTTP_200_OK
            )
        except CustomUser.DoesNotExist:
            return Response(
                {"error": "Пользователь не найден."}, status=status.HTTP_404_NOT_FOUND
            )


class GroupListView(APIView):
    permission_classes = [IsAdminUser]

    @swagger_auto_schema(
        operation_description="Получение списка всех групп",
        responses={
            200: GroupSerializer(many=True),
            403: "Нет прав доступа"
        }
    )
    def get(self, request):
        groups = Group.objects.all()
        serializer = GroupSerializer(groups, many=True)
        return Response(serializer.data)


class GroupEditView(APIView):
    permission_classes = [IsAdminUser]

    @swagger_auto_schema(
        operation_description="Редактирование группы",
        request_body=GroupSerializer,
        responses={
            200: GroupSerializer,
            400: "Неверные данные",
            404: "Группа не найдена",
            403: "Нет прав доступа"
        }
    )
    def patch(self, request, group_id):
        try:
            group = Group.objects.get(id=group_id)
            serializer = GroupSerializer(group, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Group.DoesNotExist:
            return Response(
                {"error": "Группа не найдена."}, status=status.HTTP_404_NOT_FOUND
            )


class GroupDeleteView(APIView):
    permission_classes = [IsAdminUser]

    @swagger_auto_schema(
        operation_description="Удаление группы",
        responses={
            204: "Группа успешно удалена",
            404: "Группа не найдена",
            403: "Нет прав доступа"
        }
    )
    def delete(self, request, group_id):
        try:
            group = Group.objects.get(id=group_id)
            group.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Group.DoesNotExist:
            return Response(
                {"error": "Группа не найдена."}, status=status.HTTP_404_NOT_FOUND
            )


class UserSessionDeleteView(APIView):
    permission_classes = [IsAdminUser]

    @swagger_auto_schema(
        operation_description="Удаление всех сессий пользователя",
        responses={
            200: "Все сессии пользователя успешно удалены",
            404: "Пользователь не найден",
            403: "Нет прав доступа"
        }
    )
    def delete(self, request, user_id):
        try:
            user = CustomUser.objects.get(id=user_id)
            Token.objects.filter(user=user).delete()
            return Response(
                {"message": "Все сессии пользователя завершены."},
                status=status.HTTP_200_OK,
            )
        except CustomUser.DoesNotExist:
            return Response(
                {"error": "Пользователь не найден."}, status=status.HTTP_404_NOT_FOUND
            )


class AdminUserManagementView(APIView):
    permission_classes = [IsAdminUser]

    @swagger_auto_schema(
        operation_description="Управление пользователем администратором",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['action'],
            properties={
                'action': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Действие (например, 'force_password_reset')"
                )
            }
        ),
        responses={
            200: "Действие успешно выполнено",
            400: "Неверное действие",
            404: "Пользователь не найден",
            403: "Нет прав доступа"
        }
    )
    def post(self, request, user_id):
        """Управление пользователем администратором"""
        try:
            user = CustomUser.objects.get(id=user_id)
            action = request.data.get('action')

            if action == 'force_password_reset':
                user.force_password_reset = True
                user.save()
                return Response({
                    'message': f'Пользователю {user.username} будет предложено сменить пароль при следующем входе'
                })
            else:
                return Response({
                    'error': 'Неизвестное действие'
                }, status=status.HTTP_400_BAD_REQUEST)

        except CustomUser.DoesNotExist:
            return Response({
                'error': 'Пользователь не найден'
            }, status=status.HTTP_404_NOT_FOUND)
