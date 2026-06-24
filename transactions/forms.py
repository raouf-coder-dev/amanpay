from django import forms
from django.utils.translation import gettext_lazy as _

from accounts.models import User
from .models import (
    Transaction,
    MIN_TRANSACTION_AMOUNT,
    MAX_TRANSACTION_AMOUNT,
)


class CreateTransactionForm(forms.Form):
    product_name = forms.CharField(
        label=_('اسم المنتج'),
        max_length=255,
    )
    description = forms.CharField(
        label=_('الوصف'),
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False,
    )
    amount = forms.DecimalField(
        label=_('المبلغ (دج)'),
        min_value=MIN_TRANSACTION_AMOUNT,
        max_value=MAX_TRANSACTION_AMOUNT,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'min': str(int(MIN_TRANSACTION_AMOUNT)),
            'max': str(int(MAX_TRANSACTION_AMOUNT)),
            'step': '0.01',
            'placeholder': _('من 10,000 إلى 1,000,000 دج'),
        }),
    )
    delivery_company = forms.ModelChoiceField(
        label=_('شركة التوصيل'),
        queryset=User.objects.filter(role=User.Role.DELIVERY),
        empty_label=_('— اختر شركة التوصيل —'),
        required=False,
    )

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is None:
            return amount
        if amount < MIN_TRANSACTION_AMOUNT:
            raise forms.ValidationError(_('المبلغ الأدنى للصفقة هو 10,000 دج'))
        if amount > MAX_TRANSACTION_AMOUNT:
            raise forms.ValidationError(_('المبلغ الأقصى للصفقة هو 1,000,000 دج'))
        return amount
