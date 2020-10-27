from django.urls import path
from . import views

urlpatterns = [
    path('', views.user),

    path('transactions', views.UserTransaction.as_view()),
    path('portfolio', views.user_portfolio),
    path('investment-summary', views.user_investment_summary),
    path('folios/<int:amfi_code>', views.UserFolios.as_view()),
    path('folios', views.UserFolios.as_view()),
    path('banks', views.UserBanks.as_view()),

    path('check-email/', views.check_email),
    path('login/', views.AuthenticationView.as_view()),
    path('signup/', views.user_registration),
]
