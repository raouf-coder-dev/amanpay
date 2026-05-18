from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.http import HttpResponseRedirect

from .models import User, Wallet, PlatformWallet, CommissionLog
from .forms import BuyerRegisterForm, SellerRegisterForm, DeliveryRegisterForm


FORM_MAP = {
    User.Role.BUYER:    BuyerRegisterForm,
    User.Role.SELLER:   SellerRegisterForm,
    User.Role.DELIVERY: DeliveryRegisterForm,
}


def set_language_view(request):
    lang = request.POST.get('language', 'ar')
    if lang == 'fr':
        next_url = '/fr/'
    else:
        next_url = '/'
    response = HttpResponseRedirect(next_url)
    response.set_cookie('django_language', lang, max_age=365*24*60*60)
    request.session['_language'] = lang
    return response


def landing_view(request):
    return render(request, 'accounts/landing.html')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            if user.is_staff:
                return redirect('accounts:admin_dashboard')
            elif user.role == User.Role.BUYER:
                return redirect('accounts:buyer_dashboard')
            elif user.role == User.Role.SELLER:
                return redirect('accounts:seller_dashboard')
            elif user.role == User.Role.DELIVERY:
                return redirect('accounts:delivery_dashboard')
            return redirect('accounts:dashboard')
        messages.error(request, _('اسم المستخدم أو كلمة المرور غير صحيحة'))

    return render(request, 'accounts/login.html')


def register_view(request):
    role = (
        request.POST.get('role')
        or request.GET.get('type')
        or request.session.get('register_role', User.Role.BUYER)
    )
    if role not in FORM_MAP:
        role = User.Role.BUYER
    request.session['register_role'] = role

    FormClass = FORM_MAP[role]

    if request.method == 'POST':
        print(f"[register] POST role={role} data={dict(request.POST)}")
        form = FormClass(request.POST)
        if form.is_valid():
            user = form.save()
            Wallet.objects.get_or_create(user=user, defaults={'balance': 50000, 'frozen_balance': 0})
            login(request, user)
            messages.success(request, _('تم إنشاء حسابك بنجاح!'))
            request.session.pop('register_role', None)
            return redirect('accounts:dashboard')
        else:
            print(f"[register] Form errors: {form.errors}")
    else:
        form = FormClass()

    return render(request, 'accounts/register.html', {
        'form': form,
        'register_role': role,
    })


def logout_view(request):
    logout(request)
    return redirect('accounts:login')


@login_required
def dashboard_view(request):
    role = request.user.role
    if role == User.Role.SELLER:
        return redirect('accounts:seller_dashboard')
    if role == User.Role.DELIVERY:
        return redirect('accounts:delivery_dashboard')
    return redirect('accounts:buyer_dashboard')


@login_required
def buyer_dashboard_view(request):
    from transactions.models import Transaction
    wallet = request.user.wallet
    wallet.refresh_from_db()
    transactions = Transaction.objects.filter(buyer=request.user).order_by('-created_at')
    active_count = transactions.filter(status__in=['FUNDED', 'SHIPPED']).count()
    return render(request, 'accounts/buyer_dashboard.html', {
        'transactions': transactions,
        'active_count': active_count,
        'wallet': wallet,
    })


@login_required
def seller_dashboard_view(request):
    from transactions.models import Transaction
    from django.db.models import Sum
    wallet = request.user.wallet
    wallet.refresh_from_db()
    transactions = Transaction.objects.filter(seller=request.user).order_by('-created_at')
    pending_amount = transactions.filter(
        status__in=['FUNDED', 'SHIPPED', 'DELIVERED']
    ).aggregate(total=Sum('amount'))['total'] or 0
    completed_count = transactions.filter(status='COMPLETED').count()
    delivery_companies = User.objects.filter(role=User.Role.DELIVERY)
    return render(request, 'accounts/seller_dashboard.html', {
        'transactions': transactions,
        'pending_amount': pending_amount,
        'completed_count': completed_count,
        'delivery_companies': delivery_companies,
        'wallet': wallet,
    })


@login_required
def settings_view(request):
    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name  = request.POST.get('last_name',  user.last_name)
        user.email      = request.POST.get('email',      user.email)
        user.phone      = request.POST.get('phone',      user.phone)
        if user.role == User.Role.SELLER:
            user.store_name        = request.POST.get('store_name',        user.store_name)
            user.store_description = request.POST.get('store_description', user.store_description)
        if user.role == User.Role.DELIVERY:
            user.company_name         = request.POST.get('company_name',         user.company_name)
            user.company_registration = request.POST.get('company_registration', user.company_registration)
        user.save()
        messages.success(request, _('تم حفظ التغييرات بنجاح'))
        return redirect('accounts:settings')
    return render(request, 'accounts/settings.html', {'user': request.user})


@staff_member_required(login_url='accounts:login')
def admin_dashboard_view(request):
    from transactions.models import Transaction

    now = timezone.now()

    total_users    = User.objects.filter(is_superuser=False).count()
    total_buyers   = User.objects.filter(role=User.Role.BUYER).count()
    total_sellers  = User.objects.filter(role=User.Role.SELLER).count()
    total_delivery = User.objects.filter(role=User.Role.DELIVERY).count()

    total_transactions = Transaction.objects.count()
    completed = Transaction.objects.filter(status='COMPLETED').count()
    pending   = Transaction.objects.filter(status='PENDING').count()
    funded    = Transaction.objects.filter(status='FUNDED').count()
    disputed  = Transaction.objects.filter(status='DISPUTED').count()

    platform     = PlatformWallet.get_instance()
    total_volume = Transaction.objects.filter(
        status='COMPLETED'
    ).aggregate(total=Sum('amount'))['total'] or 0

    monthly = CommissionLog.objects.filter(
        created_at__year=now.year,
        created_at__month=now.month,
    ).aggregate(
        commission=Sum('commission_amount'),
        count=Count('id'),
        volume=Sum('original_amount'),
    )

    recent_transactions = Transaction.objects.select_related(
        'seller', 'buyer', 'delivery_company'
    ).order_by('-created_at')[:10]

    recent_commissions = CommissionLog.objects.select_related(
        'transaction__seller', 'transaction__buyer'
    ).order_by('-created_at')[:5]

    top_sellers = User.objects.filter(role=User.Role.SELLER).annotate(
        total_sales=Count('sales'),
        completed_sales=Count('sales', filter=Q(sales__status='COMPLETED')),
    ).order_by('-completed_sales')[:5]

    return render(request, 'accounts/admin_dashboard.html', {
        'total_users':    total_users,
        'total_buyers':   total_buyers,
        'total_sellers':  total_sellers,
        'total_delivery': total_delivery,
        'total_transactions': total_transactions,
        'completed': completed,
        'pending':   pending,
        'funded':    funded,
        'disputed':  disputed,
        'platform':      platform,
        'total_volume':  total_volume,
        'monthly':       monthly,
        'recent_transactions': recent_transactions,
        'recent_commissions':  recent_commissions,
        'top_sellers':         top_sellers,
    })


@login_required
def delivery_dashboard_view(request):
    from transactions.models import Transaction
    transactions = Transaction.objects.filter(delivery_company=request.user).order_by('-created_at')
    shipped_count   = transactions.filter(status='SHIPPED').count()
    delivered_count = transactions.filter(status='DELIVERED').count()
    disputed_count  = transactions.filter(status='DISPUTED').count()
    return render(request, 'accounts/delivery_dashboard.html', {
        'transactions': transactions,
        'shipped_count':   shipped_count,
        'delivered_count': delivered_count,
        'disputed_count':  disputed_count,
    })
