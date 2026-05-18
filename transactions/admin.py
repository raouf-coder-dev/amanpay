from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Transaction, Review


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('code', 'product_name', 'buyer', 'seller', 'delivery_company', 'amount', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('code', 'product_name', 'buyer__username', 'seller__username')
    ordering = ('-created_at',)
    readonly_fields = ('code', 'created_at', 'updated_at')

    fieldsets = (
        (_('معلومات المعاملة'), {
            'fields': ('code', 'status', 'release_date'),
        }),
        (_('الأطراف'), {
            'fields': ('buyer', 'seller', 'delivery_company'),
        }),
        (_('تفاصيل المنتج'), {
            'fields': ('product_name', 'description', 'amount'),
        }),
        (_('التواريخ'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('buyer', 'seller', 'delivery_company')


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('transaction', 'reviewer', 'seller', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('reviewer__username', 'seller__username', 'transaction__code')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('transaction', 'reviewer', 'seller')
