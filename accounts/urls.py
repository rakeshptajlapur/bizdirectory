from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
from . import views, forms

app_name = 'accounts'

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Profile management
    path('profile/', views.profile_view, name='profile'),
    path('upgrade-to-business/', views.upgrade_to_business, name='upgrade_to_business'),

    # Password management
    path('password-change/', views.CustomPasswordChangeView.as_view(), name='password_change'),
    path('password-change-done/', auth_views.PasswordChangeDoneView.as_view(
        template_name='accounts/password_change_done.html'
    ), name='password_change_done'),

    # Password reset workflow
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='accounts/password_reset_form.html',
        email_template_name='accounts/password_reset_email.html',
        success_url=reverse_lazy('accounts:password_reset_done'),
        form_class=forms.CustomPasswordResetForm
    ), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='accounts/password_reset_done.html'
    ), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='accounts/password_reset_confirm.html',
        success_url=reverse_lazy('accounts:password_reset_complete')
    ), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='accounts/password_reset_complete.html'
    ), name='password_reset_complete'),
]