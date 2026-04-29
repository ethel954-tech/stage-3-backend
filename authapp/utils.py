import jwt
from datetime import datetime, timedelta
from django.conf import settings


def generate_access_token(user_id):
    payload = {
        'user_id': str(user_id),
        'exp': datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRY_MINUTES),
        'iat': datetime.utcnow(),
        'type': 'access'
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm='HS256')


def generate_refresh_token(user_id):
    from authapp.models import RefreshToken
    token = RefreshToken.generate_token()
    token_hash = RefreshToken.hash_token(token)
    expires_at = datetime.utcnow() + timedelta(minutes=settings.JWT_REFRESH_TOKEN_EXPIRY_MINUTES)
    RefreshToken.objects.create(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at
    )
    return token


def decode_token(token):
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

