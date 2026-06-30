from django.urls import path
from .views import ThirdPartyCodeView, AuthorizeView, TokenView

urlpatterns = [
    path("third-party-code", ThirdPartyCodeView.as_view()),
    path("authorize", AuthorizeView.as_view()),
    path("token", TokenView.as_view()),
]
