from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("watch-anime/strelizia/", admin.site.urls),
    path("watch-anime/api/", include("api.urls")),
    # path('api/', include('api.urls'))
    path('', include('django_prometheus.urls')),
]

if not settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
