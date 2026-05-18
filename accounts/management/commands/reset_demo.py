from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = 'مسح بيانات الاختبار وإعادة الأرصدة للوضع الطبيعي'

    def handle(self, *args, **kwargs):
        with transaction.atomic():
            from transactions.models import Transaction, Review
            from accounts.models import WalletTransaction, CommissionLog, PlatformWallet

            Review.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('[OK] Reviews deleted'))

            CommissionLog.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('[OK] CommissionLog deleted'))

            WalletTransaction.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('[OK] WalletTransaction deleted'))

            Transaction.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('[OK] Transactions deleted'))

            from accounts.models import Wallet
            count = Wallet.objects.all().update(balance=50000, frozen_balance=0)
            self.stdout.write(self.style.SUCCESS(f'[OK] {count} wallets reset to 50,000 DZD'))

            platform, _ = PlatformWallet.objects.get_or_create(pk=1)
            platform.balance = 0
            platform.total_transactions = 0
            platform.save()
            self.stdout.write(self.style.SUCCESS('[OK] PlatformWallet reset'))

            from accounts.models import User
            users = User.objects.exclude(is_superuser=True)
            self.stdout.write('\n--- Current state ---')
            for user in users:
                try:
                    self.stdout.write(
                        f'  {user.username} ({user.role}) — balance: {user.wallet.balance} DZD'
                    )
                except Exception:
                    pass

            self.stdout.write(self.style.SUCCESS('\n[DONE] System reset successfully!'))
