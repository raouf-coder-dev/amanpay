from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Avg
from django.shortcuts import redirect, render, get_object_or_404
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from accounts.models import User, Wallet, WalletTransaction, PlatformWallet, CommissionLog, calculate_commission
from .forms import CreateTransactionForm
from .models import Transaction, Review


# ── helpers ────────────────────────────────────────────────────────────────

def _seller_stats(seller):
    total = Transaction.objects.filter(seller=seller).count()
    completed = Transaction.objects.filter(seller=seller, status='COMPLETED').count()
    return {
        'total': total,
        'completed': completed,
        'rating': Review.objects.filter(seller=seller).aggregate(Avg('rating'))['rating__avg'] or 0,
        'reviews_count': Review.objects.filter(seller=seller).count(),
        'success_rate': (completed / total * 100) if total > 0 else 0,
    }


def _buyer_stats(buyer):
    total = Transaction.objects.filter(buyer=buyer).count()
    completed = Transaction.objects.filter(buyer=buyer, status='COMPLETED').count()
    return {
        'total': total,
        'completed': completed,
        'success_rate': (completed / total * 100) if total > 0 else 0,
    }


def _log(wallet, tx, op_type, amount, balance_before, description):
    WalletTransaction.objects.create(
        wallet=wallet,
        transaction=tx,
        type=op_type,
        amount=amount,
        balance_before=balance_before,
        balance_after=wallet.available_balance,
        description=description,
    )


# ── seller: create ──────────────────────────────────────────────────────────

@login_required
def create_transaction(request):
    if request.user.role != User.Role.SELLER:
        messages.error(request, _('هذه الصفحة مخصصة للبائعين فقط'))
        return redirect('accounts:dashboard')

    if request.method == 'POST':
        form = CreateTransactionForm(request.POST)
        if form.is_valid():
            Transaction.objects.create(
                seller=request.user,
                buyer=None,
                delivery_company=form.cleaned_data['delivery_company'],
                product_name=form.cleaned_data['product_name'],
                description=form.cleaned_data['description'],
                amount=form.cleaned_data['amount'],
                status=Transaction.Status.PENDING,
            )
            messages.success(request, _('تم إنشاء الصفقة بنجاح — شارك الكود مع المشتري'))
        else:
            for field, errors in form.errors.items():
                label = form.fields[field].label if field != '__all__' else ''
                for error in errors:
                    messages.error(request, f'{label}: {error}' if label else error)

    return redirect('accounts:seller_dashboard')


# ── seller: ship ────────────────────────────────────────────────────────────

@login_required
def ship_transaction(request, pk):
    tx = get_object_or_404(Transaction, pk=pk, seller=request.user)
    if request.method == 'POST' and tx.status == Transaction.Status.FUNDED:
        tx.status = Transaction.Status.SHIPPED
        tx.save()
        messages.success(request, _('تم تأكيد الشحن بنجاح'))
    return redirect('transactions:detail', pk=pk)


# ── buyer: join → preview → fund → withdraw ────────────────────────────────

@login_required
def join_transaction(request):
    if request.user.role != User.Role.BUYER:
        messages.error(request, _('هذه الصفحة مخصصة للمشترين فقط'))
        return redirect('accounts:dashboard')

    if request.method == 'POST':
        code = request.POST.get('code', '').strip()
        tx = Transaction.objects.filter(code=code, status=Transaction.Status.PENDING).first()

        if not tx:
            messages.error(request, _('كود الصفقة غير صحيح أو لم تعد متاحة'))
            return redirect('accounts:buyer_dashboard')

        if tx.buyer is not None:
            messages.error(request, _('انضم مشترٍ آخر بالفعل لهذه الصفقة'))
            return redirect('accounts:buyer_dashboard')

        if tx.seller == request.user:
            messages.error(request, _('لا يمكنك الانضمام لصفقتك الخاصة'))
            return redirect('accounts:buyer_dashboard')

        tx.buyer = request.user
        tx.save()
        return redirect('transactions:preview', pk=tx.pk)

    return redirect('accounts:buyer_dashboard')


