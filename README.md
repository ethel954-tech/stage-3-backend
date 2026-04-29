# Insighta Labs+

Secure Access & Multi-Interface Integration for the Profile Intelligence System.

---

## 🏗️ System Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   CLI Tool      │     │   Web Portal    │     │   Direct API    │
│   (insighta)    │     │   (HTTP-Only)   │     │   (Headers)     │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │      Django Backend     │
                    │  ┌─────────────────┐    │
                    │  │  JWT Auth MW    │    │
                    │  │  Rate Limit MW  │    │
                    │  │  API Version MW │    │
                    │  │  Request Log MW │    │
                    │  └─────────────────┘    │
                    │  ┌─────────────────┐    │
                    │  │   Auth Module   │    │
                    │  │  (GitHub OAuth) │    │
                    │  └─────────────────┘    │
                    │  ┌─────────────────┐    │
                    │  │ Profiles Module │    │
                    │  │ (CRUD + Search) │    │
                    │  └─────────────────┘    │
                    │  ┌─────────────────┐    │
                    │  │  Users Module   │    │
                    │  │  (RBAC + JWT)   │    │
                    │  └─────────────────┘    │
                    └─────────────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │      SQLite Database    │
                    │  users | profiles       │
                    │  refresh_tokens         │
                    └─────────────────────────┘
```

---

## 🔐 Authentication Flow

### CLI (PKCE)

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
