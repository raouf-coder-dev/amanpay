from django import forms
from django.utils.translation import gettext_lazy as _
from .models import User


class BuyerRegisterForm(forms.ModelForm):
    password1 = forms.CharField(label=_('كلمة المرور'), widget=forms.PasswordInput)
    password2 = forms.CharField(label=_('تأكيد المرور'), widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['username', 'email', 'phone', 'national_id']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = True

    def clean_password2(self):
        p1 = self.cleaned_data.get('password1')
        p2 = self.cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError(_('كلمتا المرور غير متطابقتين'))
        return p2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        user.role = User.Role.BUYER
        if commit:
            user.save()
        return user


class SellerRegisterForm(forms.ModelForm):
    password1 = forms.CharField(label=_('كلمة المرور'), widget=forms.PasswordInput)
    password2 = forms.CharField(label=_('تأكيد المرور'), widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['username', 'email', 'phone', 'national_id', 'commercial_register',
                  'store_name', 'store_description']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = True
        self.fields['store_description'].required = False

    def clean_password2(self):
        p1 = self.cleaned_data.get('password1')
        p2 = self.cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError(_('كلمتا المرور غير متطابقتين'))
        return p2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        user.role = User.Role.SELLER
        if commit:
            user.save()
        return user


class DeliveryRegisterForm(forms.ModelForm):
    password1 = forms.CharField(label=_('كلمة المرور'), widget=forms.PasswordInput)
    password2 = forms.CharField(label=_('تأكيد المرور'), widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['username', 'email', 'phone', 'company_name', 'company_registration']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = True

    def clean_password2(self):
        p1 = self.cleaned_data.get('password1')
        p2 = self.cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError(_('كلمتا المرور غير متطابقتين'))
        return p2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        user.role = User.Role.DELIVERY
        if commit:
            user.save()
        return user
