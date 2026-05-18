from django import forms
from django.utils.translation import gettext_lazy as _

from accounts.models import User
from .models import Transaction


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
        min_value=1,
        decimal_places=2,
    )
    delivery_company = forms.ModelChoiceField(
        label=_('شركة التوصيل'),
        queryset=User.objects.filter(role=User.Role.DELIVERY),
        empty_label=_('— اختر شركة التوصيل —'),
        required=False,
    )

