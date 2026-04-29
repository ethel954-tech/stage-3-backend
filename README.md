# Insighta Labs+ Backend API

A Django REST API with GitHub OAuth authentication, JWT tokens, and profile intelligence features.

## Features

- **GitHub OAuth 2.0** with PKCE support for both web and CLI
- **JWT Authentication** (access + refresh tokens)
- **Cross-site Authentication** (Netlify frontend ↔ Railway backend)
- **Rate Limiting** on auth endpoints
- **Profile Search** with natural language queries
- **CSV Export** functionality
- **Role-based Access Control** (admin, analyst)

## Tech Stack

- Django 4.x
- Django REST Framework
- PostgreSQL / SQLite
- JWT for token management
- CORS for cross-origin requests

## Quick Start

### Prerequisites

```bash
python >= 3.8
pip
git
```

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/stage-3-backend.git
cd stage-3-backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env

# Apply migrations
python manage.py migrate

# Create superuser (optional)
python manage.py createsuperuser

# Start server
python manage.py runserver 0.0.0.0:8000
```

## Environment Setup

Create a `.env` file with:

```env
# Django
SECRET_KEY=your-django-secret-key
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,your-railway-url.up.railway.app

# Database
DB_ENGINE=django.db.backends.sqlite3
DB_NAME=db.sqlite3

# GitHub OAuth
GITHUB_CLIENT_ID=your_github_app_id
GITHUB_CLIENT_SECRET=your_github_app_secret

# JWT
JWT_SECRET_KEY=your-jwt-secret-key
JWT_ACCESS_TOKEN_EXPIRY_MINUTES=3
JWT_REFRESH_TOKEN_EXPIRY_MINUTES=5

# URLs
BACKEND_URL=https://your-railway-url.up.railway.app
WEB_PORTAL_URL=https://your-netlify-url.netlify.app
```

## API Endpoints

### Authentication

#### GitHub OAuth Flow

```
GET /auth/github
  ?client_type=web|cli
  &redirect_uri=<optional>
  &code_challenge=<optional-for-PKCE>

Response: 302 redirect to GitHub OAuth
```

#### OAuth Callback

```
GET /auth/github/callback
  ?code=<github_auth_code>
  &state=<state_parameter>

Response (web): 302 redirect to dashboard + cookies set
Response (CLI/test_code): 200 JSON with tokens
```

#### CLI Token Exchange

```
POST /auth/cli/exchange
Content-Type: application/json

{
  "code": "github_auth_code",
  "code_verifier": "pkce_code_verifier",
  "redirect_uri": "http://localhost:8765/callback"
}

Response:
{
  "status": "success",
  "access_token": "eyJ0eXAi...",
  "refresh_token": "token123...",
  "user": {...}
}
```

#### Refresh Token

```
POST /auth/refresh
Content-Type: application/json

{
  "refresh_token": "token123..."
}

Response:
{
  "status": "success",
  "access_token": "new_token...",
  "refresh_token": "new_refresh..."
}
```

#### Logout

```
POST /auth/logout
Content-Type: application/json

Response:
{
  "status": "success",
  "message": "Logged out successfully"
}
```

#### Get Current User

```
GET /auth/me
Authorization: Bearer <access_token>

Response:
{
  "status": "success",
  "data": {
    "id": "user_id",
    "username": "username",
    "email": "user@example.com",
    "avatar_url": "https://...",
    "role": "analyst",
    "is_active": true,
    "created_at": "2024-01-01T00:00:00Z",
    "last_login_at": "2024-01-02T00:00:00Z"
  }
}
```

### Profiles API

All profile endpoints require authentication and `X-API-Version: 1` header.

#### List Profiles

```
GET /api/profiles?page=1&limit=10
Authorization: Bearer <access_token>
X-API-Version: 1

