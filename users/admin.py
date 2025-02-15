from django.contrib import admin
from .models import CustomUser, UserConfirmation


class CustomUserModelAdmin(admin.ModelAdmin):
    list_display = ['id', 'username', 'email', 'phone_number']

admin.site.register(CustomUser, CustomUserModelAdmin)
admin.site.register(UserConfirmation)