from django.shortcuts import render
from django.http import HttpResponse
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from .methods import MutualFund, FundAdvanced, fund_search

# Create your views here

def fund_info(request, amfi_code=None):
    search = request.GET.get('search', None)
    if amfi_code is not None:
        mf = MutualFund(amfi_code)
        result = mf.info
    elif search is not None:
        result = fund_search(search)
        result = result.to_dict(orient='records')
    else:
        return HttpResponse("Provide a search string or amfi_code", status=400)
    return JsonResponse(result, safe=False)

def nav_history(request, amfi_code=None):
    if amfi_code is None:
        return HttpResponse("Provide an amfi_code", status=400)
    mf = MutualFund(amfi_code)
    nav_hist = mf.nav_history.to_dict(orient='records')
    return JsonResponse(nav_hist, safe=False)


def rolling_return(request, amfi_code=None):
    if amfi_code is None:
        return HttpResponse("Provide an amfi_code", status=400)
    period = int(request.GET.get('period', 1))
    start_date = request.GET.get('start_date', None)
    end_date = request.GET.get('end_date', None)
    mf = FundAdvanced(amfi_code)
    rolling_returns = mf.rolling_returns(period, start_date, end_date)
    rolling_returns = rolling_returns.to_dict(orient='records')
    return JsonResponse(rolling_returns, safe=False)
