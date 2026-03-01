# ══════════════════════════════════════════════════════════════════════════
# config/urls.py
# ══════════════════════════════════════════════════════════════════════════
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns

from apps.core.views import health_check
urlpatterns = [
    ...
    path("health/", health_check),
]

urlpatterns = [
    path('admin/',          admin.site.urls),
    path('rosetta/',        include('rosetta.urls')),
    path('api/auth/',       include('apps.users.urls')),
    path('api/weather/',    include('apps.weather.urls')),
    path('api/locations/',  include('apps.locations.urls')),
]

# Internationalised frontend routes
urlpatterns += i18n_patterns(
    path('', include('apps.weather.urls')),
    prefix_default_language=False,
)

if settings.DEBUG:
    import debug_toolbar
    urlpatterns += [path('__debug__/', include(debug_toolbar.urls))]
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)