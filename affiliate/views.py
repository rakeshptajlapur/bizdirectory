import logging
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from .models import AffiliateProfile, AffiliateReferral, AffiliatePayment
from .forms import AffiliateApplicationForm, BankDetailsForm, KYCDocumentsForm

logger = logging.getLogger(__name__)

@login_required
def affiliate_dashboard(request):
    """Main affiliate dashboard view"""
    try:
        affiliate = AffiliateProfile.objects.get(user=request.user)
    except AffiliateProfile.DoesNotExist:
        messages.info(request, "Apply to become an affiliate partner first.")
        return redirect('affiliate:apply')

    # Get all referrals
    referrals = AffiliateReferral.objects.filter(affiliate=affiliate)
    total_referrals = referrals.count()

    # Get only approved referrals for earnings calculation
    approved_referrals = referrals.filter(status='approved')
    
    # 1. TOTAL EARNINGS: Sum of all approved referral commissions
    approved_earnings = approved_referrals.aggregate(Sum('commission_amount'))['commission_amount__sum'] or 0
    
    # 2. TOTAL SETTLEMENTS: Sum of all completed payments (NOT from affiliate.paid_earnings)
    total_settlements = AffiliatePayment.objects.filter(
        affiliate=affiliate,
        status='completed'
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    # 3. AVAILABLE BALANCE: Total Earnings - Total Settlements
    available_balance = max(0, approved_earnings - total_settlements)
    
    # Get latest referrals for dashboard display
    latest_referrals = referrals.order_by('-created_at')[:5]
    
    # Check if payout threshold reached and bank details submitted
    payout_eligible = (available_balance >= 5000)
    bank_details_complete = all([
        affiliate.account_holder_name,
        affiliate.bank_name,
        affiliate.account_number,
        affiliate.ifsc_code
    ])
    
    context = {
        'affiliate': affiliate,
        'total_referrals': total_referrals,
        'approved_earnings': approved_earnings,
        'available_balance': available_balance,
        'total_settlements': total_settlements,
        'business_count': referrals.values('subscription__business').distinct().count(),
        'referrals': latest_referrals,
        'payout_eligible': payout_eligible,
        'bank_details_complete': bank_details_complete,
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
        form = AffiliateApplicationForm(request.POST, request.FILES, instance=affiliate)
        if form.is_valid():
            # Log file uploads before saving
            aadhar_card = request.FILES.get('aadhar_card')
            if aadhar_card:
                logger.info(f"Affiliate Aadhar card upload attempt: user={request.user.id}, file={aadhar_card.name}, size={aadhar_card.size}B, type={aadhar_card.content_type}")
                
            pan_card = request.FILES.get('pan_card')
            if pan_card:
                logger.info(f"Affiliate PAN card upload attempt: user={request.user.id}, file={pan_card.name}, size={pan_card.size}B, type={pan_card.content_type}")
            
            affiliate = form.save(commit=False)
            affiliate.user = request.user
            affiliate.status = 'pending'
            affiliate.save()
            
            logger.info(f"Affiliate application submitted with documents: user={request.user.id}, aadhar={bool(aadhar_card)}, pan={bool(pan_card)}")
            messages.success(request, "Your affiliate application with KYC documents has been submitted for review.")
            return redirect('affiliate:dashboard')
    else:
        form = AffiliateApplicationForm(instance=affiliate)
    
    context = {
        'form': form,
        'active_tab': 'affiliate_apply'
    }
    return render(request, 'affiliate/apply.html', context)

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
    
    context = {
        'form': form,
        'active_tab': 'affiliate_bank'  # Make sure this is set
    }
    
    return render(request, 'affiliate/bank_details.html', context)

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
            # Log file uploads before saving
            aadhar_card = request.FILES.get('aadhar_card')
            if aadhar_card:
                logger.info(f"Affiliate Aadhar card upload attempt: user={request.user.id}, file={aadhar_card.name}, size={aadhar_card.size}B, type={aadhar_card.content_type}")
                
            pan_card = request.FILES.get('pan_card')
            if pan_card:
                logger.info(f"Affiliate PAN card upload attempt: user={request.user.id}, file={pan_card.name}, size={pan_card.size}B, type={pan_card.content_type}")
            
            form.save()
            logger.info(f"Affiliate KYC documents uploaded: user={request.user.id}, aadhar={bool(aadhar_card)}, pan={bool(pan_card)}")
            messages.success(request, "KYC documents uploaded successfully.")
            return redirect('affiliate:dashboard')
    else:
        form = KYCDocumentsForm(instance=affiliate)
    
    context = {
        'form': form,
        'affiliate': affiliate,
        'active_tab': 'affiliate_kyc'  # Make sure this is set
    }
    
    return render(request, 'affiliate/kyc_documents.html', context)

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
    
    # Calculate approved earnings from approved referrals
    approved_referrals = AffiliateReferral.objects.filter(
        affiliate=affiliate,
        status='approved'
    )
    approved_earnings = approved_referrals.aggregate(Sum('commission_amount'))['commission_amount__sum'] or 0
    
    # Calculate total settlements from completed payments
    total_settlements = AffiliatePayment.objects.filter(
        affiliate=affiliate,
        status='completed'
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Calculate available balance
    available_balance = max(0, approved_earnings - total_settlements)
    
    # Check if eligible for payout
    payout_eligible = available_balance >= 5000
    
    context = {
        'affiliate': affiliate,
        'payments': payments,
        'approved_earnings': approved_earnings,
        'available_balance': available_balance,
        'total_settlements': total_settlements,
        'payout_eligible': payout_eligible,
        'active_tab': 'affiliate_payments'
    }
    
    return render(request, 'affiliate/payment_history.html', context)

@login_required
def request_payout(request):
    """Request payout for available balance"""
    try:
        affiliate = AffiliateProfile.objects.get(user=request.user)
    except AffiliateProfile.DoesNotExist:
        messages.error(request, "You need to apply as an affiliate first.")
        return redirect('affiliate:apply')
    
    # Calculate available balance from approved referrals and completed payments
    approved_referrals = AffiliateReferral.objects.filter(
        affiliate=affiliate, 
        status='approved'
    )
    approved_earnings = approved_referrals.aggregate(Sum('commission_amount'))['commission_amount__sum'] or 0
    
    total_settlements = AffiliatePayment.objects.filter(
        affiliate=affiliate,
        status='completed'
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    available_balance = max(0, approved_earnings - total_settlements)
    
    # Check if eligible for payout
    if available_balance < 5000:
        messages.error(request, "You need at least ₹5,000 in available balance to request a payout.")
        return redirect('affiliate:dashboard')
    
    # Check if bank details are complete
    bank_details_complete = all([
        affiliate.account_holder_name,
        affiliate.bank_name,
        affiliate.account_number,
        affiliate.ifsc_code
    ])
    
    if not bank_details_complete:
        messages.warning(request, "Please complete your bank details before requesting a payout.")
        return redirect('affiliate:bank_details')
    
    if request.method == 'POST':
        # Create payment record
        payment = AffiliatePayment.objects.create(
            affiliate=affiliate,
            amount=available_balance,
            status='processing'
        )
        
        messages.success(request, "Your payout request has been submitted successfully! We'll process it within 2-4 business days.")
        return redirect('affiliate:payments')
    
    context = {
        'affiliate': affiliate,
        'available_balance': available_balance,
        'active_tab': 'affiliate_payments'
    }
    
    return render(request, 'affiliate/request_payout.html', context)
