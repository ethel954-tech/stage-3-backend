import re
from django.db.models import Q, Min, Max
from rest_framework import status as http_status
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from .models import Profile
from .serializers import ProfileCreateSerializer, ProfileListSerializer, ProfileSerializer


class ProfileViewSet(ViewSet):
    def get_queryset(self):
        return Profile.objects.all()

    def list(self, request):
        queryset = self.get_queryset().order_by('-created_at')
        
        # Filters
        params = request.query_params
        gender = params.get('gender')
        age_group = params.get('age_group')
        country_id = params.get('country_id')
        min_age = params.get('min_age')
        max_age = params.get('max_age')
        min_gender_prob = params.get('min_gender_probability')
        min_country_prob = params.get('min_country_probability')

        if gender:
            queryset = queryset.filter(gender__iexact=gender)
        if age_group:
            queryset = queryset.filter(age_group__iexact=age_group)
        if country_id:
            queryset = queryset.filter(country_id__iexact=country_id)
        if min_age:
            try:
                queryset = queryset.filter(age__gte=int(min_age))
            except ValueError:
                return Response({"status": "error", "message": "Invalid query parameters"}, status=422)
        if max_age:
            try:
                queryset = queryset.filter(age__lte=int(max_age))
            except ValueError:
                return Response({"status": "error", "message": "Invalid query parameters"}, status=422)
        if min_gender_prob:
            try:
                queryset = queryset.filter(gender_probability__gte=float(min_gender_prob))
            except ValueError:
                return Response({"status": "error", "message": "Invalid query parameters"}, status=422)
        if min_country_prob:
            try:
                queryset = queryset.filter(country_probability__gte=float(min_country_prob))
            except ValueError:
                return Response({"status": "error", "message": "Invalid query parameters"}, status=422)

        # Sorting
        sort_by = params.get('sort_by', 'created_at')
        order = params.get('order', 'desc')
        if order not in ['asc', 'desc']:
            return Response({"status": "error", "message": "Invalid query parameters"}, status=422)
        
        sort_fields = {
            'age': 'age',
            'created_at': 'created_at',
            'gender_probability': 'gender_probability',
        }
        if sort_by in sort_fields:
            sort_field = sort_fields[sort_by]
            direction = '' if order == 'asc' else '-'
            queryset = queryset.order_by(direction + sort_field)
        else:
            queryset = queryset.order_by('-created_at')

        try:
            # Pagination
            page = max(1, int(params.get('page', 1)))
            limit = min(50, max(1, int(params.get('limit', 10))))
        except ValueError:
            return Response({"status": "error", "message": "Invalid query parameters"}, status=422)

        total = queryset.count()
        start = (page - 1) * limit
        end = start + limit
        paginated_data = queryset[start:end]

        serializer = ProfileListSerializer(paginated_data, many=True)

        return Response({
            "status": "success",
            "page": page,
            "limit": limit,
            "total": total,
            "data": serializer.data,
        })

    def search(self, request):
        q = request.query_params.get('q', '').strip().lower()
        if not q:
            return Response({"status": "error", "message": "Missing or empty parameter"}, status=400)

        filters = self._parse_query(q)
        if not filters:
            return Response({"status": "error", "message": "Unable to interpret query"}, status=400)

        queryset = self.get_queryset()
        q_obj = Q()
        
        for field, value in filters.items():
            if field == 'min_age':
                q_obj &= Q(age__gte=value)
            elif field == 'max_age':
                q_obj &= Q(age__lte=value)
            elif field == 'gender':
                q_obj &= Q(gender__iexact=value)
            elif field == 'age_group':
                q_obj &= Q(age_group__iexact=value)
            elif field == 'country_id':
                q_obj &= Q(country_id__iexact=value)

        queryset = queryset.filter(q_obj).order_by('-created_at')
        
        try:
            page_num = max(1, int(request.query_params.get('page', 1)))
            page_size = min(50, max(1, int(request.query_params.get('limit', 10))))
        except ValueError:
            return Response({"status": "error", "message": "Invalid query parameters"}, status=422)

        total_count = queryset.count()
        
        serializer = ProfileListSerializer(queryset[(page_num-1)*page_size : page_num*page_size], many=True)
        
        return Response({
            "status": "success",
            "page": page_num,
            "limit": page_size,
            "total": total_count,
            "data": serializer.data,
        })

    def _parse_query(self, query):
        """Rule-based NL query parser"""
        filters = {}
        
        # Gender
        has_male = re.search(r'\b(males?|guys?|men?|boys?)\b', query)
        has_female = re.search(r'\b(females?|girls?|women?|ladies?)\b', query)
        if has_male and not has_female:
            filters['gender'] = 'male'
        elif has_female and not has_male:
            filters['gender'] = 'female'
            
        # Age groups
        if re.search(r'\b(teenagers?|teens?)\b', query):
            filters['age_group'] = 'teenager'
        elif 'adult' in query:
            filters['age_group'] = 'adult'
        elif re.search(r'\b(senior|elderly|old)\b', query):
            filters['age_group'] = 'senior'
        elif re.search(r'\b(child|kids?|children)\b', query):
            filters['age_group'] = 'child'
            
        # "Young" requirement (16-24)
        if 'young' in query:
            filters['min_age'] = 16
            filters['max_age'] = 24

        # Age numbers
        above_match = re.search(r'\b(above|over|more than|gt)\s*(\d+)\b', query)
        if above_match:
            filters['min_age'] = int(above_match.group(2))
            
        # Countries (expanded map)
        country_map = {
            'nigeria': 'NG', 'kenya': 'KE', 'angola': 'AO',
            'usa': 'US', 'america': 'US', 'united states': 'US',
            'uk': 'GB', 'britain': 'GB', 'england': 'GB',
            'benin': 'BJ', 'ghana': 'GH', 'south africa': 'ZA'
        }
        for name, code in country_map.items():
            if name in query:
                filters['country_id'] = code
                break
                
        return filters if filters else None

    # Keep create, retrieve, destroy from original (simplified)
    def create(self, request):
        # Use original create logic...
        name = request.data.get("name")
        if not name or not isinstance(name, str) or not name.strip():
            return Response({"status": "error", "message": "Missing or empty parameter"}, status=400)
        
        normalized_name = name.strip().lower()
        if Profile.objects.filter(name=normalized_name).exists():
            profile = Profile.objects.get(name=normalized_name)
            return Response({
                "status": "success", 
                "data": ProfileSerializer(profile).data
            })

        serializer = ProfileCreateSerializer(data={"name": normalized_name})
        if serializer.is_valid():
            profile = serializer.save()
            return Response({
                "status": "success", 
                "data": ProfileSerializer(profile).data
            }, status=201)
        return Response({"status": "error", "message": "Invalid data"}, status=400)

    def retrieve(self, request, pk=None):
        try:
            profile = Profile.objects.get(pk=pk)
            return Response({"status": "success", "data": ProfileSerializer(profile).data})
        except Profile.DoesNotExist:
            return Response({"status": "error", "message": "Profile not found"}, status=404)

    def destroy(self, request, pk=None):
        try:
            profile = Profile.objects.get(pk=pk)
            profile.delete()
            return Response(status=204)
        except Profile.DoesNotExist:
            return Response(status=404)
