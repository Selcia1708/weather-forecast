# ══════════════════════════════════════════════════════════════════════════
# apps/weather/urls.py
# ══════════════════════════════════════════════════════════════════════════
from django.urls import path
from . import views

urlpatterns = [
    # HTML
    path('',                    views.dashboard,                name='dashboard'),

    # REST
    path('full/',               views.FullWeatherAPIView.as_view(),     name='weather-full'),
    path('current/',            views.CurrentWeatherAPIView.as_view(),   name='weather-current'),
    path('forecast/',           views.ForecastAPIView.as_view(),         name='weather-forecast'),
    path('aqi/',                views.AQIAPIView.as_view(),              name='weather-aqi'),
    path('alerts/',             views.AlertsAPIView.as_view(),           name='weather-alerts'),
    path('search/',             views.SearchLocationAPIView.as_view(),   name='weather-search'),
    path('reverse-geocode/',    views.ReverseGeocodeAPIView.as_view(),   name='weather-reverse-geocode'),
    path('history/',            views.HistoryAPIView.as_view(),          name='weather-history'),
]