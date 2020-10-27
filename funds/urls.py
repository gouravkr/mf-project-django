from django.urls import path
from . import views


urlpatterns = [
    path('<int:amfi_code>', views.fund_info),
    path('<int:amfi_code>/info', views.fund_info),
    path('<int:amfi_code>/nav-history', views.nav_history),
    path('<int:amfi_code>/latest-return', views.fund_returns),
    path('<int:amfi_code>/sip-return', views.fund_sip_returns),
    path('<int:amfi_code>/rolling-return', views.rolling_return),
    path('', views.fund_info),
    path('amc-list', views.amc_list),
]
