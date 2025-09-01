from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Q
from decimal import Decimal
from .models import AffiliateProfile, AffiliateReferral, AffiliatePayment
from .forms import AffiliateApplicationForm, BankDetailsForm, KYCDocumentsForm

@login_required
def affiliate_dashboard(request):
    """Main affiliate dashboard view with proper error handling"""
    try:
        affiliate = AffiliateProfile.objects.get(user=request.user)
    except AffiliateProfile.DoesNotExist:
        # User is not an affiliate yet
        context = {
            'affiliate': None,
            'active_tab': 'affiliate_dashboard'
        }
        return render(request, 'affiliate/dashboard.html', context)

    # Initialize default values
    total_referrals = 0
    approved_earnings = Decimal('0.00')
    available_balance = Decimal('0.00')
    total_settlements = Decimal('0.00')
    latest_referrals = []
    payout_eligible = False
    bank_details_complete = False

    try:
        # Get referrals with proper error handling
        referrals = AffiliateReferral.objects.filter(affiliate=affiliate)
        total_referrals = referrals.count()

        # Get approved referrals for earnings calculation
        approved_referrals = referrals.filter(status='approved')
        
        # Calculate approved earnings with proper null handling
        earnings_result = approved_referrals.aggregate(
            total=Sum('commission_amount')
        )
        approved_earnings = earnings_result['total'] if earnings_result['total'] is not None else Decimal('0.00')
        
        # Calculate total settlements with proper null handling
        settlements_result = AffiliatePayment.objects.filter(
            affiliate=affiliate,
            status='completed'
        ).aggregate(total=Sum('amount'))
        total_settlements = settlements_result['total'] if settlements_result['total'] is not None else Decimal('0.00')
        
        # Calculate available balance
        available_balance = max(Decimal('0.00'), approved_earnings - total_settlements)
        
        # Get latest referrals for dashboard display
        latest_referrals = referrals.order_by('-created_at')[:5]
        
        # Check payout eligibility
        payout_eligible = available_balance >= Decimal('5000.00')
        
        # Check bank details completion
        bank_details_complete = all([
            affiliate.account_holder_name,
            affiliate.bank_name,
            affiliate.account_number,
            affiliate.ifsc_code
        ])
        
    except Exception as e:
        # Log the error for debugging
        print(f"Error in affiliate dashboard calculations: {e}")
        messages.error(request, "Error loading dashboard data. Please try again.")

    context = {
        'affiliate': affiliate,
        'total_referrals': total_referrals,
        'approved_earnings': approved_earnings,
        'available_balance': available_balance,
        'total_settlements': total_settlements,
        'latest_referrals': latest_referrals,
        'payout_eligible': payout_eligible,
        'bank_details_complete': bank_details_complete,
        'active_tab': 'affiliate_dashboard'
    }
    
    return render(request, 'affiliate/dashboard.html', context)

