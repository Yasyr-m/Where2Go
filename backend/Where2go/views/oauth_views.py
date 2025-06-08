import json
import logging

import requests
from allauth.socialaccount.models import SocialAccount, SocialToken
from allauth.socialaccount.providers.google.provider import GoogleProvider
from django.conf import settings
from django.contrib.auth import get_user_model
from django.shortcuts import redirect
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from django.http import HttpResponseRedirect

logger = logging.getLogger("django.security")

User = get_user_model()


class VKLoginView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        """
        Перенаправляет пользователя на страницу авторизации VK
        """
        client_id = settings.SOCIALACCOUNT_PROVIDERS["vk"]["APP"]["client_id"]
        redirect_uri = "https://localhost:8000/accounts/vk/login/callback/"
        scope = "email"

        vk_auth_url = (
            f"https://oauth.vk.com/authorize"
            f"?client_id={client_id}"
            f"&redirect_uri={redirect_uri}"
            f"&scope={scope}"
            f"&response_type=code"
            f"&v=5.131"
        )

        return redirect(vk_auth_url)

    def post(self, request):
        """
        Обрабатывает POST-запрос для авторизации через VK
        """
        return self.get(request)


class GoogleLoginView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        """
        Перенаправляет пользователя на страницу авторизации Google
        """
        print("\n=== Starting Google OAuth login ===")
        client_id = settings.SOCIALACCOUNT_PROVIDERS["google"]["APP"]["client_id"]
        redirect_uri = "https://localhost:8000/api/auth/social/callback/"
        scope = "email profile"

        google_auth_url = (
            f"https://accounts.google.com/o/oauth2/v2/auth"
            f"?client_id={client_id}"
            f"&redirect_uri={redirect_uri}"
            f"&scope={scope}"
            f"&response_type=code"
            f"&access_type=online"
            f"&prompt=select_account"
        )

        print(f"Redirecting to Google auth URL: {google_auth_url}")
        return redirect(google_auth_url)

    def post(self, request):
        """
        Обрабатывает POST-запрос для авторизации через Google
        """
        return self.get(request)


@api_view(["GET"])
@permission_classes([AllowAny])
def social_auth_callback(request):
    """
    Обработчик callback от OAuth-провайдеров
    """
    try:
        print("\n=== Starting social_auth_callback ===")
        print(f"Request GET params: {request.GET}")
        code = request.GET.get("code")
        if not code:
            print("Error: No code provided in callback")
            return Response(
                {"error": "No code provided"}, status=status.HTTP_400_BAD_REQUEST
            )
        print(f"Received code: {code}")

        # Получаем токен доступа от Google
        token_url = "https://oauth2.googleapis.com/token"
        token_data = {
            "code": code,
            "client_id": settings.SOCIALACCOUNT_PROVIDERS["google"]["APP"]["client_id"],
            "client_secret": settings.SOCIALACCOUNT_PROVIDERS["google"]["APP"][
                "secret"
            ],
            "redirect_uri": "https://localhost:8000/api/auth/social/callback/",
            "grant_type": "authorization_code",
        }
        print(f"Requesting token with data: {token_data}")
        token_response = requests.post(token_url, data=token_data)
        token_json = token_response.json()
        print(
            f"Token response JSON: {json.dumps(token_json, indent=2, ensure_ascii=False)}"
        )

        if "error" in token_json:
            print(f"Token error: {token_json['error']}")
            return Response(
                {"error": f"Token error: {token_json['error']}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Получаем информацию о пользователе
        userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
        headers = {"Authorization": f"Bearer {token_json['access_token']}"}
        print(f"Requesting user info with headers: {headers}")
        userinfo_response = requests.get(userinfo_url, headers=headers)
        userinfo = userinfo_response.json()
        print(
            f"User info response JSON: {json.dumps(userinfo, indent=2, ensure_ascii=False)}"
        )

        if "error" in userinfo:
            print(f"Userinfo error: {userinfo['error']}")
            return Response(
                {"error": f"Userinfo error: {userinfo['error']}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Создаем или получаем пользователя
        email = userinfo.get("email")
        if not email:
            print("Error: No email provided by Google")
            return Response(
                {"error": "No email provided by Google"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        print(f"Processing user with email: {email}")

        try:
            user = User.objects.get(email=email)
            print(f"Existing user found: {email}")
        except User.DoesNotExist:
            # Создаем нового пользователя
            username = email.split("@")[0]
            base_username = username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1

            print(f"Creating new user with username: {username}")
            user = User.objects.create_user(
                username=username,
                email=email,
                first_name=userinfo.get("given_name", ""),
                last_name=userinfo.get("family_name", ""),
            )
            print(f"New user created: {email}")

        # Создаем или обновляем токены для пользователя
        print("Creating/updating token for user")
        token, created = Token.objects.get_or_create(user=user)
        if not created:
            token.delete()
            token = Token.objects.create(user=user)
        print(f"Token created for user: {email}")

        # Сохраняем социальный аккаунт
        print("Creating/updating social account")
        social_account, created = SocialAccount.objects.get_or_create(
            user=user,
            provider=GoogleProvider.id,
            defaults={"uid": userinfo.get("id"), "extra_data": userinfo},
        )

        if not created:
            social_account.extra_data = userinfo
            social_account.save()
        print(f"Social account {'created' if created else 'updated'} for user: {email}")

        # Сохраняем токены
        print("Saving social tokens")
        SocialToken.objects.update_or_create(
            account=social_account,
            defaults={
                "token": token_json.get("access_token", ""),
                "token_secret": token_json.get("refresh_token", ""),
                "expires_at": None,  # Google tokens don't expire
            },
        )
        print("Social tokens saved successfully")

        # Возвращаем информацию о пользователе
        response_data = {
            "user": {
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
            }
        }
        print(
            f"Returning response JSON: {json.dumps(response_data, indent=2, ensure_ascii=False)}"
        )
        print("=== End of social_auth_callback ===\n")
        frontend_url = f"https://localhost:3000/oauth-success?token={token.key}"
        return HttpResponseRedirect(frontend_url)

    except Exception as e:
        print(f"Error in social_auth_callback: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
