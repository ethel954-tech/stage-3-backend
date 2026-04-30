import csv
import re
from datetime import datetime
from io import StringIO

from django.http import HttpResponse
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action

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

    # ----------------------------
    # FILTERS
    # ----------------------------
    def _apply_filters(self, queryset, params):
        filters = {}
        try:
            if params.get('gender'):
                filters['gender__iexact'] = params.get('gender').strip()

            if params.get('age_group'):
                filters['age_group__iexact'] = params.get('age_group').strip()

            if params.get('country_id'):
                filters['country_id__iexact'] = params.get('country_id').strip()

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

    # ----------------------------
    # SORTING
    # ----------------------------
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

    # ----------------------------
    # PAGINATION (FIXED - Handle empty/missing/invalid gracefully)
    # ----------------------------
    def _paginate(self, queryset, params):
        page = 1
        limit = 10
        
        try:
            page_param = params.get('page')
            limit_param = params.get('limit')

            if page_param:
                page_str = str(page_param).strip()
                if page_str:
                    page_int = int(page_str)
                    if page_int > 0:
                        page = page_int

            if limit_param:
                limit_str = str(limit_param).strip()
                if limit_str:
                    limit_int = int(limit_str)
                    if limit_int > 0:
                        limit = limit_int

        except (ValueError, TypeError):
            pass

        limit = min(limit, 50)
        total = queryset.count()
        total_pages = (total + limit - 1) // limit if limit > 0 else 0
        offset = (page - 1) * limit
        data = queryset[offset:offset + limit]

        return data, {
            'page': page,
            'limit': limit,
            'total': total,
            'total_pages': total_pages
        }, None

    # ----------------------------
    # LIST
    # ----------------------------
    def list(self, request):
        queryset = self.get_queryset()
        params = request.query_params

        queryset, error = self._apply_filters(queryset, params)
        if error:
            return error

        queryset, error = self._apply_sorting(queryset, params)
        if error:
            return error

        data, meta, error = self._paginate(queryset, params)
        if error:
            return error

        serializer = ProfileListSerializer(data, many=True)

        return Response({
            "status": "success",
            "page": meta['page'],
            "limit": meta['limit'],
            "total": meta['total'],
            "total_pages": meta['total_pages'],
            "data": serializer.data
        })

    # ----------------------------
    # SEARCH
    # ----------------------------
    @action(detail=False, methods=['get'])
    def search(self, request):
        params = request.query_params
        q = params.get('q', '').strip()

        if not q:
            return Response(
                {"status": "error", "message": "Missing or empty 'q' parameter"},
                status=400
            )

        queryset = self.get_queryset().filter(name__icontains=q)

        data, meta, error = self._paginate(queryset, params)
        if error:
            return error

        serializer = ProfileListSerializer(data, many=True)

        return Response({
            "status": "success",
            "page": meta['page'],
            "limit": meta['limit'],
            "total": meta['total'],
            "total_pages": meta['total_pages'],
            "data": serializer.data
        })

    # ----------------------------
    # EXPORT
    # ----------------------------
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
                profile.created_at.isoformat()
            ])

        response = HttpResponse(output.getvalue(), content_type='text/csv')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        response['Content-Disposition'] = f'attachment; filename="profiles_{timestamp}.csv"'

        return response

    # ----------------------------
    # CREATE
    # ----------------------------
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

        profile = serializer.save()

        return Response(
            {"status": "success", "data": ProfileSerializer(profile).data},
            status=201
        )

    # ----------------------------
    # RETRIEVE
    # ----------------------------
    def retrieve(self, request, pk):
        try:
            profile = Profile.objects.get(pk=pk)
            return Response({"status": "success", "data": ProfileSerializer(profile).data})
        except Profile.DoesNotExist:
            return Response({"status": "error", "message": "Profile not found"}, status=404)

    # ----------------------------
    # DELETE
    # ----------------------------
    def destroy(self, request, pk):
        try:
            profile = Profile.objects.get(pk=pk)
            profile.delete()
            return Response(status=204)
        except Profile.DoesNotExist:
            return Response(status=404)
