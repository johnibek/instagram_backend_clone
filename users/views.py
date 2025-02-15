from datetime import datetime

from django.core.exceptions import ObjectDoesNotExist
from rest_framework.exceptions import ValidationError, NotFound
from rest_framework.generics import UpdateAPIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from .serializers import SignUpSerializer, ChangeUserDataSerializer, ChangeUserImageSerializer, LoginSerializer, \
    LoginRefreshSerializer, LogoutSerializer, ForgotPasswordSerializer, ResetPasswordSerializer
from .models import CustomUser
from shared.utils import send_email, check_user_input
from rest_framework import permissions, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from .tasks import send_phone_verification_code


class SignUpUserAPIView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = SignUpSerializer
    permission_classes = [permissions.AllowAny]


class VerifyAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = self.request.user
        code = self.request.data.get('code')

        self.check_verification(user, code)
        return Response(data={
            'success': True,
            'auth_status': user.auth_status,
            'access_token': user.token()['access_token'],
            'refresh_token': user.token()['refresh_token']
        })

    @staticmethod
    def check_verification(user, code):
        verification_codes = user.verification_codes.filter(expiration_time__gte=datetime.now(), code=code, is_confirmed=False)

        if not verification_codes.exists():
            data = {
                'message': 'This user has already been confirmed or confirmation code is incorrect.'
            }
            raise ValidationError(data)

        verification_codes.update(is_confirmed=True)

        if user.auth_status == CustomUser.AuthStatus.NEW.value:
            user.auth_status = CustomUser.AuthStatus.CODE_VERIFIED.value
            user.save()


class GetNewVerificationCode(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = self.request.user
        self.check_verification(user)
        if user.auth_type == CustomUser.AuthTypes.VIA_EMAIL:
            code = user.create_verification_code(CustomUser.AuthTypes.VIA_EMAIL.value)
            send_email(user.email, code)
            return Response(
                {'success': True, "message": f"Your new verification code has been sent to {user.email}"}
            )
        elif user.auth_type == CustomUser.AuthTypes.VIA_PHONE:
            code = user.create_verification_code(CustomUser.AuthTypes.VIA_PHONE.value)
            send_phone_verification_code.delay(user.phone_number, code)
            return Response(
                {'success': True, 'message': f'Your new verification code has been sent to {user.phone_number}'}
            )
        else:
            data = {
                'success': False,
                'message': 'Invalid email or phone number entered'
            }
            raise ValidationError(data)



    @staticmethod
    def check_verification(user):
        verification_codes = user.verification_codes.filter(expiration_time__gte=datetime.now(), is_confirmed=False)
        if verification_codes.exists():
            data = {
                'message': "You have a valid code. You can use it."
            }
            raise ValidationError(data)


class ChangeUserDataAPIView(UpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ChangeUserDataSerializer
    http_method_names = ['patch', 'put']

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        super(ChangeUserDataAPIView, self).update(request, *args, **kwargs)
        data = {
            'success': True,
            'message': 'User updated successfully',
            'auth_status': self.request.user.auth_status
        }
        return Response(data, status=status.HTTP_200_OK)


    def partial_update(self, request, *args, **kwargs):
        super(ChangeUserDataAPIView, self).partial_update(request, *args, **kwargs)
        data = {
            'success': True,
            'message': 'User updated successfully',
            'auth_status': self.request.user.auth_status
        }
        return Response(data, status=status.HTTP_200_OK)


class ChangeUserImageAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request):
        serializer = ChangeUserImageSerializer(data=request.data)
        if serializer.is_valid():
            serializer.update(request.user, serializer.validated_data)
            return Response({'message': 'Image Uploaded Successfully'}, status=status.HTTP_200_OK)

        return Response(
            serializer.errors, status=status.HTTP_400_BAD_REQUEST
        )


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer


class LoginRefreshView(TokenRefreshView):
    serializer_class = LoginRefreshSerializer


class LogoutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            refresh_token = serializer.validated_data['refresh_token']
            token = RefreshToken(refresh_token)
            token.blacklist()
            data = {
                'success': True,
                'message': "You have successfully logged out"
            }
            return Response(data, status=status.HTTP_205_RESET_CONTENT)
        except TokenError:
            return Response(status=status.HTTP_400_BAD_REQUEST)


class ForgotPasswordAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email_or_phone = serializer.validated_data.get('email_or_phone')
        user = serializer.validated_data.get('user')

        if check_user_input(email_or_phone) == 'phone_number':
            code = user.create_verification_code(CustomUser.AuthTypes.VIA_PHONE)
            send_phone_verification_code.delay(email_or_phone, code)
            return Response(
                {
                    'success': True,
                    'message': 'Your verification code has been sent to your phone {}'.format(user.phone_number),
                    'access': user.token()['access_token'],
                    'refresh': user.token()['refresh_token'],
                    'auth_status': user.auth_status
                }, status=status.HTTP_200_OK
            )

        elif check_user_input(email_or_phone) == 'email':
            code = user.create_verification_code(CustomUser.AuthTypes.VIA_EMAIL)
            send_phone_verification_code.delay(email_or_phone, code)
            return Response(
                {
                    'success': True,
                    'message': 'Your verification code has been sent to your email {}'.format(user.email),
                    'access': user.token()['access_token'],
                    'refresh': user.token()['refresh_token'],
                    'auth_status': user.auth_status
                }, status=status.HTTP_200_OK
            )


class ResetPasswordView(UpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ResetPasswordSerializer
    http_method_names = ['put']

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        response = super(ResetPasswordView, self).update(request, *args, **kwargs)
        try:
            user = CustomUser.objects.get(id=response.data['id'])
            return Response(
                {
                    'success': True,
                    'message': 'Your password successfully changed',
                    'access': user.token()['access_token'],
                    'refresh': user.token()['refresh_token']
                }
            )
        except ObjectDoesNotExist as e:
            raise NotFound(detail="User not found")

