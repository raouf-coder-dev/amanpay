import random
import string

from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


def _generate_transaction_code():
    """توليد كود معاملة مكوّن من 6 أرقام فريدة."""
    while True:
        code = ''.join(random.choices(string.digits, k=6))
        if not Transaction.objects.filter(code=code).exists():
            return code


class Transaction(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', _('في الانتظار')
        FUNDED = 'FUNDED', _('ممول')
        SHIPPED = 'SHIPPED', _('تم الشحن')
        DELIVERED = 'DELIVERED', _('تم التسليم')
        COMPLETED = 'COMPLETED', _('مكتمل')
        DISPUTED = 'DISPUTED', _('متنازع عليه')
        REFUNDED = 'REFUNDED', _('مسترجع')
        CANCELLED = 'CANCELLED', _('ملغى')

    code = models.CharField(
        max_length=6,
        unique=True,
        default=_generate_transaction_code,
        editable=False,
        verbose_name=_('كود المعاملة'),
    )
    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='sales',
        verbose_name=_('البائع'),
    )
    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='purchases',
        null=True,
        blank=True,
        verbose_name=_('المشتري'),
    )
    delivery_company = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='deliveries',
        verbose_name=_('شركة التوصيل'),
    )
    product_name = models.CharField(
        max_length=255,
        verbose_name=_('اسم المنتج'),
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('الوصف'),
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name=_('المبلغ'),
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name=_('الحالة'),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('تاريخ الإنشاء'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('تاريخ التحديث'))
    release_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('تاريخ الإفراج عن المبلغ'),
    )

    class Meta:
        verbose_name = _('معاملة')
        verbose_name_plural = _('المعاملات')
        ordering = ['-created_at']

    def __str__(self):
        return f'#{self.code} — {self.product_name} ({self.get_status_display()})'


class Review(models.Model):
    RATING_CHOICES = [(i, str(i)) for i in range(1, 6)]

    transaction = models.OneToOneField(
        Transaction,
        on_delete=models.CASCADE,
        related_name='review',
        verbose_name=_('المعاملة'),
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='given_reviews',
        verbose_name=_('المقيِّم'),
    )
    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_reviews',
        verbose_name=_('البائع'),
    )
    rating = models.PositiveSmallIntegerField(
        choices=RATING_CHOICES,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name=_('التقييم'),
    )
    comment = models.TextField(
        blank=True,
        verbose_name=_('التعليق'),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('تاريخ الإنشاء'))

    class Meta:
        verbose_name = _('تقييم')
        verbose_name_plural = _('التقييمات')
        ordering = ['-created_at']

    def __str__(self):
        return f'تقييم {self.reviewer.username} للبائع {self.seller.username} — {self.rating}/5'
