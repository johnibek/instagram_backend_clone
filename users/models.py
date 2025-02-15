from django.core.validators import FileExtensionValidator
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext as _
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.hashers import is_password_usable

from shared.models import BaseModel
from datetime import datetime, timedelta
import random
import uuid


class CustomUser(AbstractUser, BaseModel):
    class UserRoles(models.TextChoices):
        ORDINARY_USER = "ordinary_user", _("Ordinary User")
        MANAGER = "manager", _("Manager")
        ADMIN = "admin", _("Admin")

    class AuthTypes(models.TextChoices):
        VIA_EMAIL = "via_email", _("Via Email")
        VIA_PHONE = "via_phone", _("Via Phone Number")

    class AuthStatus(models.TextChoices):
        NEW = "new", _("New")
        CODE_VERIFIED = "code_verified", _("Code Verified")
        DONE = "done", _("Done")
        PHOTO_UPLOADED = "photo_uploaded", _("Photo Uploaded")


    user_roles = models.CharField(max_length=31, choices=UserRoles.choices, default=UserRoles.ORDINARY_USER.value)
    auth_type = models.CharField(max_length=31, choices=AuthTypes.choices)
    auth_status = models.CharField(max_length=31, choices=AuthStatus.choices, default=AuthStatus.NEW.value)
    email = models.EmailField(null=True, blank=True, unique=True)
    phone_number = models.CharField(max_length=13, null=True, blank=True, unique=True)
    photo = models.ImageField(upload_to="user_images/", null=True, blank=True,
                              validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'tiff', 'heic', 'heif'])])

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


    def create_verification_code(self, verification_type):
        code = "".join([str(random.randint(0, 9)) for _ in range(4)])
        UserConfirmation.objects.create(
            user_id=self.id,
            verification_type=verification_type,
            code=code
        )
        return code


    def check_username(self):
        if not self.username:
            temp_username = f"instagram-{uuid.uuid4().__str__().split("-")[-1]}"
            while CustomUser.objects.filter(username=temp_username):
                temp_username = f"{temp_username}{random.randint(0, 9)}"
            self.username = temp_username


    def check_email(self):
        if self.email:
            normalize_email = self.email.lower()
            self.email = normalize_email


    def check_pass(self):
        if not self.password:
            temp_password = f"password-{uuid.uuid4().__str__().split("-")[-1]}"
            self.password = temp_password


    def hash_password(self):
        if not is_password_usable(self.password):
            self.set_password(self.password)


    def token(self):
        refresh = RefreshToken.for_user(self)
        return {
            "access_token": str(refresh.access_token),
            "refresh_token": str(refresh)
        }


    def save(self, *args, **kwargs):
        # Run validation before saving
        self.clean()
        super(CustomUser, self).save(*args, **kwargs)


    def clean(self):
        self.check_email()
        self.check_username()
        self.check_pass()
        self.hash_password()


    def __str__(self):
        return self.username


EMAIL_EXPIRATION_MINUTES = 5
PHONE_EXPIRATION_MINUTES = 2
VIA_EMAIL, VIA_PHONE = "via_email", "via_phone"

class UserConfirmation(BaseModel):
    VERIFICATION_TYPES = (
        (VIA_EMAIL, _("Via Email")),
        (VIA_PHONE, _("Via Phone"))
    )

    user = models.ForeignKey('users.CustomUser', on_delete=models.CASCADE, related_name="verification_codes")
    code = models.CharField(max_length=4)
    verification_type = models.CharField(max_length=31, choices=VERIFICATION_TYPES)
    expiration_time = models.DateTimeField(null=True)
    is_confirmed = models.BooleanField(default=False)


    def __str__(self):
        return f"{self.user.username} - {self.code}"


    def save(self, *args, **kwargs):
        if not self.expiration_time:
            if self.verification_type == VIA_EMAIL:
                self.expiration_time = datetime.now() + timedelta(minutes=EMAIL_EXPIRATION_MINUTES)
            elif self.verification_type == VIA_PHONE:
                self.expiration_time = datetime.now() + timedelta(minutes=PHONE_EXPIRATION_MINUTES)

        super(UserConfirmation, self).save(*args, **kwargs)
