import time
import jwt
import re
from django.http import JsonResponse
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from users.models import User


class APIVersionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith('/api/'):
            version = request.headers.get('X-API-Version')
            if not version:
                return JsonResponse(
                    {"status": "error", "message": "API version header required"},
                    status=400
                )
            if version != '1':
                return JsonResponse(
                    {"status": "error", "message": "Unsupported API version"},
                    status=400
                )
        response = self.get_response(request)
        return response


class RateLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.requests = {}

    def _get_client_id(self, request):
        # Use user ID if authenticated, otherwise IP
        if hasattr(request, 'user') and request.user and getattr(request.user, 'id', None):
            return str(request.user.id)
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded:
            return x_forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')

    def __call__(self, request):
        if request.path.startswith('/auth/'):
            limit = 10
            window = 60
        elif request.path.startswith('/api/'):
            limit = 60
            window = 60
        else:
            return self.get_response(request)

        client_id = self._get_client_id(request)
        key = f"{client_id}:{request.path.split('/')[1]}"
        now = time.time()

        if key not in self.requests:
            self.requests[key] = []

        # Clean old requests
        self.requests[key] = [t for t in self.requests[key] if now - t < window]

        if len(self.requests[key]) >= limit:
            return JsonResponse(
                {"status": "error", "message": "Rate limit exceeded. Try again later."},
                status=429
            )

        self.requests[key].append(now)
        response = self.get_response(request)
        return response


class RequestLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.time()
        response = self.get_response(request)
        duration = int((time.time() - start_time) * 1000)

        print(
            f"[{request.method}] {request.path} | "
            f"Status: {response.status_code} | "
            f"Time: {duration}ms"
        )
        return response


class JWTAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.user = None
        request.auth_user = None

        # Skip auth for OAuth endpoints and admin
        if request.path.startswith('/auth/') or request.path.startswith('/admin/'):
            return self.get_response(request)

        # Try to get token from Authorization header first
        auth_header = request.headers.get('Authorization', '')
        token = None

        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
            print(f"[JWT] Bearer token found in Authorization header")

        # Try to get token from cookie (for web portal, cross-site)
        if not token:
            token = request.COOKIES.get('access_token')
            if token:
                print(f"[JWT] Token found in access_token cookie")

        if not token:
            if request.path.startswith('/api/'):
                print(f"[JWT] No token for {request.method} {request.path}")
                return JsonResponse(
                    {"status": "error", "message": "Authentication required"},
                    status=401
                )
            return self.get_response(request)

        try:
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=['HS256'])
            user_id = payload.get('user_id')
            if user_id:
                user = User.objects.filter(id=user_id).first()
                if user and user.is_active:
                    request.user = user
                    request.auth_user = user
                    print(f"[JWT] Authenticated as {user.username}")
                elif user and not user.is_active:
                    print(f"[JWT] Account disabled: {user.username}")
                    return JsonResponse(
                        {"status": "error", "message": "Account is disabled"},
                        status=403
                    )
                else:
                    print(f"[JWT] User not found: {user_id}")
        except jwt.ExpiredSignatureError:
            print(f"[JWT] Token expired")
            if request.path.startswith('/api/'):
                return JsonResponse(
                    {"status": "error", "message": "Token expired"},
                    status=401
                )
        except jwt.InvalidTokenError as e:
            print(f"[JWT] Invalid token: {str(e)}")
            if request.path.startswith('/api/'):
                return JsonResponse(
                    {"status": "error", "message": "Invalid token"},
                    status=401
                )

        if request.path.startswith('/api/') and not getattr(request, 'user', None):
            print(f"[JWT] API access denied for {request.method} {request.path}")
            return JsonResponse(
                {"status": "error", "message": "Authentication required"},
                status=401
            )

        return self.get_response(request)

