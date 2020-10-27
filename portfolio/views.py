"""Views for user authentication, info, and portfolios"""

import json

from django.http import JsonResponse, HttpResponse
from django.contrib.auth import authenticate
from django.contrib.auth.models import User

from rest_framework.decorators import api_view, permission_classes
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authtoken.models import Token

from .methods import UserInfo, UserInvestmentManager, UserPortfolio


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user(request):
    """user information"""

    user = UserInfo(request.user.id)
    info = user.info()
    return JsonResponse(info, safe=False)


class UserTransaction(APIView):
    """This class allows fetching, adding, and updating of transactions"""

    permission_classes = (IsAuthenticated,)

    def get(self, request):
        """get user transactions"""

        user_id = request.user.id
        user = UserPortfolio(user_id)
        result = user.transaction_history
        return Response(result)

    def post(self, request):
        """create user transactions"""

        body_unicode = request.body.decode('utf-8')
        body = json.loads(body_unicode)
        user_id = request.user.id

        required_vals = ['amfi_code', 'trx_date', 'trx_type']
        one_reqd_val = ['amount', 'units']

        if all(val in body for val in required_vals) and any(val in body for val in one_reqd_val):
            user = UserInvestmentManager(user_id)
            response = user.add_transaction(**body)
        else:
            error = (f"Error: All required fields are not present."
                     f" Please provide all of {', '.join(required_vals)}"
                     f" and any one of {' or '.join(one_reqd_val)}")

            return Response({'message': error}, status=400)
        return Response(response)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_portfolio(request):
    """fetch user portfolio"""

    user = UserPortfolio(request.user.id)
    result = user.fetch_portfolio()
    return Response(result)


# @csrf_exempt
def user_registration(request):
    """register a user"""

    body_unicode = request.body.decode('utf-8')
    body = json.loads(body_unicode)
    user = User.objects.create_user(body['username'], body['email'], body['password'])
    user.last_name = body['last_name']
    user.last_name = body['first_name']
    user.save()
    user_info = UserInfo(user.id)
    user_created = user_info.create_user(**body)
    if not user_created:
        user.delete()
        return HttpResponse("User creation failed", status=400)
    return HttpResponse(user.id, status=201)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_investment_summary(request):
    """Investment summary for a user"""

    user = UserPortfolio(request.user.id)
    result = user.investment_summary()
    return Response(result)


class UserFolios(APIView):
    """This class allows fetching, adding, and updating of user folios"""

    permission_classes = (IsAuthenticated,)

    def get(self, request, amfi_code=None):
        """Get user folios"""

        user = UserInfo(request.user.id)
        result = user.get_folios(amfi_code)
        return Response(result)

    def post(self, request):
        """Create user folios"""

        body_unicode = request.body.decode('utf-8')
        body = json.loads(body_unicode)
        user = UserInvestmentManager(request.user.id)
        created_folio = user.create_folio(**body)
        status = created_folio['status']
        del created_folio['status']
        return Response(created_folio, status=status)


class UserBanks(APIView):
    """This class allows fetching, creating, and updating of user banks"""

    permission_classes = (IsAuthenticated,)

    def get(self, request):
        """get user banks"""

        user = UserInfo(request.user.id)
        result = user.get_banks()
        return Response(result)

    def post(self, request):
        """Create user banks"""

        body_unicode = request.body.decode('utf-8')
        body = json.loads(body_unicode)
        user = UserInvestmentManager(request.user.id)

        added_bank = user.create_bank(**body)
        status = added_bank['status']
        del added_bank['status']
        return Response(added_bank, status=status)


class AuthenticationView(APIView):
    """this class allows fetching of user info and login"""

    permission_classes = (AllowAny,)

    def get(self, request):
        """get user info"""

        content = {'message': 'Hello, World!'}
        return Response(content)

    def post(self, request):
        """Login a user"""

        body_unicode = request.body.decode('utf-8')
        body = json.loads(body_unicode)
        username = body['username']
        password = body['password']
        user = authenticate(username=username, password=password)
        if not user:
            return Response({'Error': 'Invalid userid or password'}, status=401)
        token, _ = Token.objects.get_or_create(user=user)
        return Response({'Token': token.key})


@api_view(['POST'])
def check_email(request):
    """Check if an email is available at the time of signup"""

    body_unicode = request.body.decode('utf-8')
    body = json.loads(body_unicode)
    email = body['email']
    count = User.objects.filter(email=email).count()
    if count:
        return Response({"message": "Email already exists"})
    else:
        return Response({"message": "You're good to go"})
