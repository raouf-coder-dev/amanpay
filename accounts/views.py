from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.db.models import Sum, Count, Q, Avg
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
    if request.user.is_staff:
        return redirect('accounts:admin_dashboard')
    role = request.user.role
    if role == User.Role.SELLER:
        return redirect('accounts:seller_dashboard')
    if role == User.Role.DELIVERY:
        return redirect('accounts:delivery_dashboard')
    return redirect('accounts:buyer_dashboard')


@login_required
def buyer_dashboard_view(request):
    from transactions.models import Transaction
    wallet, _created = Wallet.objects.get_or_create(
        user=request.user,
        defaults={'balance': 50000, 'frozen_balance': 0},
    )
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
    wallet, _created = Wallet.objects.get_or_create(
        user=request.user,
        defaults={'balance': 50000, 'frozen_balance': 0},
    )
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
    from django.db.models.functions import TruncMonth
    from datetime import timedelta

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

    # ── Feature 1: user search (GET, read-only) ─────────────────────────────
    search_query = request.GET.get('q', '').strip()
    search_result = None
    search_no_match = False
    if search_query:
        if search_query.isdigit():
            search_result = User.objects.filter(
                Q(id=search_query) | Q(username__iexact=search_query)
            ).first()
        else:
            search_result = User.objects.filter(username__iexact=search_query).first()
        if search_result is None:
            search_no_match = True
        else:
            search_result.tx_count = Transaction.objects.filter(
                Q(seller=search_result) | Q(buyer=search_result) | Q(delivery_company=search_result)
            ).count()

    # ── Feature 1b: transaction search by ID or code (GET, read-only) ───────
    tx_search_query = request.GET.get('tx_q', '').strip()
    tx_search_no_match = False
    if tx_search_query:
        tx_match = None
        if tx_search_query.isdigit():
            tx_match = (
                Transaction.objects.filter(Q(id=tx_search_query) | Q(code=tx_search_query)).first()
                or Transaction.objects.filter(code=tx_search_query).first()
            )
        else:
            tx_match = Transaction.objects.filter(code__iexact=tx_search_query).first()
        if tx_match:
            return redirect('transactions:detail', pk=tx_match.pk)
        tx_search_no_match = True

    # ── Feature 2: transactions filter by date range + status ───────────────
    date_from = request.GET.get('date_from', '').strip()
    date_to   = request.GET.get('date_to', '').strip()
    status_filter = request.GET.get('status_filter', '').strip()

    tx_qs = Transaction.objects.select_related(
        'seller', 'buyer', 'delivery_company'
    ).order_by('-created_at')

    filter_active = bool(date_from or date_to or status_filter)
    if date_from:
        tx_qs = tx_qs.filter(created_at__date__gte=date_from)
    if date_to:
        tx_qs = tx_qs.filter(created_at__date__lte=date_to)
    if status_filter:
        tx_qs = tx_qs.filter(status=status_filter)

    # عند تطبيق فلتر اعرض كل المطابقات (مقيّدة بـ 200 لأمان الأداء)؛ وإلا آخر 10 كالسلوك الحالي.
    recent_transactions = tx_qs[:200] if filter_active else tx_qs[:10]

    recent_commissions = CommissionLog.objects.select_related(
        'transaction__seller', 'transaction__buyer'
    ).order_by('-created_at')[:5]

    top_sellers = User.objects.filter(role=User.Role.SELLER).annotate(
        total_sales=Count('sales'),
        completed_sales=Count('sales', filter=Q(sales__status='COMPLETED')),
    ).order_by('-completed_sales')[:5]

    # ── All users (latest 50, with wallet prefetched) ──────────────────────
    all_users = User.objects.select_related('wallet').order_by('-id')[:50]

    # ── Feature 3: monthly commissions chart — last 6 months ────────────────
    six_months_ago = (now - timedelta(days=183)).replace(day=1)
    monthly_qs = (
        CommissionLog.objects
        .filter(created_at__gte=six_months_ago)
        .annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(total=Sum('commission_amount'), count=Count('id'))
        .order_by('month')
    )
    monthly_chart = [
        {
            'label': row['month'].strftime('%Y-%m'),
            'total': float(row['total'] or 0),
            'count': row['count'],
        }
        for row in monthly_qs
    ]

    # خيارات حالات الصفقة لـ select الفلتر (نمرّر الـ choices الكاملة)
    status_choices = Transaction.Status.choices

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
        'all_users':           all_users,
        # search
        'search_query':    search_query,
        'search_result':   search_result,
        'search_no_match': search_no_match,
        # filter
        'date_from':      date_from,
        'date_to':        date_to,
        'status_filter':  status_filter,
        'status_choices': status_choices,
        'filter_active':  filter_active,
        # chart
        'monthly_chart':  monthly_chart,
    })


@staff_member_required(login_url='accounts:login')
def admin_user_detail(request, user_id):
    from transactions.models import Transaction, Review

    user = get_object_or_404(User, pk=user_id)
    wallet, _created = Wallet.objects.get_or_create(
        user=user,
        defaults={'balance': 50000, 'frozen_balance': 0},
    )

    sales_count     = Transaction.objects.filter(seller=user).count()
    purchases_count = Transaction.objects.filter(buyer=user).count()
    deliveries_count = Transaction.objects.filter(delivery_company=user).count()

    avg_rating = Review.objects.filter(seller=user).aggregate(avg=Avg('rating'))['avg'] or 0
    reviews_count = Review.objects.filter(seller=user).count()

    commissions_paid = CommissionLog.objects.filter(
        transaction__seller=user
    ).aggregate(total=Sum('commission_amount'))['total'] or 0

    user_transactions = Transaction.objects.filter(
        Q(seller=user) | Q(buyer=user) | Q(delivery_company=user)
    ).select_related('seller', 'buyer', 'delivery_company').order_by('-created_at')[:50]

    return render(request, 'accounts/admin_user_detail.html', {
        'profile_user':     user,
        'wallet':           wallet,
        'sales_count':      sales_count,
        'purchases_count':  purchases_count,
        'deliveries_count': deliveries_count,
        'avg_rating':       avg_rating,
        'reviews_count':    reviews_count,
        'commissions_paid': commissions_paid,
        'user_transactions': user_transactions,
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