@login_required
def preview_transaction(request, pk):
    tx = get_object_or_404(Transaction, pk=pk, buyer=request.user)
    return render(request, 'transactions/preview_transaction.html', {
        'transaction': tx,
        'seller_stats': _seller_stats(tx.seller),
    })


@login_required
def fund_transaction(request, pk):
    tx = get_object_or_404(Transaction, pk=pk, buyer=request.user, status=Transaction.Status.PENDING)
    if request.method == 'POST':
        wallet, _created = Wallet.objects.get_or_create(
            user=request.user,
            defaults={'balance': 50000, 'frozen_balance': 0},
        )
        if wallet.available_balance >= tx.amount:
            bal_before = wallet.available_balance
            wallet.frozen_balance += tx.amount
            wallet.save()
            wallet.refresh_from_db()
            _log(wallet, tx, 'FREEZE', tx.amount, bal_before, f'تجميد مبلغ صفقة {tx.code}')
            tx.status = Transaction.Status.FUNDED
            tx.save()
            messages.success(request, _('تم تجميد المبلغ بنجاح — الصفقة ممولة'))
            return redirect('transactions:detail', pk=pk)
        else:
            messages.error(
                request,
                _('رصيدك المتاح غير كافٍ — تحتاج %(amount)s دج') % {'amount': tx.amount}
            )
    return redirect('transactions:preview', pk=pk)


@login_required
def withdraw_transaction(request, pk):
    tx = get_object_or_404(Transaction, pk=pk, buyer=request.user)
    if request.method == 'POST':
        if tx.status == Transaction.Status.FUNDED:
            wallet, _created = Wallet.objects.get_or_create(
                user=request.user,
                defaults={'balance': 50000, 'frozen_balance': 0},
            )
            bal_before = wallet.available_balance
            wallet.frozen_balance -= tx.amount
            wallet.save()
            wallet.refresh_from_db()
            _log(wallet, tx, 'UNFREEZE', tx.amount, bal_before, f'فك تجميد مبلغ صفقة {tx.code}')
            tx.buyer = None
            tx.status = Transaction.Status.PENDING
            tx.save()
            messages.success(request, _('تم الانسحاب وإعادة المبلغ'))
            return redirect('accounts:buyer_dashboard')
        messages.error(request, _('لا يمكن الانسحاب في هذه المرحلة'))
    return redirect('transactions:detail', pk=pk)


# ── buyer: confirm delivery ─────────────────────────────────────────────────

@login_required
def confirm_delivery(request, pk):
    tx = get_object_or_404(Transaction, pk=pk, buyer=request.user)
    if request.method == 'POST' and tx.status == Transaction.Status.SHIPPED:
        tx.status = Transaction.Status.DELIVERED
        tx.save()
        messages.success(request, _('تم تأكيد استلام الطرد'))
    return redirect('transactions:detail', pk=pk)


# ── delivery: complete / dispute ────────────────────────────────────────────