@login_required
def apply_affiliate(request):
    """Apply to become an affiliate with proper error handling"""
    # Check if already an affiliate
    try:
        affiliate = AffiliateProfile.objects.get(user=request.user)
        if affiliate.status == 'approved':
            messages.info(request, "You're already an approved affiliate.")
            return redirect('affiliate:dashboard')
        elif affiliate.status == 'pending':
            messages.info(request, "Your application is still under review.")
            return redirect('affiliate:dashboard')
    except AffiliateProfile.DoesNotExist:
        affiliate = None
    
    if request.method == 'POST':
        try:
            form = AffiliateApplicationForm(request.POST, request.FILES, instance=affiliate)
            if form.is_valid():
                affiliate = form.save(commit=False)
                affiliate.user = request.user
                affiliate.status = 'pending'
                affiliate.save()
                
                messages.success(request, "Your affiliate application has been submitted for review.")
                return redirect('affiliate:dashboard')
            else:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")
        except Exception as e:
            print(f"Error in apply_affiliate: {e}")
            messages.error(request, "An error occurred while submitting your application. Please try again.")
    else:
        form = AffiliateApplicationForm(instance=affiliate)
    
    context = {
        'form': form,
        'affiliate': affiliate,
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
        try:
            form = BankDetailsForm(request.POST, instance=affiliate)
            if form.is_valid():
                form.save()
                messages.success(request, "Bank details updated successfully.")
                return redirect('affiliate:dashboard')
            else:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")
        except Exception as e:
            print(f"Error updating bank details: {e}")
            messages.error(request, "An error occurred while updating bank details.")
    else:
        form = BankDetailsForm(instance=affiliate)
    
    context = {
        'form': form,
        'affiliate': affiliate,
        'active_tab': 'affiliate_bank'
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
        try:
            form = KYCDocumentsForm(request.POST, request.FILES, instance=affiliate)
            if form.is_valid():
                form.save()
                messages.success(request, "KYC documents uploaded successfully.")
                return redirect('affiliate:dashboard')
            else:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")
        except Exception as e:
            print(f"Error uploading KYC documents: {e}")
            messages.error(request, "An error occurred while uploading documents.")
    else:
        form = KYCDocumentsForm(instance=affiliate)
    
    context = {
        'form': form,
        'affiliate': affiliate,
        'active_tab': 'affiliate_kyc'
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
    
    try:
        referrals = AffiliateReferral.objects.filter(
            affiliate=affiliate
        ).order_by('-created_at')
    except Exception as e:
        print(f"Error fetching referrals: {e}")
        referrals = []
        messages.error(request, "Error loading referrals.")
    
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
    
    # Initialize default values
    payments = []
    approved_earnings = Decimal('0.00')
    available_balance = Decimal('0.00')
    total_settlements = Decimal('0.00')
    payout_eligible = False
    
    try:
        # Get payment history
        payments = AffiliatePayment.objects.filter(
            affiliate=affiliate
        ).order_by('-payment_date')
        
        # Calculate earnings and balances
        approved_referrals = AffiliateReferral.objects.filter(
            affiliate=affiliate,
            status='approved'
        )
        
        earnings_result = approved_referrals.aggregate(total=Sum('commission_amount'))
        approved_earnings = earnings_result['total'] if earnings_result['total'] is not None else Decimal('0.00')
        
        settlements_result = AffiliatePayment.objects.filter(
            affiliate=affiliate,
            status='completed'
        ).aggregate(total=Sum('amount'))
        total_settlements = settlements_result['total'] if settlements_result['total'] is not None else Decimal('0.00')
        
        available_balance = max(Decimal('0.00'), approved_earnings - total_settlements)
        payout_eligible = available_balance >= Decimal('5000.00')
        
    except Exception as e:
        print(f"Error in payments history: {e}")
        messages.error(request, "Error loading payment history.")
    
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
    
    try:
        # Calculate available balance
        approved_referrals = AffiliateReferral.objects.filter(
            affiliate=affiliate, 
            status='approved'
        )
        
        earnings_result = approved_referrals.aggregate(total=Sum('commission_amount'))
        approved_earnings = earnings_result['total'] if earnings_result['total'] is not None else Decimal('0.00')
        
        settlements_result = AffiliatePayment.objects.filter(
            affiliate=affiliate,
            status='completed'
        ).aggregate(total=Sum('amount'))
        total_settlements = settlements_result['total'] if settlements_result['total'] is not None else Decimal('0.00')
        
        available_balance = max(Decimal('0.00'), approved_earnings - total_settlements)
        
        # Check eligibility
        if available_balance < Decimal('5000.00'):
            messages.error(request, "You need at least ₹5,000 in available balance to request a payout.")
            return redirect('affiliate:dashboard')
        
        # Check bank details
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
        
    except Exception as e:
        print(f"Error in request payout: {e}")
        messages.error(request, "An error occurred while processing your payout request.")
        return redirect('affiliate:dashboard')
    
    context = {
        'affiliate': affiliate,
        'available_balance': available_balance,
        'active_tab': 'affiliate_payments'
    }
    
    return render(request, 'affiliate/request_payout.html', context)

# Add this simple test view to affiliate/views.py
def test_view(request):
    return render(request, 'affiliate/test.html', {'message': 'Affiliate app is working!'})
