from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User, Wallet, PlatformWallet, CommissionLog


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'phone', 'is_verified', 'is_staff', 'date_joined')
    list_filter = ('role', 'is_verified', 'is_staff', 'is_active')
    search_fields = ('username', 'email', 'phone', 'store_name', 'company_name')
    ordering = ('-date_joined',)

    fieldsets = UserAdmin.fieldsets + (
        (_('معلومات AmanPay'), {
            'fields': ('role', 'phone', 'is_verified'),
        }),
        (_('بيانات الهوية'), {
            'fields': ('national_id', 'commercial_register'),
            'classes': ('collapse',),
        }),
        (_('بيانات البائع'), {
            'fields': ('store_name', 'store_description'),
            'classes': ('collapse',),
        }),
        (_('بيانات شركة التوصيل'), {
            'fields': ('company_name', 'company_registration'),
            'classes': ('collapse',),
        }),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        (_('معلومات AmanPay'), {
            'fields': ('role', 'phone'),
        }),
    )


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance', 'frozen_balance', 'available_balance')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('available_balance',)

    @admin.display(description=_('الرصيد المتاح'))
    def available_balance(self, obj):
        return obj.available_balance


@admin.register(PlatformWallet)
class PlatformWalletAdmin(admin.ModelAdmin):
    list_display = ['balance', 'total_transactions', 'last_updated']


@admin.register(CommissionLog)
class CommissionLogAdmin(admin.ModelAdmin):
    list_display = ['transaction', 'original_amount', 'commission_rate', 'commission_amount', 'seller_received', 'created_at']
    list_filter = ['commission_rate', 'created_at']
