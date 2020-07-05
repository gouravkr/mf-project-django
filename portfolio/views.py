from django.shortcuts import render
from django.http import JsonResponse

from .methods import User
# Create your views here.

def user(request, user_id):
    user = User(user_id)
    info = user.info
    return JsonResponse(info, safe=False)