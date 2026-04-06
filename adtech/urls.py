from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic.base import RedirectView

urlpatterns = [
    # Admin panel
    path('admin/', admin.site.urls),

    # eCommerce Store (pure Django templates)
    path('', include('store.urls')),

    # Legacy REST API (available for tools / Postman / PayPal backend calls)
    path('api/users/', include('users.urls')),
    path('api/', include('customers.urls')),
    path('api/', include('inventory.urls')),
    path('api/', include('sales.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
