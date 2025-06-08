from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from django.utils import timezone
from django.conf import settings

class Admin2FAMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Разрешаем доступ к логину и логауту всегда
        if request.path in ['/admin/login/', '/admin/logout/']:
            return self.get_response(request)

        if request.path.startswith('/admin/'):
            if request.user.is_authenticated and request.user.is_staff:
                if not request.session.get('admin_2fa_verified'):
                    if request.path != '/admin/verify-2fa/':
                        return redirect('admin_verify_2fa')
        
        response = self.get_response(request)
        return response 