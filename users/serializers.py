from django.contrib.auth import authenticate
from django.contrib.auth.models import update_last_login
from django.contrib.auth.password_validation import validate_password
from django.core.validators import FileExtensionValidator
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer
from rest_framework_simplejwt.tokens import AccessToken

from .models import CustomUser, UserConfirmation, VIA_EMAIL, VIA_PHONE
from rest_framework import serializers, status
from django.db.models import Q
from rest_framework.exceptions import ValidationError, PermissionDenied, NotFound
from shared.utils import check_user_input, send_email
from users.tasks import send_phone_verification_code


class SignUpSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)

    def __init__(self, *args, **kwargs):
        super(SignUpSerializer, self).__init__(*args, **kwargs)
        self.fields['email_or_phone_number'] = serializers.CharField(required=False)


    def create(self, validated_data):
        user = super(SignUpSerializer, self).create(validated_data)
        if user.auth_type == VIA_EMAIL:
            code = user.create_verification_code(VIA_EMAIL)
            send_email(user.email, code)
        elif user.auth_type == VIA_PHONE:
            code = user.create_verification_code(VIA_PHONE)
            send_phone_verification_code.delay(user.phone_number, code)
        user.save()
        return user


    class Meta:
        model = CustomUser
        fields = (
            'id',
            'auth_type',
            'auth_status'
        )
        extra_kwargs = {
            'auth_type': {'read_only': True, 'required': False},
            'auth_status': {'read_only': True, 'required': False}
        }


    def validate(self, attrs):
        super(SignUpSerializer, self).validate(attrs)
        attrs = self.auth_validate(attrs)
        return attrs


    @staticmethod
    def auth_validate(attrs):
        # Check if user entered email or phone number
        user_input = str(attrs.get('email_or_phone_number')).lower()
        input_type = check_user_input(user_input)
        if input_type == 'email':
            attrs = {
                'email': user_input,
                'auth_type': CustomUser.AuthTypes.VIA_EMAIL
            }
        elif input_type == 'phone_number':
            attrs = {
                'phone_number': user_input,
                'auth_type': CustomUser.AuthTypes.VIA_PHONE
            }
        else:
            data = {
                'success': False,
                'message': 'Invalid data. Please enter email or phone number.'
            }
            raise ValidationError(data)

        return attrs


    def to_representation(self, instance):
        data = super(SignUpSerializer, self).to_representation(instance)  # data is output in JSON format
        data.update(instance.token())

        return data


    def validate_email_or_phone_number(self, value):
        value = value.lower()
        if value and check_user_input(value) == "email" and CustomUser.objects.filter(email=value).exists():
            result = {
                'success': False,
                'message': "A user with this email already exists."
            }
            raise ValidationError(result)

        elif value and check_user_input(value) == "phone_number" and CustomUser.objects.filter(phone_number=value).exists():
            result = {
                'success': False,
                'message': "A user with this phone number already exists."
            }
            raise ValidationError(result)

        return value


class ChangeUserDataSerializer(serializers.Serializer):
    first_name = serializers.CharField(write_only=True, required=True)
    last_name = serializers.CharField(write_only=True, required=True)
    username = serializers.CharField(write_only=True, required=True)
    password = serializers.CharField(write_only=True, required=True)
    confirm_password = serializers.CharField(write_only=True, required=True)

    def validate(self, attrs):
        password = attrs.get('password', None)
        confirm_password = attrs.get('confirm_password', None)
        first_name = attrs.get('first_name', None)
        last_name = attrs.get('last_name', None)

        if password != confirm_password:
            raise ValidationError({'message': 'Your password does not match'})

        if password:
            validate_password(password)

        if first_name.isdigit() or last_name.isdigit():
            raise ValidationError(
                {
                    'message': 'Your first name and last name cannot be numeric.'
                }
            )

        return attrs


    def validate_username(self, username):
        if len(username) < 5 or len(username) > 30:
            raise ValidationError(
                {
                    'message': 'Your username must be 5 and 30 characters long'
                }
            )

        if username.isdigit():
            raise ValidationError(
                {
                    'message': 'Your username is entirely numeric'
                }
            )

        return username


    def update(self, instance, validated_data):
        instance.first_name = validated_data.get('first_name', instance.first_name)
        instance.last_name = validated_data.get('last_name', instance.last_name)
        instance.username = validated_data.get('username', instance.username)

        if instance.password:
            instance.set_password(validated_data.get('password'))

        if instance.auth_status == CustomUser.AuthStatus.CODE_VERIFIED:
            instance.auth_status = CustomUser.AuthStatus.DONE

        instance.save()
        return instance


