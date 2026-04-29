import requests
from rest_framework import serializers

from .models import Profile


class ExternalAPIError(Exception):
    def __init__(self, external_api):
        self.external_api = external_api
        super().__init__(f"{external_api} returned an invalid response")


def get_age_group(age):
    if age is None:
        return None
    if age is None: return None
    if age <= 12: return "child"
    if age <= 19: return "teenager"
    if age <= 59: return "adult"
    return "senior"

def get_full_country_name(code):
    mapping = {
        "NG": "Nigeria", "BJ": "Benin", "KE": "Kenya", "GH": "Ghana", 
        "ZA": "South Africa", "AO": "Angola", "US": "United States", 
        "GB": "United Kingdom", "CA": "Canada", "AU": "Australia", 
        "DE": "Germany", "FR": "France", "IN": "India", "BR": "Brazil",
        "TG": "Togo", "UG": "Uganda", "RW": "Rwanda", "EG": "Egypt", "MA": "Morocco"
    }
    return mapping.get(code.upper(), code.upper() if code else None)


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = [
            "id",
            "name",
            "gender",
            "gender_probability",
            "sample_size",
            "age",
            "age_group",
            "country_id",
            "country_name",
            "country_probability",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class ProfileListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = [
            "id",
            "name",
            "gender",
            "age",
            "age_group",
            "country_id",
            "country_name",
            "gender_probability",
            "country_probability",
            "created_at",
        ]


class ProfileCreateSerializer(serializers.Serializer):
    name = serializers.CharField()

    def validate_name(self, value):
        if not isinstance(value, str):
            raise serializers.ValidationError("Invalid type")

        cleaned_value = value.strip()
        if not cleaned_value:
            raise serializers.ValidationError("Missing or empty name")

        return cleaned_value.lower()

    def _get_json(self, url):
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except:
            return {}

    def create(self, validated_data):
        name = validated_data["name"]

        gender_data = self._get_json(f"https://api.genderize.io?name={name}")
        age_data = self._get_json(f"https://api.agify.io?name={name}")
        country_data = self._get_json(f"https://api.nationalize.io?name={name}")

        gender = gender_data.get("gender")
        gender_probability = gender_data.get("probability", 0.0)
        sample_size = gender_data.get("count", 0)

        age = age_data.get("age")
        age_group = get_age_group(age)

        countries = country_data.get("country", [])
        country_id = None
        country_name = None
        country_probability = 0.0
        if countries:
            top_country = max(countries, key=lambda item: item["probability"])
            country_id = top_country.get("country_id")
            country_probability = top_country.get("probability", 0.0)
            country_name = get_full_country_name(country_id)

        return Profile.objects.create(
            name=name,
            gender=gender,
            gender_probability=gender_probability,
            sample_size=sample_size,
            age=age,
            age_group=age_group,
            country_id=country_id,
            country_name=country_name,
            country_probability=country_probability,
        )
