from django.urls import include
from dmr.routing import Router, path

from . import views

router = Router(
    "api/",
    [
        path("third-parties/", views.PartiesView.as_view(), name="third-parties"),
        path("accounts/", views.AccountsView.as_view(), name="accounts"),
        path(
            "accounts/<uuid:account_id>/",
            views.AccountDetailView.as_view(),
            name="account-detail",
        ),
        path(
            "statements/<uuid:account_id>/",
            views.StatementsView.as_view(),
            name="statements",
        ),
        path(
            "accounts/<uuid:account_id>/statements/<uuid:statement_id>/",
            views.StatementDetailView.as_view(),
            name="statement-detail",
        ),
    ],
)

urlpatterns = [
    path(router.prefix, include((router.urls, "banking"), namespace="banking")),
]
