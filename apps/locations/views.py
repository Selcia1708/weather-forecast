# ══════════════════════════════════════════════════════════════════════════
# apps/locations/views.py
# ══════════════════════════════════════════════════════════════════════════
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Location
from .serializers import LocationSerializer, LocationCreateSerializer

from django.http import JsonResponse

def health_check(request):
    return JsonResponse({"status": "ok"})


class LocationListCreateView(generics.ListCreateAPIView):
    """List all user locations or add a new one."""
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        return LocationCreateSerializer if self.request.method == 'POST' else LocationSerializer

    def get_queryset(self):
        return Location.objects.filter(user=self.request.user).order_by('-is_default', 'city')

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        location = serializer.save()
        return Response(LocationSerializer(location).data, status=status.HTTP_201_CREATED)


class LocationDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a single user location."""
    serializer_class   = LocationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Location.objects.filter(user=self.request.user)


class SetDefaultLocationView(generics.UpdateAPIView):
    """Mark a location as the user's default."""
    permission_classes = [IsAuthenticated]
    serializer_class   = LocationSerializer

    def get_queryset(self):
        return Location.objects.filter(user=self.request.user)

    def update(self, request, *args, **kwargs):
        location = self.get_object()
        location.is_default = True
        location.save()  # triggers unique-default logic in model.save()
        return Response(LocationSerializer(location).data)