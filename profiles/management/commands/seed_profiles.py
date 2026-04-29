import json
import os
from django.conf import settings
from django.core.management.base import BaseCommand
from profiles.models import Profile

class Command(BaseCommand):
    help = 'Seeds the database with profiles from the local seed_profiles.json file'

    def get_country_name(self, country_id):
        """Mapping for country names if not provided in JSON."""
        country_names = {
            "US": "United States",
            "NG": "Nigeria",
            "KE": "Kenya",
            "GB": "United Kingdom",
            "CA": "Canada",
            "AU": "Australia",
            "DE": "Germany",
            "FR": "France",
            "IN": "India",
            "BR": "Brazil",
            "ZA": "South Africa",
            "GH": "Ghana",
            "BJ": "Benin",
            "AO": "Angola"
        }
        if not country_id:
            return "Unknown"
        return country_names.get(country_id.upper(), country_id.upper())

    def handle(self, *args, **options):
        file_path = os.path.join(settings.BASE_DIR, 'seed_profiles.json')
        
        if not os.path.exists(file_path):
            self.stderr.write(f"Error: File not found at {file_path}")
            return

        self.stdout.write(f"Reading data from {file_path}...")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
            
            # Handle the nested structure: {"profiles": [...]}
            data = raw_data.get('profiles', [])
            if not isinstance(data, list):
                data = raw_data if isinstance(raw_data, list) else []
            
            # Get all existing names in lowercase for fast lookup
            existing_names = set(Profile.objects.values_list('name', flat=True))
            
            profiles_to_create = []
            for item in data:
                name_raw = item.get('name', '')
                if not name_raw:
                    continue
                
                name_lower = name_raw.strip().lower()
                
                # Idempotency check: skip if name already exists
                if name_lower not in existing_names:
                    country_id = item.get('country_id')
                    # Ensure country_name is always filled
                    country_name = item.get('country_name') or self.get_country_name(country_id)
                    
                    profiles_to_create.append(Profile(
                        name=name_lower,
                        gender=item.get('gender'),
                        gender_probability=item.get('gender_probability', 0.0),
                        sample_size=item.get('sample_size', 0),
                        age=item.get('age'),
                        age_group=item.get('age_group'),
                        country_id=country_id,
                        country_name=country_name,
                        country_probability=item.get('country_probability', 0.0)
                    ))
                    # Add to tracking set to prevent duplicates within the same JSON file
                    existing_names.add(name_lower)
            
            if profiles_to_create:
                Profile.objects.bulk_create(profiles_to_create)
                self.stdout.write(self.style.SUCCESS(f"Seeded {len(profiles_to_create)} profiles"))
            elif not data:
                self.stderr.write("No profiles found in JSON file.")
            else:
                self.stdout.write("Database already seeded.")

        except json.JSONDecodeError as e:
            self.stderr.write(f"Invalid JSON data: {e}")