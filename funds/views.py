"""Views related to fund analysis"""

from django.http import HttpResponse
from django.http import JsonResponse

from .methods import MutualFund, FundAdvanced, fund_search, fetch_amc_list


def fund_info(request, amfi_code=None):
    """This view is used to search for funds or retrieve fund information"""

    search = request.GET.get('search', None)
    if amfi_code is not None:
        mf = MutualFund(amfi_code)
        result = mf.info
        returns = mf.latest_returns()
        result.update({'returns': returns})
    elif search is not None:
        result = fund_search(search)
        result = result.to_dict(orient='records')
    else:
        return HttpResponse("Provide a search string or amfi_code", status=400)
    return JsonResponse(result, safe=False)


def nav_history(request, amfi_code=None):
    """Returns the nav history of a fund"""

    if amfi_code is None:
        return HttpResponse("Provide an amfi_code", status=400)
    mf = MutualFund(amfi_code)
    nav_hist = mf.nav_history.reset_index()
    nav_hist['date'] = nav_hist['date'].dt.date
    nav_hist_dict = nav_hist.to_dict(orient='records')
    return JsonResponse(nav_hist_dict, safe=False)


def fund_returns(request, amfi_code=None):
    """1-3-5 year returns of a fund"""

    if amfi_code is None:
        return HttpResponse("Provide an amfi_code", status=400)
    mf = MutualFund(amfi_code)
    returns = mf.latest_returns()
    return JsonResponse(returns, safe=False)


def fund_sip_returns(request, amfi_code=None):
    """1-3-5 year SIP returns of a fund"""

    if amfi_code is None:
        return HttpResponse("Provide an amfi_code", status=400)
    mf = MutualFund(amfi_code)
    returns = mf.sip_returns()
    return JsonResponse(returns, safe=False)


def rolling_return(request, amfi_code=None):
    """Rolling returns based on provided frequency and period"""

    if amfi_code is None:
        return HttpResponse("Provide an amfi_code", status=400)
    period = int(request.GET.get('period', 1))
    start_date = request.GET.get('start_date', None)
    end_date = request.GET.get('end_date', None)
    summary = request.GET.get('summary', None)
    mf = FundAdvanced(amfi_code)
    rolling_returns = mf.rolling_returns(period, start_date, end_date)
    rolling_returns = rolling_returns.to_dict(orient='records')
    returns_dict = {'returns': rolling_returns}
    if summary is not None:
        rolling_summary = mf.rolling_summary(period, start_date, end_date)
    returns_dict['summary'] = rolling_summary
    return JsonResponse(returns_dict, safe=False)


def amc_list(request):
    """Return a list of AMCs"""

    return JsonResponse(fetch_amc_list(), safe=False)
