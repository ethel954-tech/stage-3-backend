import jwt
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from users.models import User


class JWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get('Authorization', '')
        token = None

        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
        else:
            # Try cookie for web portal
            token = request.COOKIES.get('access_token')

        if not token:
            return None

        try:
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed('Token expired')
        except jwt.InvalidTokenError:
            raise AuthenticationFailed('Invalid token')

        user_id = payload.get('user_id')
        if not user_id:
            raise AuthenticationFailed('Invalid token payload')

        user = User.objects.filter(id=user_id).first()
        if not user:
            raise AuthenticationFailed('User not found')

        if not user.is_active:
            raise AuthenticationFailed('Account is disabled')

        return (user, None)

    def authenticate_header(self, request):
        return 'Bearer'
