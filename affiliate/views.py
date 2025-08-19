from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from .models import AffiliateProfile, AffiliateReferral, AffiliatePayment
from .forms import AffiliateApplicationForm, BankDetailsForm, KYCDocumentsForm

@login_required
def affiliate_dashboard(request):
    """Main affiliate dashboard view"""
    try:
        affiliate = AffiliateProfile.objects.get(user=request.user)
    except AffiliateProfile.DoesNotExist:
        # If not an affiliate yet, redirect to application page
        messages.info(request, "Apply to become an affiliate partner first.")
        return redirect('affiliate:apply')
    
    # Get referral stats
    referrals = AffiliateReferral.objects.filter(affiliate=affiliate)
    total_referrals = referrals.count()
    
    # Get business count
    business_count = referrals.values('subscription__business').distinct().count()
    
    # Check if payout threshold reached
    payout_eligible = affiliate.pending_earnings >= 5000
    
    context = {
        'affiliate': affiliate,
        'total_referrals': total_referrals,
        'business_count': business_count,
        'payout_eligible': payout_eligible,
        'active_tab': 'affiliate_dashboard'
    }
    
    return render(request, 'affiliate/dashboard.html', context)

@login_required
def apply_affiliate(request):
    """Apply to become an affiliate"""
    # Check if already an affiliate
    try:
        affiliate = AffiliateProfile.objects.get(user=request.user)
        if affiliate.status == 'approved':
            messages.info(request, "You're already an approved affiliate.")
            return redirect('affiliate:dashboard')
        elif affiliate.status == 'pending':
            messages.info(request, "Your application is still under review.")
            return redirect('affiliate:dashboard')
        # If rejected, allow to re-apply
    except AffiliateProfile.DoesNotExist:
        affiliate = None
    
    if request.method == 'POST':
        form = AffiliateApplicationForm(request.POST)
        if form.is_valid():
            affiliate = form.save(commit=False)
            affiliate.user = request.user
            affiliate.status = 'pending'
            affiliate.save()
            
            messages.success(request, "Your affiliate application has been submitted for review.")
            return redirect('affiliate:dashboard')
    else:
        form = AffiliateApplicationForm(instance=affiliate)
    
    return render(request, 'affiliate/apply.html', {'form': form})

@login_required
def update_bank_details(request):
    """Update affiliate bank details"""
    try:
        affiliate = AffiliateProfile.objects.get(user=request.user)
    except AffiliateProfile.DoesNotExist:
        messages.error(request, "You need to apply as an affiliate first.")
        return redirect('affiliate:apply')
    
    if request.method == 'POST':
        form = BankDetailsForm(request.POST, instance=affiliate)
        if form.is_valid():
            form.save()
            messages.success(request, "Bank details updated successfully.")
            return redirect('affiliate:dashboard')
    else:
        form = BankDetailsForm(instance=affiliate)
    
    return render(request, 'affiliate/bank_details.html', {'form': form})

@login_required
def upload_kyc_documents(request):
    """Upload affiliate KYC documents"""
    try:
        affiliate = AffiliateProfile.objects.get(user=request.user)
    except AffiliateProfile.DoesNotExist:
        messages.error(request, "You need to apply as an affiliate first.")
        return redirect('affiliate:apply')
    
    if request.method == 'POST':
        form = KYCDocumentsForm(request.POST, request.FILES, instance=affiliate)
        if form.is_valid():
            form.save()
            messages.success(request, "KYC documents uploaded successfully.")
            return redirect('affiliate:dashboard')
    else:
        form = KYCDocumentsForm(instance=affiliate)
    
    return render(request, 'affiliate/kyc_documents.html', {'form': form})

@login_required
def referrals_list(request):
    """View all referrals"""
    try:
        affiliate = AffiliateProfile.objects.get(user=request.user)
    except AffiliateProfile.DoesNotExist:
        messages.error(request, "You need to apply as an affiliate first.")
        return redirect('affiliate:apply')
    
    referrals = AffiliateReferral.objects.filter(affiliate=affiliate).order_by('-created_at')
    
    context = {
        'affiliate': affiliate,
        'referrals': referrals,
        'active_tab': 'affiliate_referrals'
    }
    
    return render(request, 'affiliate/referrals_list.html', context)

@login_required
def payments_history(request):
    """View payment history"""
    try:
        affiliate = AffiliateProfile.objects.get(user=request.user)
    except AffiliateProfile.DoesNotExist:
        messages.error(request, "You need to apply as an affiliate first.")
        return redirect('affiliate:apply')
    
    payments = AffiliatePayment.objects.filter(affiliate=affiliate).order_by('-payment_date')
    
    context = {
        'affiliate': affiliate,
        'payments': payments,
        'active_tab': 'affiliate_payments'
    }
    
    return render(request, 'affiliate/payment_history.html', context)
