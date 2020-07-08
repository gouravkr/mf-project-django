from django.urls import path
from . import views

urlpatterns = [
    path('<int:user_id>', views.user),

    path('<int:user_id>/transactions', views.UserTransaction.as_view()),
    path('<int:user_id>/portfolio', views.user_portfolio),
    path('<int:user_id>/investment-summary', views.user_investment_summary),
    path('<int:user_id>/folios/<int:amfi_code>', views.UserFolios.as_view()),
    path('<int:user_id>/folios', views.UserFolios.as_view()),
    path('<int:user_id>/banks', views.UserBanks.as_view()),
]
