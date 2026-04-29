import csv
import re
from datetime import datetime
from io import StringIO

from django.db.models import Q
from django.http import HttpResponse
from rest_framework import status as http_status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from .models import Profile
from .permissions import IsAuthenticated, IsAdmin
from .serializers import (
    ProfileCreateSerializer,
    ProfileListSerializer,
    ProfileSerializer,
)


class ProfileViewSet(ViewSet):
    def get_permissions(self):
        if self.action in ['create', 'destroy']:
            return [IsAdmin()]
        return [IsAuthenticated()]

    def get_queryset(self):
        return Profile.objects.all()

    def perform_content_negotiation(self, request, force=False):
        """Skip format negotiation for export action to avoid Http404 on ?format=csv."""
        if getattr(self, 'action', None) == 'export':
            from rest_framework.renderers import JSONRenderer
            return JSONRenderer(), 'application/json'
        return super().perform_content_negotiation(request, force)

    def _build_links(self, request, page, limit, total_pages):
        base = request.path
        query = request.query_params.copy()
        query.pop('page', None)
        query.pop('limit', None)
        base_query = query.urlencode()
        separator = '&' if base_query else ''

        self_link = f"{base}?page={page}&limit={limit}{separator}{base_query}" if base_query else f"{base}?page={page}&limit={limit}"
        next_link = f"{base}?page={page + 1}&limit={limit}{separator}{base_query}" if page < total_pages else None
        prev_link = f"{base}?page={page - 1}&limit={limit}{separator}{base_query}" if page > 1 else None

        return {
            "self": self_link,
            "next": next_link,
            "prev": prev_link,
        }

    def _apply_filters(self, queryset, params):
        filters = {}
        try:
            if params.get('gender'):
                filters['gender__iexact'] = params.get('gender')
            if params.get('age_group'):
                filters['age_group__iexact'] = params.get('age_group')
            if params.get('country_id'):
                filters['country_id__iexact'] = params.get('country_id')
            if params.get('min_age'):
                filters['age__gte'] = int(params.get('min_age'))
            if params.get('max_age'):
                filters['age__lte'] = int(params.get('max_age'))
            if params.get('min_gender_probability'):
                filters['gender_probability__gte'] = float(params.get('min_gender_probability'))
            if params.get('min_country_probability'):
                filters['country_probability__gte'] = float(params.get('min_country_probability'))
        except (ValueError, TypeError):
            return None, Response(
                {"status": "error", "message": "Invalid query parameters"},
                status=422
            )
        return queryset.filter(**filters), None

    def _apply_sorting(self, queryset, params):
        sort_by = params.get('sort_by', 'created_at')
        order = params.get('order', 'desc').lower()
        allowed_sort = ['age', 'created_at', 'gender_probability']

        if sort_by not in allowed_sort or order not in ['asc', 'desc']:
            return None, Response(
                {"status": "error", "message": "Invalid query parameters"},
                status=422
            )

        prefix = '-' if order == 'desc' else ''
        return queryset.order_by(f"{prefix}{sort_by}"), None

    def _paginate(self, queryset, params):
        try:
            page = int(params.get('page', 1))
            limit = int(params.get('limit', 10))
            if page <= 0 or limit <= 0:
                raise ValueError
        except (ValueError, TypeError):
            return None, None, Response(
                {"status": "error", "message": "Invalid query parameters"},
                status=422
            )

        limit = min(limit, 50)
        total = queryset.count()
        total_pages = (total + limit - 1) // limit
        offset = (page - 1) * limit
        data = queryset[offset:offset + limit]
        return data, {'page': page, 'limit': limit, 'total': total, 'total_pages': total_pages}, None

    def list(self, request):
        allowed_params = {'search', 'username', 'page', 'limit'}
        query_params = request.query_params
        
        # Check for invalid parameters
        invalid_params = [key for key in query_params.keys() if key not in allowed_params]
        if invalid_params:
            return Response({
                "status": "error", 
                "message": f"Invalid query parameters: {', '.join(invalid_params)}"
            }, status=422)
        
        queryset = self.get_queryset()
        
        # Search filter
        search_query = query_params.get('search') or query_params.get('username', '').strip()
        if search_query:
            queryset = queryset.filter(name__icontains=search_query)
        
        # Pagination
        try:
            page = max(1, int(query_params.get('page', 1)))
            limit = min(50, max(1, int(query_params.get('limit', 10))))
        except ValueError:
            return Response({
                "status": "error", 
                "message": "Invalid page or limit: must be positive integers"
            }, status=422)
        
        total = queryset.count()
        start = (page - 1) * limit
        data = queryset[start:start + limit]
        
        serializer = ProfileListSerializer(data, many=True)
        
        return Response({
            "status": "success",
            "page": page,
            "limit": limit,
            "total": total,
            "data": serializer.data
        })

    @action(detail=False, methods=['get'])
    def export(self, request):
        queryset = self.get_queryset()
        params = request.query_params

        queryset, error = self._apply_filters(queryset, params)
        if error:
            return error

        queryset, error = self._apply_sorting(queryset, params)
        if error:
            return error

        output = StringIO()
        writer = csv.writer(output)
        writer.writerow([
            'id', 'name', 'gender', 'gender_probability', 'age', 'age_group',
            'country_id', 'country_name', 'country_probability', 'created_at'
        ])

        for profile in queryset:
            writer.writerow([
                str(profile.id),
                profile.name,
                profile.gender,
                profile.gender_probability,
                profile.age,
                profile.age_group,
                profile.country_id,
                profile.country_name,
                profile.country_probability,
                profile.created_at.isoformat(),
            ])

        response = HttpResponse(output.getvalue(), content_type='text/csv')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        response['Content-Disposition'] = f'attachment; filename="profiles_{timestamp}.csv"'
        return response

    @action(detail=False, methods=['get'])
    def search(self, request):
        params = request.query_params
        q = params.get('q', '').strip()

        if not q:
            return Response({"status": "error", "message": "Missing or empty 'q' parameter"}, status=400)

        # Simple search on name for consistency
        queryset = self.get_queryset().filter(name__icontains=q).order_by('-created_at')

        try:
            page = max(1, int(params.get('page', 1)))
            limit = min(50, max(1, int(params.get('limit', 10))))
        except ValueError:
            return Response({
                "status": "error", 
                "message": "Invalid page or limit: must be positive integers"
            }, status=422)

        total = queryset.count()
        start = (page - 1) * limit
        data = queryset[start:start + limit]

        serializer = ProfileListSerializer(data, many=True)

        return Response({
            "status": "success",
            "page": page,
            "limit": limit,
            "total": total,
            "data": serializer.data
        })

    def _parse_query(self, query):
        query = query.lower()
        filters = {}

        males = re.search(r'\b(male|males|man|men|boy|boys)\b', query)
        females = re.search(r'\b(female|females|woman|women|girl|girls|lady|ladies)\b', query)

        if males and females:
            pass
        elif males:
            filters['gender'] = 'male'
        elif females:
            filters['gender'] = 'female'

        if re.search(r'\byoung\b', query):
            filters['min_age'] = 16
            filters['max_age'] = 24

        above = re.search(r'\b(above|over)\s+(\d+)\b', query)
        if above:
            filters['min_age'] = int(above.group(2))

        below = re.search(r'\b(below|under)\s+(\d+)\b', query)
        if below:
            filters['max_age'] = int(below.group(2))

        if re.search(r'\b(adult|adults)\b', query):
            filters['age_group'] = 'adult'
        if re.search(r'\b(teen|teens|teenager|teenagers)\b', query):
            filters['age_group'] = 'teenager'

        country_map = {
            'nigeria': 'NG',
            'kenya': 'KE',
            'angola': 'AO',
            'usa': 'US',
            'america': 'US',
            'united states': 'US',
            'uk': 'GB',
            'britain': 'GB',
            'england': 'GB',
            'benin': 'BJ',
            'ghana': 'GH',
            'south africa': 'ZA',
        }

        for name, code in country_map.items():
            if re.search(rf'\b{name}\b', query):
                filters['country_id'] = code
                break

        if not filters:
            if re.search(r'\b(people|persons)\b', query):
                return filters
            return None

        return filters

    def create(self, request):
        name = request.data.get('name')

        if not isinstance(name, str) or not name.strip():
            return Response(
                {"status": "error", "message": "Invalid or missing name"},
                status=422
            )

        name = name.strip().lower()

        if Profile.objects.filter(name=name).exists():
            profile = Profile.objects.get(name=name)
            return Response(
                {"status": "success", "data": ProfileSerializer(profile).data},
                status=200
            )

        serializer = ProfileCreateSerializer(data={"name": name})

        if not serializer.is_valid():
            return Response(
                {"status": "error", "message": serializer.errors},
                status=400
            )

        try:
            profile = serializer.save()
            return Response(
                {"status": "success", "data": ProfileSerializer(profile).data},
                status=201
            )
        except Exception:
            return Response(
                {"status": "error", "message": "Server error"},
                status=500
            )

    def retrieve(self, request, pk):
        try:
            profile = Profile.objects.get(pk=pk)
            return Response({"status": "success", "data": ProfileSerializer(profile).data})
        except Profile.DoesNotExist:
            return Response({"status": "error", "message": "Profile not found"}, status=404)

    def destroy(self, request, pk):
        try:
            profile = Profile.objects.get(pk=pk)
            profile.delete()
            return Response(status=204)
        except Profile.DoesNotExist:
            return Response(status=404)

