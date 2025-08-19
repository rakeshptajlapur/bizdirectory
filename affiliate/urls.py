# affiliate/urls.py
from django.urls import path

from . import views

app_name = 'affiliate'

urlpatterns = [
    path('dashboard/', views.affiliate_dashboard, name='dashboard'),
    path('apply/', views.apply_affiliate, name='apply'),
    path('bank-details/', views.update_bank_details, name='bank_details'),
    path('kyc/', views.upload_kyc_documents, name='kyc'),
    path('referrals/', views.referrals_list, name='referrals'),
    path('payments/', views.payments_history, name='payments'),
]