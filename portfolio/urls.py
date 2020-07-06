from django.urls import path
from . import views

urlpatterns = [
    path('<int:user_id>', views.user),

    path('<int:user_id>/transactions', views.UserTransaction.as_view()),
    path('<int:user_id>/portfolio', views.user_portfolio),
    # path('<int:user_id>/xirr', views.fetch_xirr, name='user_xirr'),
    path('<int:user_id>/investment-summary', views.user_investment_summary),
    # path('<int:user_id>/folios/<int:amfi_code>', views.folios.as_view(), name='user_folios'),
    # path('<int:user_id>/folios', views.folios.as_view(), name='user_folios'),
    # path('<int:user_id>/banks', views.user_banks.as_view(), name='user_banks'),
]