Response:
{
  "status": "success",
  "page": 1,
  "limit": 10,
  "total": 5000,
  "total_pages": 500,
  "data": [
    {
      "id": "profile_1",
      "name": "John Doe",
      "gender": "male",
      "gender_probability": 0.95,
      "age": 28,
      "age_group": "adult",
      "country_id": "US",
      "country_name": "United States",
      "country_probability": 0.88,
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

#### Search Profiles

```
GET /api/profiles/search?q=young+males+from+nigeria&page=1&limit=10
Authorization: Bearer <access_token>
X-API-Version: 1

Response: Same as list endpoint
```

#### Get Profile Detail

```
GET /api/profiles/{id}
Authorization: Bearer <access_token>
X-API-Version: 1

Response: Single profile object
```

#### Export CSV

```
GET /api/profiles/export?gender=male&age_group=adult
Authorization: Bearer <access_token>
X-API-Version: 1

Response: CSV file download
```

## Authentication Methods

### Web (Browser)

```javascript
// 1. Login via GitHub OAuth
window.location.href = "https://api.example.com/auth/github?client_type=web"

// 2. After callback, cookies automatically set:
// - access_token (HttpOnly, Secure, SameSite=None)
// - refresh_token (HttpOnly, Secure, SameSite=None)

// 3. API calls include cookies automatically:
fetch("https://api.example.com/api/profiles", {
  credentials: "include",  // Include cookies
  headers: { "X-API-Version": "1" }
})
```

### CLI / Programmatic

```bash
# 1. Initiate OAuth
curl "https://api.example.com/auth/github?client_type=cli&redirect_uri=http://localhost:8765/callback"

# 2. Capture authorization code (or use test_code)

# 3. Exchange code for tokens
curl -X POST "https://api.example.com/auth/cli/exchange" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "github_code_or_test_code",
    "code_verifier": "pkce_verifier",
    "redirect_uri": "http://localhost:8765/callback"
  }'

# 4. Use Bearer token in requests
curl -H "Authorization: Bearer ACCESS_TOKEN" \
     -H "X-API-Version: 1" \
     https://api.example.com/api/profiles
```

### Testing with test_code

For automated testing, use special code `test_code`:

```bash
curl -X POST "https://api.example.com/auth/github/callback" \
  -H "Content-Type: application/json" \
  -d '{"code": "test_code", "state": "any_state"}'

# Returns dummy test tokens:
{
  "status": "success",
  "access_token": "test_token_...",
  "refresh_token": "test_refresh_...",
  "user": {
    "id": "test_user_123",
    "username": "test_user",
    "email": "test@example.com",
    "role": "analyst"
  }
}
```

## Security Features

### Rate Limiting

- `/auth/` endpoints: 10 requests per minute per IP
- `/api/` endpoints: 60 requests per minute per user
- Exceeds limit returns: `HTTP 429 Too Many Requests`

### API Versioning

All API endpoints require header:
```
X-API-Version: 1
```

Missing header returns:
```
HTTP 400 Bad Request
{"status": "error", "message": "API version header required"}
```

### PKCE Support

For CLI applications, use PKCE (Proof Key for Code Exchange):

```bash
# Generate code_verifier
code_verifier=$(openssl rand -base64 32 | sed 's/=*$//' | tr '+/' '-_')

# Generate code_challenge
code_challenge=$(echo -n "$code_verifier" | sha256sum | cut -c1-64 | base64 | sed 's/=*$//' | tr '+/' '-_')

# Request auth with code_challenge
# Exchange code with code_verifier for validation
```

### Cross-Site Authentication

Frontend (Netlify) ↔ Backend (Railway) HTTPS

Cookies configured:
- `HttpOnly`: True (prevents JavaScript access)
- `Secure`: True (HTTPS only)
- `SameSite`: None (allows cross-site)

## Database Models

### User

```python
- id: UUID
- github_id: String (unique)
- username: String
- email: String
- avatar_url: String
- role: Enum (admin, analyst)
- is_active: Boolean
- created_at: DateTime
- last_login_at: DateTime
```

### Profile

```python
- id: UUID
- name: String
- gender: String (male, female)
- gender_probability: Float (0-1)
- age: Integer
- age_group: Enum (child, teenager, adult, senior)
- country_id: String (ISO 3166-1 alpha-2)
- country_name: String
- country_probability: Float (0-1)
- created_at: DateTime
- updated_at: DateTime
```

### RefreshToken

```python
- id: UUID
- user: ForeignKey(User)
- token_hash: String (unique)
- is_revoked: Boolean
- expires_at: DateTime
- created_at: DateTime
```

## Project Structure

```
stage-3-backend/
├── manage.py
├── requirements.txt
├── README.md
├── .env.example
├── db.sqlite3
├── backend1/                 # Main Django project settings
│   ├── settings.py
│   ├── urls.py
│   ├── middleware.py
│   ├── wsgi.py
│   └── asgi.py
├── authapp/                 # Authentication app
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   ├── utils.py
│   └── migrations/
├── profiles/                # Profiles app
│   ├── models.py
│   ├── views.py
│   ├── serializers.py
│   ├── urls.py
│   ├── authentication.py
│   └── migrations/
├── users/                   # Users app
│   ├── models.py
│   ├── admin.py
│   └── migrations/
└── .github/
    └── workflows/
        └── ci.yml
```

## Deployment

### Railway

```bash
# Set environment variables in Railway dashboard
# Push code
git push origin main

# Railway auto-deploys from main branch
```

### Database Migrations

```bash
# Apply migrations on deployment
python manage.py migrate
```

## Testing

```bash
# Run tests
python manage.py test

# Test specific scenario
# test_code flow
curl -X POST "http://localhost:8000/auth/github/callback" \
  -d "code=test_code&state=test_state"

# Rate limiting (hit 11+ times)
for i in {1..15}; do
  curl "http://localhost:8000/auth/github"
done
```

## Troubleshooting

### 401 Unauthorized on API calls

- Check cookies/tokens present
- Verify Bearer header format
- Ensure credentials: 'include' in fetch

### CORS errors

- Verify frontend URL in CORS_ALLOWED_ORIGINS
- Check CORS_ALLOW_CREDENTIALS = True

### test_code returns 400

- Ensure code is exactly "test_code"
- Include state parameter

## Performance

Expected response times:
- `/auth/github`: ~50ms
- `/auth/github/callback`: ~500-1000ms
- `/api/profiles`: ~100-200ms
- `/api/profiles/search`: ~200-500ms

## License

MIT License


```
┌─────────┐    ┌──────────┐    ┌─────────┐    ┌──────────┐
│  User   │───▶│ insighta │───▶│  Local  │───▶│ Browser  │
│         │    │  login   │    │  Server │    │ GitHub   │
└─────────┘    └──────────┘    └────┬────┘    └────┬─────┘
                                     │              │
                                     │◄─────────────│
                                     │   callback   │
                                     │              │
                              ┌──────▼──────┐       │
                              │  Backend    │◄──────┘
                              │ /auth/cli/  │  code+verifier
                              │  exchange   │
                              └──────┬──────┘
                                     │
                              ┌──────▼──────┐
                              │  Tokens     │
                              │  Stored at  │
                              │~/.insighta/ │
                              │credentials  │
                              └─────────────┘
```

1. `insighta login` generates PKCE `code_verifier`, `code_challenge`, and `state`
2. Starts temporary HTTP server on `localhost:8765`
3. Opens GitHub OAuth in browser
4. GitHub redirects to `localhost:8765/callback` with `code` + `state`
5. CLI validates state, sends `code + code_verifier` to backend
6. Backend exchanges with GitHub, creates/updates user, issues tokens
7. CLI stores tokens at `~/.insighta/credentials.json`

### Web Portal (HTTP-Only Cookies)

1. User clicks "Continue with GitHub"
2. Backend redirects to GitHub OAuth (`client_type=web`)
3. GitHub redirects to backend callback
4. Backend issues tokens as **HTTP-only cookies** (`access_token`, `refresh_token`)
5. CSRF token included for state-changing requests
6. JavaScript cannot read tokens (XSS protection)

---

## 🖥️ CLI Usage

### Installation

```bash
cd cli
pip install -e .
```

### Commands

```bash
# Authentication
insighta login              # GitHub OAuth with PKCE
insighta logout             # Clear credentials
insighta whoami             # Show current user

# Profiles
insighta profiles list                              # List all
insighta profiles list --gender male                # Filter by gender
insighta profiles list --country NG --age-group adult
insighta profiles list --min-age 25 --max-age 40
insighta profiles list --sort-by age --order desc
insighta profiles list --page 2 --limit 20

insighta profiles get <id>                          # Get single profile
insighta profiles search "young males from nigeria" # Natural language
insighta profiles create --name "Harriet Tubman"    # Admin only
insighta profiles export --format csv               # Export to CSV
```

### Global Install

```bash
pip install -e .
insighta login  # works from any directory
```

---

## 🔑 Token Handling Approach

### Access Token
- **Type**: JWT (HS256)
- **Expiry**: 3 minutes
- **Storage**: 
  - CLI: `~/.insighta/credentials.json`
  - Web: HTTP-only cookie
- **Transmission**: `Authorization: Bearer <token>` header or cookie

### Refresh Token
- **Type**: Random 64-byte token (SHA-256 hashed in DB)
- **Expiry**: 5 minutes
- **Rotation**: Each refresh invalidates the old token and issues a new pair
- **Storage**: Same as access token but never exposed to JavaScript

### Auto-Refresh (CLI)
```python
if response.status_code == 401:
    new_token = refresh_access_token()  # POST /auth/refresh
    if new_token:
        retry_request()
    else:
        prompt_relogin()
```

### Logout
- POST `/auth/logout` with refresh token
- Server revokes the refresh token in DB
- Client clears local storage

---

## 👮 Role Enforcement Logic

### Roles
| Role   | Permissions                          |
|--------|--------------------------------------|
| admin  | Full access: create, delete, read    |
| analyst| Read-only: list, get, search, export |

### Enforcement
All `/api/*` endpoints pass through `JWTAuthMiddleware` + DRF permission classes:

```python
class IsAuthenticated(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_active)

class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return user and user.is_active and user.role == 'admin'
```

### Endpoint Map
| Endpoint          | Auth Required | Role Required |
|-------------------|---------------|---------------|
| GET /api/profiles | Yes           | Any           |
| GET /api/profiles/export | Yes    | Any           |
| GET /api/profiles/search | Yes    | Any           |
| GET /api/profiles/<id> | Yes      | Any           |
| POST /api/profiles | Yes          | Admin only    |
| DELETE /api/profiles/<id> | Yes   | Admin only    |

### Inactive Users
If `is_active=False` → **403 Forbidden** on all requests.

---

## 🧠 Natural Language Parsing Approach

The search endpoint (`GET /api/profiles/search/?q=...`) uses a **rule-based parser** built with Python's `re` module.

### 1. Keyword Detection

#### Gender
- `male`, `males`, `men`, `boys` → `gender=male`
- `female`, `females`, `women`, `girls`, `ladies` → `gender=female`
- **Conflict Rule**: If both appear → no gender filter

#### Age Groups
- `adult`, `adults` → `age_group=adult`
- `teen`, `teens`, `teenager`, `teenagers` → `age_group=teenager`

#### "Young" Mapping
- `young` → age 16–24 (`min_age=16`, `max_age=24`)

#### Numeric Conditions
- `above 30`, `over 30` → `age__gte=30`
- `below 20`, `under 20` → `age__lte=20`

#### Country Mapping
| Keyword      | Code |
|--------------|------|
| nigeria      | NG   |
| kenya        | KE   |
| angola       | AO   |
| usa, america | US   |
| uk, britain  | GB   |
| benin        | BJ   |
| ghana        | GH   |
| south africa | ZA   |

### 2. Combined Query Handling

| Query | Filters Applied |
|-------|-----------------|
| `young males` | gender=male, age 16-24 |
| `females above 30` | gender=female, age>=30 |
| `people from nigeria` | country_id=NG |
| `adult males from kenya` | gender=male, age_group=adult, country=KE |

---

## 📡 API Endpoints

### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/auth/github` | Redirect to GitHub OAuth |
| GET | `/auth/github/callback` | OAuth callback handler |
| POST | `/auth/refresh` | Rotate refresh token |
| POST | `/auth/logout` | Invalidate refresh token |
| GET | `/auth/me` | Get current user |

### Profiles
| Method | Endpoint | Auth | Role |
|--------|----------|------|------|
| GET | `/api/profiles` | Bearer/Cookie | Any |
| POST | `/api/profiles` | Bearer/Cookie | Admin |
| GET | `/api/profiles/<id>` | Bearer/Cookie | Any |
| DELETE | `/api/profiles/<id>` | Bearer/Cookie | Admin |
| GET | `/api/profiles/search/?q=` | Bearer/Cookie | Any |
| GET | `/api/profiles/export?format=csv` | Bearer/Cookie | Any |

### Headers Required
```
X-API-Version: 1
Authorization: Bearer <access_token>  # CLI
# OR cookie-based for web portal
```

---

## 🛡️ Security Features

| Feature | Implementation |
|---------|----------------|
| OAuth with PKCE | CLI generates code_verifier + code_challenge |
| HTTP-Only Cookies | Web tokens not accessible via JavaScript |
| CSRF Protection | CSRF token required for state-changing requests |
| Rate Limiting | 10/min auth, 60/min API per user |
| Token Rotation | Refresh tokens invalidated on use |
| Short Expiry | 3 min access, 5 min refresh |
| Role Enforcement | Structured permission classes |
| Request Logging | Method, endpoint, status, response time |

---

## ⚙️ Setup Instructions

### Backend

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Copy environment variables
cp .env.example .env
# Edit .env with your GitHub OAuth credentials

# 3. Run migrations
python manage.py migrate

# 4. Seed database (optional)
python manage.py seed_profiles

# 5. Run server
python manage.py runserver
```

### CLI

```bash
cd cli
pip install -e .
insighta login
```

### Web Portal

Open `web-portal/index.html` in a browser or serve via any static file server.

---

## 🧪 Testing

```bash
# Run Django tests
python manage.py test

# Test auth flow
curl -X POST http://localhost:8000/auth/refresh \
  -H "Content-Type: application/json" \
  -H "X-API-Version: 1" \
  -d '{"refresh_token": "your-token"}'

# Test profiles (authenticated)
curl http://localhost:8000/api/profiles \
  -H "Authorization: Bearer <token>" \
  -H "X-API-Version: 1"
```

---

## 📁 Repository Structure

```
backend2/
├── backend1/           # Django project settings
├── users/              # User model & auth backend
├── authapp/            # OAuth & token management
├── profiles/           # Profile APIs (Stage 2 + updates)
├── cli/                # Insighta CLI tool
│   └── insighta/
├── web-portal/         # Web portal frontend
├── .github/workflows/  # CI/CD
├── requirements.txt
└── README.md
```

---

## 🚀 Deployment

### Backend
- Set `DEBUG=False` in production
- Set `ALLOWED_HOSTS` to your domain
- Use PostgreSQL instead of SQLite for production
- Set strong `SECRET_KEY` and `JWT_SECRET_KEY`

### Web Portal
- Deploy as static site (Netlify, Vercel, GitHub Pages)
- Update `API_BASE_URL` in portal JavaScript to your backend URL

### CLI
- Installable globally via `pip install -e .`
- Configure `INSIGHTA_BACKEND_URL` environment variable for custom backends

---

Built for Insighta Labs+ Stage 3.
