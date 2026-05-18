from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    class Role(models.TextChoices):
        BUYER = 'BUYER', _('مشتري')
        SELLER = 'SELLER', _('بائع')
        DELIVERY = 'DELIVERY', _('شركة توصيل')

    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        verbose_name=_('الدور'),
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name=_('رقم الهاتف'),
    )

    # Seller fields
    store_name = models.CharField(
        max_length=150,
        blank=True,
        verbose_name=_('اسم المتجر'),
    )
    store_description = models.TextField(
        blank=True,
        verbose_name=_('وصف المتجر'),
    )

    # Identity fields
    national_id = models.CharField(
        max_length=18,
        blank=True,
        null=True,
        verbose_name=_('رقم التعريف الوطني'),
    )
    commercial_register = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name=_('رقم السجل التجاري'),
    )

    # Delivery company fields
    company_name = models.CharField(
        max_length=150,
        blank=True,
        verbose_name=_('اسم شركة التوصيل'),
    )
    company_registration = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('رقم تسجيل الشركة'),
    )

    is_verified = models.BooleanField(
        default=False,
        verbose_name=_('موثق'),
    )

    class Meta:
        verbose_name = _('مستخدم')
        verbose_name_plural = _('المستخدمون')

    def __str__(self):
        return f'{self.username} ({self.get_role_display()})'

    @property
    def is_buyer(self):
        return self.role == self.Role.BUYER

    @property
    def is_seller(self):
        return self.role == self.Role.SELLER

    @property
    def is_delivery(self):
        return self.role == self.Role.DELIVERY


class Wallet(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='wallet',
        verbose_name=_('المستخدم'),
    )
    balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=50000,
        verbose_name=_('الرصيد'),
    )
    frozen_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name=_('الرصيد المجمد'),
    )

    class Meta:
        verbose_name = _('محفظة')
        verbose_name_plural = _('المحافظ')

    def __str__(self):
        return f'محفظة {self.user.username} — {self.balance} دج'

    @property
    def available_balance(self):
        return self.balance - self.frozen_balance


class WalletTransaction(models.Model):
    TYPE_CHOICES = [
        ('CREDIT',   _('إيداع')),
        ('DEBIT',    _('خصم')),
        ('FREEZE',   _('تجميد')),
        ('UNFREEZE', _('فك تجميد')),
        ('RELEASE',  _('تحرير')),
    ]

    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name='transactions_log',
        verbose_name=_('المحفظة'),
    )
    transaction = models.ForeignKey(
        'transactions.Transaction',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('الصفقة'),
    )
    type = models.CharField(
        max_length=10,
        choices=TYPE_CHOICES,
        verbose_name=_('النوع'),
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name=_('المبلغ'),
    )
    balance_before = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name=_('الرصيد قبل العملية'),
    )
    balance_after = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name=_('الرصيد بعد العملية'),
    )
    description = models.CharField(
        max_length=255,
        verbose_name=_('الوصف'),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('التاريخ'))

    class Meta:
        verbose_name = _('سجل المحفظة')
        verbose_name_plural = _('سجلات المحفظة')
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.get_type_display()} — {self.amount} دج ({self.wallet.user.username})'


def calculate_commission(amount):
    """
    العمولة المتدرجة:
    0 - 5,000 دج      → 2%
    5,001 - 20,000 دج → 1.5%
    +20,000 دج        → 1%
    """
    amount = float(amount)
    if amount <= 5000:
        rate = 2.0
    elif amount <= 20000:
        rate = 1.5
    else:
        rate = 1.0
    commission = round(amount * rate / 100, 2)
    seller_receives = round(amount - commission, 2)
    return {
        'rate': rate,
        'commission': commission,
        'seller_receives': seller_receives,
    }


class PlatformWallet(models.Model):
    balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name=_('الرصيد'),
    )
    total_transactions = models.IntegerField(default=0, verbose_name=_('إجمالي الصفقات'))
    last_updated = models.DateTimeField(auto_now=True, verbose_name=_('آخر تحديث'))

    class Meta:
        verbose_name = _('سلة AmanPay')

    def __str__(self):
        return f'AmanPay Wallet — {self.balance} دج'

    @classmethod
    def get_instance(cls):
        wallet, _ = cls.objects.get_or_create(pk=1)
        return wallet


class CommissionLog(models.Model):
    transaction = models.OneToOneField(
        'transactions.Transaction',
        on_delete=models.CASCADE,
        related_name='commission',
        verbose_name=_('الصفقة'),
    )
    original_amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name=_('المبلغ الأصلي'))
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, verbose_name=_('نسبة العمولة'))
    commission_amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name=_('مبلغ العمولة'))
    seller_received = models.DecimalField(max_digits=12, decimal_places=2, verbose_name=_('المبلغ المحوّل للبائع'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('التاريخ'))

    class Meta:
        verbose_name = _('سجل العمولة')
        verbose_name_plural = _('سجلات العمولات')

    def __str__(self):
        return f'عمولة صفقة {self.transaction.code} — {self.commission_amount} دج'


from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_wallet(sender, instance, created, **kwargs):
    if created:
        Wallet.objects.get_or_create(
            user=instance,
            defaults={'balance': 50000, 'frozen_balance': 0}
        )
