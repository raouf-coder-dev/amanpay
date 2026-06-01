from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import User, Wallet


DEMO_PASSWORD = 'demo1234'

# 4 حسابات تجريبية بأسماء عامة — لا تُحذف الحسابات الموجودة.
DEMO_ACCOUNTS = [
    # username,          role,        is_staff, first_name
    ('demo_buyer',    User.Role.BUYER,    False, 'المشتري التجريبي'),
    ('demo_seller',   User.Role.SELLER,   False, 'البائع التجريبي'),
    ('demo_delivery', User.Role.DELIVERY, False, 'شركة التوصيل التجريبية'),
    # أدمن: is_staff=True. الدور يبقى موجوداً لأنه حقل مطلوب على الموديل،
    # لكن login_view يفحص is_staff قبل الدور فلا يؤثّر على التوجيه.
    ('demo_admin',    User.Role.BUYER,    True,  'المشرف التجريبي'),
]


class Command(BaseCommand):
    help = 'إنشاء 4 حسابات تجريبية بأسماء عامة لتسهيل الاختبار (idempotent).'

    def handle(self, *args, **kwargs):
        created_count = 0
        existing_count = 0

        with transaction.atomic():
            for username, role, is_staff, first_name in DEMO_ACCOUNTS:
                existing = User.objects.filter(username=username).first()
                if existing:
                    # الحساب موجود — لا نعدّل كلمة المرور ولا الحقول، فقط نضمن وجود المحفظة.
                    Wallet.objects.get_or_create(
                        user=existing,
                        defaults={'balance': 50000, 'frozen_balance': 0},
                    )
                    existing_count += 1
                    self.stdout.write(f'  - {username:14} ({role}) -- exists, left untouched')
                else:
                    # create_user يُشفّر كلمة المرور ويُطلق signal الذي ينشئ Wallet برصيد 50000
                    user = User.objects.create_user(
                        username=username,
                        password=DEMO_PASSWORD,
                        role=role,
                        is_staff=is_staff,
                        first_name=first_name,
                    )
                    # ضمان وجود المحفظة (لو لم يُطلَق الـsignal لأي سبب)
                    Wallet.objects.get_or_create(
                        user=user,
                        defaults={'balance': 50000, 'frozen_balance': 0},
                    )
                    created_count += 1
                    self.stdout.write(self.style.SUCCESS(
                        f'  + {username:14} ({role}{", staff" if is_staff else ""}) -- created'
                    ))

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'[OK] 4 demo accounts ensured (created: {created_count}, existing: {existing_count})'
        ))
        self.stdout.write(f'Password for all demo accounts: {DEMO_PASSWORD}')