class ChangeUserImageSerializer(serializers.Serializer):
    photo = serializers.ImageField(validators=[FileExtensionValidator(
        allowed_extensions=('jpg', 'jpeg', 'png', 'heic', 'heif', 'tiff')
    )])

    def update(self, instance, validated_data):
        photo = validated_data.get('photo')
        if photo:
            instance.photo = photo
            instance.auth_status = CustomUser.AuthStatus.PHOTO_UPLOADED
            instance.save()

        return instance


class LoginSerializer(TokenObtainPairSerializer):
    def __init__(self, *args, **kwargs):
        super(LoginSerializer, self).__init__(*args, **kwargs)
        self.user = None
        self.fields['user_input'] = serializers.CharField(required=True)  # We are creating new user_input field.
        self.fields['username'] = serializers.CharField(required=False, read_only=True)  # We are overriding the username field to change required and read_only parameters.

    def auth_validate(self, data):
        user_input = data.get('user_input')  # username|email|phone_number
        if check_user_input(user_input) == 'username':
            username = user_input
        elif check_user_input(user_input) == 'email':
            user = self.get_user(email__iexact=user_input)
            username = user.username
        elif check_user_input(user_input) == 'phone_number':
            user = self.get_user(phone_number=user_input)
            username = user.username
        else:
            error = {
                'success': False,
                'message': 'Invalid input. You must enter username, email or phone number'
            }
            raise ValidationError(error)

        authentication_kwargs = {
            self.username_field: username,
            'password': data['password']
        }

        current_user = self.get_user(username=username)

        if current_user.auth_status in [CustomUser.AuthStatus.NEW, CustomUser.AuthStatus.CODE_VERIFIED]:
            raise ValidationError(
                {
                    'success': False,
                    'message': 'You have not registered successfully. Please sign up first.'
                }
            )
        user = authenticate(**authentication_kwargs)
        if user is not None:
            self.user = user
        else:
            raise ValidationError(
                {
                    'success': False,
                    'message': 'Sorry, username or password you entered is incorrect. Please check and try again.'
                }
            )

    def validate(self, attrs):
        self.auth_validate(attrs)
        attrs = self.user.token()
        attrs['auth_status'] = self.user.auth_status
        attrs['full_name'] = self.user.full_name
        return attrs


    @staticmethod
    def get_user(**kwargs):
        users = CustomUser.objects.filter(**kwargs)
        if not users.exists():
            raise ValidationError(
                {
                    'message': 'No active account found'
                }
            )

        return users.first()



class LoginRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)  # it gives "access token" like {"access": "some gibberish"}
        access_token_instance = AccessToken(data['access'])
        user_id = access_token_instance['user_id']
        user = get_object_or_404(CustomUser, id=user_id)
        update_last_login(None, user)
        return data


class LogoutSerializer(serializers.Serializer):
    refresh_token = serializers.CharField()


class ForgotPasswordSerializer(serializers.Serializer):
    email_or_phone = serializers.CharField(write_only=True, required=True)

    def validate(self, attrs):
        email_or_phone = attrs.get('email_or_phone', None)
        if email_or_phone is None:
            raise ValidationError(
                {
                    'success': False,
                    'message': "You must enter email or phone number"
                }
            )

        user = CustomUser.objects.filter(Q(email=email_or_phone) | Q(phone_number=email_or_phone))
        if not user.exists():
            raise NotFound(detail="User not found")

        attrs['user'] = user.first()

        return attrs


class ResetPasswordSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)
    password = serializers.CharField(min_length=8, write_only=True, required=True)
    confirm_password = serializers.CharField(min_length=8, write_only=True, required=True)

    class Meta:
        model = CustomUser
        fields = ('id', 'password', 'confirm_password')


    def validate(self, attrs):
        password = attrs.get('password')
        confirm_password = attrs.get('confirm_password')
        if password != confirm_password:
            raise ValidationError(
                {
                    'success': False,
                    'message': 'You passwords do not match'
                }
            )

        if password:
            validate_password(password)

        return attrs


    def update(self, instance, validated_data):  # update method will be called in serializer.save() in UpdateAPIView.
        password = validated_data.pop('password')
        instance.set_password(password)
        super(ResetPasswordSerializer, self).update(instance, validated_data)
        return instance


