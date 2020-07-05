from django.urls import path
from . import views


urlpatterns = [
    path('<int:amfi_code>', views.fund_info),
    path('<int:amfi_code>/info', views.fund_info),
    path('<int:amfi_code>/nav-history', views.nav_history),
    path('<int:amfi_code>/rolling-return', views.rolling_return),
    path('', views.fund_info)
]
