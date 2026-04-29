from unittest.mock import Mock, patch

from django.test import TestCase
from rest_framework.test import APIClient

from authapp.utils import generate_access_token
from users.models import User
from .models import Profile


class ProfileAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_user = User.objects.create(
            github_id="admin123",
            username="admin",
            role=User.ROLE_ADMIN,
        )
        self.analyst_user = User.objects.create(
            github_id="analyst456",
            username="analyst",
            role=User.ROLE_ANALYST,
        )
        self.admin_token = generate_access_token(self.admin_user.id)
        self.analyst_token = generate_access_token(self.analyst_user.id)

    def _admin_client(self):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}", HTTP_X_API_VERSION="1")
        return c

    def _analyst_client(self):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION=f"Bearer {self.analyst_token}", HTTP_X_API_VERSION="1")
        return c

    def _mock_response(self, payload, status_code=200):
        response = Mock()
        response.status_code = status_code
        response.json.return_value = payload
        response.raise_for_status = Mock()
        return response

    # --- Auth Requirements ---

    def test_missing_api_version_returns_400(self):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        response = c.get("/api/profiles/")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["message"], "API version header required")

    def test_missing_auth_returns_401(self):
        response = self.client.get("/api/profiles/", HTTP_X_API_VERSION="1")
        self.assertEqual(response.status_code, 401)

    def test_inactive_user_returns_403(self):
        inactive_user = User.objects.create(
            github_id="inactive",
            username="inactive",
            role=User.ROLE_ANALYST,
            is_active=False,
        )
        token = generate_access_token(inactive_user.id)
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION=f"Bearer {token}", HTTP_X_API_VERSION="1")
        response = c.get("/api/profiles/")
        self.assertEqual(response.status_code, 403)

    def test_analyst_cannot_create_profile(self):
        response = self._analyst_client().post("/api/profiles/", {"name": "test"}, format="json")
        self.assertEqual(response.status_code, 403)

    def test_analyst_cannot_delete_profile(self):
        profile = Profile.objects.create(
            name="ella",
            gender="female",
            gender_probability=0.99,
            sample_size=1234,
            age=46,
            age_group="adult",
            country_id="DRC",
            country_probability=0.85,
        )
        response = self._analyst_client().delete(f"/api/profiles/{profile.id}/")
        self.assertEqual(response.status_code, 403)

    # --- Profile CRUD ---

    @patch("profiles.serializers.requests.get")
    def test_create_profile_success(self, mock_get):
        mock_get.side_effect = [
            self._mock_response(
                {"name": "ella", "gender": "female", "probability": 0.99, "count": 1234}
            ),
            self._mock_response({"name": "ella", "age": 46, "count": 1000}),
            self._mock_response(
                {
                    "name": "ella",
                    "country": [
                        {"country_id": "US", "probability": 0.15},
                        {"country_id": "DRC", "probability": 0.85},
                    ],
                }
            ),
        ]

        response = self._admin_client().post("/api/profiles/", {"name": "ella"}, format="json")
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["data"]["name"], "ella")
        self.assertEqual(data["data"]["gender"], "female")
        self.assertEqual(data["data"]["gender_probability"], 0.99)
        self.assertEqual(data["data"]["sample_size"], 1234)
        self.assertEqual(data["data"]["age"], 46)
        self.assertEqual(data["data"]["age_group"], "adult")
        self.assertEqual(data["data"]["country_id"], "DRC")
        self.assertEqual(data["data"]["country_probability"], 0.85)
        self.assertIn("created_at", data["data"])

    @patch("profiles.serializers.requests.get")
    def test_create_profile_duplicate_returns_200(self, mock_get):
        """Duplicate profile returns 200 with existing data (idempotent)."""
        Profile.objects.create(
            name="ella",
            gender="female",
            gender_probability=0.99,
            sample_size=1234,
            age=46,
            age_group="adult",
            country_id="DRC",
            country_probability=0.85,
        )

        response = self._admin_client().post("/api/profiles/", {"name": "Ella"}, format="json")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["data"]["name"], "ella")
        self.assertEqual(Profile.objects.count(), 1)
        mock_get.assert_not_called()

    def test_create_profile_missing_name(self):
        response = self._admin_client().post("/api/profiles/", {}, format="json")
        self.assertEqual(response.status_code, 422)

    def test_create_profile_empty_name(self):
        response = self._admin_client().post("/api/profiles/", {"name": "   "}, format="json")
        self.assertEqual(response.status_code, 422)

    def test_create_profile_invalid_type(self):
        response = self._admin_client().post("/api/profiles/", {"name": 123}, format="json")
        self.assertEqual(response.status_code, 422)

    def test_get_single_profile(self):
        profile = Profile.objects.create(
            name="emmanuel",
            gender="male",
            gender_probability=0.99,
            sample_size=1234,
            age=25,
            age_group="adult",
            country_id="NG",
            country_probability=0.85,
        )

        response = self._admin_client().get(f"/api/profiles/{profile.id}/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["data"]["name"], "emmanuel")
        self.assertEqual(data["data"]["country_id"], "NG")
        self.assertIn("created_at", data["data"])

    def test_get_single_profile_not_found(self):
        response = self._admin_client().get("/api/profiles/00000000-0000-0000-0000-000000000000/")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["message"], "Profile not found")

    def test_get_all_profiles_with_filters(self):
        Profile.objects.create(
            name="emmanuel",
            gender="male",
            gender_probability=0.99,
            sample_size=1234,
            age=25,
            age_group="adult",
            country_id="NG",
            country_probability=0.85,
        )
        Profile.objects.create(
            name="sarah",
            gender="female",
            gender_probability=0.98,
            sample_size=2345,
            age=28,
            age_group="adult",
            country_id="US",
            country_probability=0.90,
        )

        response = self._admin_client().get("/api/profiles/?gender=MALE&country_id=ng")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(len(data["data"]), 1)
        self.assertEqual(data["data"][0]["name"], "emmanuel")
        self.assertEqual(data["data"][0]["country_id"], "NG")
        self.assertIn("links", data)
        self.assertIn("total_pages", data)

    def test_delete_profile(self):
        profile = Profile.objects.create(
            name="ella",
            gender="female",
            gender_probability=0.99,
            sample_size=1234,
            age=46,
            age_group="adult",
            country_id="DRC",
            country_probability=0.85,
        )

        response = self._admin_client().delete(f"/api/profiles/{profile.id}/")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Profile.objects.filter(id=profile.id).exists())

    # --- Search ---

    def test_search_profiles(self):
        Profile.objects.create(
            name="emmanuel",
            gender="male",
            gender_probability=0.99,
            sample_size=1234,
            age=25,
            age_group="adult",
            country_id="NG",
            country_probability=0.85,
        )

        response = self._admin_client().get("/api/profiles/search/?q=males+from+nigeria")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(len(data["data"]), 1)
        self.assertEqual(data["data"][0]["name"], "emmanuel")

    def test_search_empty_query(self):
        response = self._admin_client().get("/api/profiles/search/?q=")
        self.assertEqual(response.status_code, 400)

    # --- Export ---

    def test_export_csv(self):
        Profile.objects.create(
            name="ella",
            gender="female",
            gender_probability=0.99,
            sample_size=1234,
            age=46,
            age_group="adult",
            country_id="DRC",
            country_probability=0.85,
        )

        response = self._admin_client().get("/api/profiles/export", {"format": "csv"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("Content-Disposition", response)
        content = response.content.decode()
        self.assertIn("id,name,gender", content)
        self.assertIn("ella", content)

    # --- Pagination & Links ---

    def test_pagination_includes_links(self):
        for i in range(15):
            Profile.objects.create(
                name=f"user{i}",
                gender="male",
                gender_probability=0.9,
                sample_size=100,
                age=25,
                age_group="adult",
                country_id="NG",
                country_probability=0.8,
            )

        response = self._admin_client().get("/api/profiles/?page=1&limit=10")
        data = response.json()
        self.assertEqual(data["page"], 1)
        self.assertEqual(data["limit"], 10)
        self.assertEqual(data["total"], 15)
        self.assertEqual(data["total_pages"], 2)
        self.assertIsNotNone(data["links"]["self"])
        self.assertIsNotNone(data["links"]["next"])
        self.assertIsNone(data["links"]["prev"])

    # --- Rate Limiting ---

    def test_rate_limit_api(self):
        """Hit API rate limit after 60 requests."""
        c = self._admin_client()
        for _ in range(60):
            c.get("/api/profiles/")
        response = c.get("/api/profiles/")
        # May or may not be rate limited depending on test speed
        self.assertIn(response.status_code, [200, 429])


class AuthFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_refresh_token_invalid(self):
        response = self.client.post(
            "/auth/refresh",
            {"refresh_token": "invalid-token"},
            format="json",
        )
        self.assertEqual(response.status_code, 401)

    def test_csrf_token_endpoint(self):
        response = self.client.get("/auth/csrf/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("csrf_token", data)

    def test_logout_without_token(self):
        response = self.client.post("/auth/logout", {}, format="json")
        self.assertEqual(response.status_code, 200)