@login_required
def complete_transaction(request, pk):
    from decimal import Decimal
    transaction = get_object_or_404(
        Transaction, pk=pk, delivery_company=request.user
    )
    if request.method == 'POST' and transaction.status == Transaction.Status.DELIVERED:
        amount = Decimal(str(transaction.amount))

        commission_data = calculate_commission(amount)
        commission = Decimal(str(commission_data['commission']))
        seller_receives = Decimal(str(commission_data['seller_receives']))
        rate = commission_data['rate']

        # 1 — محفظة المشتري
        buyer_wallet = Wallet.objects.select_for_update().get(
            user=transaction.buyer
        )
        buyer_wallet.balance -= amount
        buyer_wallet.frozen_balance -= amount
        buyer_wallet.save()
        buyer_wallet.refresh_from_db()

        WalletTransaction.objects.create(
            wallet=buyer_wallet,
            transaction=transaction,
            type='DEBIT',
            amount=amount,
            balance_after=buyer_wallet.balance,
            description=f'خصم صفقة {transaction.code} — عمولة {rate}%'
        )

        # 2 — محفظة البائع
        seller_wallet = Wallet.objects.select_for_update().get(
            user=transaction.seller
        )
        seller_wallet.balance += seller_receives
        seller_wallet.save()
        seller_wallet.refresh_from_db()

        WalletTransaction.objects.create(
            wallet=seller_wallet,
            transaction=transaction,
            type='CREDIT',
            amount=seller_receives,
            balance_after=seller_wallet.balance,
            description=f'تحويل صفقة {transaction.code} بعد عمولة {rate}%'
        )

        # 3 — سلة AmanPay
        platform = PlatformWallet.get_instance()
        platform.balance += commission
        platform.total_transactions += 1
        platform.save()

        # 4 — سجل العمولة
        CommissionLog.objects.get_or_create(
            transaction=transaction,
            defaults={
                'original_amount': amount,
                'commission_rate': rate,
                'commission_amount': commission,
                'seller_received': seller_receives,
            }
        )

        transaction.status = Transaction.Status.COMPLETED
        transaction.release_date = timezone.now()
        transaction.save()
        messages.success(
            request,
            f'تم تحرير الأموال — البائع استلم {seller_receives} دج — عمولة AmanPay: {commission} دج'
        )

    return redirect('transactions:detail', pk=transaction.pk)


@login_required
def dispute_transaction(request, pk):
    tx = get_object_or_404(Transaction, pk=pk)
    allowed = (
        request.user == tx.delivery_company and
        tx.status in (Transaction.Status.DELIVERED,)
    )
    if request.method == 'POST' and allowed:
        tx.status = Transaction.Status.DISPUTED
        tx.save()
        messages.warning(request, _('تم رفع الإشكال — سيراجعه الفريق'))
    return redirect('transactions:detail', pk=pk)


# ── buyer: review ───────────────────────────────────────────────────────────

@login_required
def review_transaction(request, pk):
    tx = get_object_or_404(Transaction, pk=pk, buyer=request.user, status='COMPLETED')
    if hasattr(tx, 'review'):
        messages.error(request, _('قمت بالتقييم مسبقاً'))
        return redirect('transactions:detail', pk=pk)

    if request.method == 'POST':
        rating = request.POST.get('rating')
        comment = request.POST.get('comment', '')
        Review.objects.create(
            transaction=tx,
            reviewer=request.user,
            seller=tx.seller,
            rating=rating,
            comment=comment,
        )
        messages.success(request, _('تم إرسال تقييمك بنجاح'))
        return redirect('transactions:detail', pk=pk)

    return render(request, 'transactions/review_transaction.html', {'transaction': tx})


# ── shared: detail + wallet history ────────────────────────────────────────

@login_required
def transaction_detail(request, pk):
    tx = get_object_or_404(Transaction, pk=pk)
    # الأدمن (is_staff) يقرأ كل الصفقات؛ غيره يجب أن يكون طرفاً فيها.
    if not request.user.is_staff and request.user not in (tx.seller, tx.buyer, tx.delivery_company):
        messages.error(request, _('ليس لديك صلاحية لعرض هذه الصفقة'))
        return redirect('accounts:dashboard')

    context = {'transaction': tx}
    if request.user == tx.buyer:
        context['seller_stats'] = _seller_stats(tx.seller)
    if request.user == tx.seller and tx.buyer:
        context['buyer_stats'] = _buyer_stats(tx.buyer)

    return render(request, 'transactions/transaction_detail.html', context)


@login_required
def wallet_history(request):
    wallet, _created = Wallet.objects.get_or_create(
        user=request.user,
        defaults={'balance': 50000, 'frozen_balance': 0},
    )
    logs = wallet.transactions_log.select_related('transaction').all()
    return render(request, 'accounts/wallet_history.html', {'logs': logs})
