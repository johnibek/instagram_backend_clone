from django.urls import path
from . import views


urlpatterns = [
    path('login/', views.LoginView.as_view(), name='login'),
    path('login/refresh', views.LoginRefreshView.as_view(), name='login_refresh'),
    path('logout/', views.LogoutAPIView.as_view(), name='logout'),
    path('forgot-password/', views.ForgotPasswordAPIView.as_view(), name='forgot_password'),
    path('reset-password/', views.ResetPasswordView.as_view(), name='reset_password'),
    path('signup/', views.SignUpUserAPIView.as_view(), name='signup'),
    path('verify/', views.VerifyAPIView.as_view(), name='verify'),
    path('new_verification_code/', views.GetNewVerificationCode.as_view(), name='new_code'),
    path('change_user_data/', views.ChangeUserDataAPIView.as_view(), name='change_user_data'),
    path('change_user_photo/', views.ChangeUserImageAPIView.as_view(), name='change_user_image'),
]