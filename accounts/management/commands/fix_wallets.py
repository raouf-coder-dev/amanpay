from django.core.management.base import BaseCommand
from accounts.models import User, Wallet


class Command(BaseCommand):
    help = 'Create a Wallet for any user that does not have one.'

    def handle(self, *args, **kwargs):
        fixed = 0
        total = User.objects.count()
        for user in User.objects.all():
            wallet, created = Wallet.objects.get_or_create(
                user=user,
                defaults={'balance': 50000, 'frozen_balance': 0},
            )
            if created:
                fixed += 1
                # ASCII-safe — Windows console may not handle Arabic stdout
                self.stdout.write(self.style.SUCCESS(f'  + wallet created for: {user.username}'))
        if fixed == 0:
            self.stdout.write(self.style.SUCCESS(f'OK — all {total} users already have a wallet.'))
        else:
            self.stdout.write(self.style.SUCCESS(f'OK — {fixed} wallet(s) created (out of {total} users).'))
