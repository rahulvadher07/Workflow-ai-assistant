from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("accounts.urls")),
    path("api/company/", include("company.urls")),
    path("api/attendance/", include("attendance.urls")),
    path("api/teams/", include("teams.urls")),
    path("api/workspace/", include("workspace.urls")),
    path("api/ai/", include("ai.urls")),
    path("api/notifications/", include("notifications.urls")),
    path("api/payroll/", include("payroll.urls")),
    path("api/leave/", include("leave.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
