# ══════════════════════════════════════════════════════════════════════════
# apps/users/urls.py
# ══════════════════════════════════════════════════════════════════════════
from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import RegisterView, MeView, PreferencesView, LogoutView

from django.http import JsonResponse
from django.urls import path

def health(request):
    return JsonResponse({"status": "ok"})

urlpatterns = [
    path('register/',      RegisterView.as_view(),      name='auth-register'),
    path('login/',         TokenObtainPairView.as_view(),name='auth-login'),
    path('token/refresh/', TokenRefreshView.as_view(),   name='token-refresh'),
    path('logout/',        LogoutView.as_view(),          name='auth-logout'),
    path('me/',            MeView.as_view(),              name='auth-me'),
    path('preferences/',   PreferencesView.as_view(),     name='auth-preferences'),

]

