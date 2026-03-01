# ══════════════════════════════════════════════════════════════════════════
# apps/locations/urls.py
# ══════════════════════════════════════════════════════════════════════════
from django.urls import path
from .views import LocationListCreateView, LocationDetailView, SetDefaultLocationView

urlpatterns = [
    path('',                  LocationListCreateView.as_view(), name='location-list'),
    path('<int:pk>/',          LocationDetailView.as_view(),     name='location-detail'),
    path('<int:pk>/default/',  SetDefaultLocationView.as_view(), name='location-set-default'),
]