from django.shortcuts import render
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from .methods import User, UserInvestmentManager, UserPortfolio
# Create your views here.

def user(request, user_id):
    user = User(user_id)
    info = user.info
    return JsonResponse(info, safe=False)

class UserTransaction(View):
    def get(self, request, user_id):
        user = UserPortfolio(user_id)
        df = user.transaction_history
        result = df.to_dict(orient='records')
        return JsonResponse(result, safe=False)

    def post(request, user_id):
        pass

def user_portfolio(request, user_id):
    user = UserPortfolio(user_id)
    df = user.fetch_portfolio(with_xirr=True)
    result = df.to_dict(orient='records')
    return JsonResponse(result, safe=False)


def user_investment_summary(request, user_id):
    user = UserPortfolio(user_id)
    result = user.investment_summary()
    return JsonResponse(result, safe=False)
