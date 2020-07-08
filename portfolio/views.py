from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

import json

from .methods import User, UserInvestmentManager, UserPortfolio
# Create your views here.

def user(request, user_id):
    user = User(user_id)
    info = user.info
    return JsonResponse(info, safe=False)


@method_decorator(csrf_exempt, name='dispatch')
class UserTransaction(View):
    def get(self, request, user_id):
        user = UserPortfolio(user_id)
        df = user.transaction_history
        result = df.to_dict(orient='records')
        return JsonResponse(result, safe=False)

    def post(self, request, user_id):
        body_unicode = request.body.decode('utf-8')
        body = json.loads(body_unicode)
        required_vals = ['amfi_code', 'trx_date', 'trx_type']
        one_optional_val = ['amount', 'units']
        user = UserInvestmentManager(user_id)
        if all(val in body for val in required_vals) and any(val in body for val in one_optional_val):
            response = user.add_past_transaction(**body)
        else:
            error = f"""Error: All required fields are not present.</br>
                        Please provide all of {', '.join(required_vals)} 
                        and any one of {' or '.join(one_optional_val)}
                    """
            return HttpResponse(error, status=400)
        return HttpResponse(response)


def user_portfolio(request, user_id):
    user = UserPortfolio(user_id)
    df = user.fetch_portfolio(with_xirr=True)
    result = df.to_dict(orient='records')
    return JsonResponse(result, safe=False)


def user_investment_summary(request, user_id):
    user = UserPortfolio(user_id)
    result = user.investment_summary()
    return JsonResponse(result, safe=False)


class UserFolios(View):
    def get(self, request, user_id, amfi_code=None):
        user = User(user_id)
        result = user.get_folios(amfi_code)
        return JsonResponse(result, safe=False)

    def post(request, user_id):
        pass

class UserBanks(View):
    def get(self, request, user_id):
        user = User(user_id)
        result = user.get_banks()
        return JsonResponse(result, safe=False)
    
    def post(request, user_id):
        pass
