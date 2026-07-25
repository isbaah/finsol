from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from common.api.health import liveness, readiness

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/live/", liveness, name="health-live"),
    path("health/ready/", readiness, name="health-ready"),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    # HEADLESS_ONLY=True, so this only ever contains the social-provider
    # redirect/callback routes (e.g. Google) — no server-rendered account
    # pages. See docs/ARCHITECTURE.md's authentication section.
    path("accounts/", include("allauth.urls")),
    # JSON API used by the Next.js frontend for all auth actions.
    path("_allauth/", include("allauth.headless.urls")),
    path("api/v1/", include("apps.accounts.urls")),
    path("api/v1/", include("apps.customers.urls")),
    path("api/v1/", include("apps.loan_requests.urls")),
    path("api/v1/", include("apps.loan_offers.urls")),
    path("api/v1/", include("apps.agreements.urls")),
    path("api/v1/", include("apps.loans.urls")),
    path("api/v1/", include("apps.repayments.urls")),
    path("api/v1/", include("apps.messaging.urls")),
    path("api/v1/", include("apps.dashboards.urls")),
]
