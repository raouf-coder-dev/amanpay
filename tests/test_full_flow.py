from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import User, Wallet, PlatformWallet
from transactions.models import Transaction
from decimal import Decimal


class FullFlowTest(TestCase):

    def setUp(self):
        self.buyer = User.objects.create_user(
            username='buyer_test', password='test123', role='BUYER'
        )
        self.seller = User.objects.create_user(
            username='seller_test', password='test123', role='SELLER'
        )
        self.delivery = User.objects.create_user(
            username='delivery_test', password='test123', role='DELIVERY'
        )
        # post_save signal already created wallets for each user above —
        # override their balances to match the expected test fixture state.
        Wallet.objects.update_or_create(
            user=self.buyer,   defaults={'balance': 50000, 'frozen_balance': 0}
        )
        Wallet.objects.update_or_create(
            user=self.seller,  defaults={'balance': 50000, 'frozen_balance': 0}
        )
        Wallet.objects.update_or_create(
            user=self.delivery, defaults={'balance': 0, 'frozen_balance': 0}
        )

        self.buyer_client = Client()
        self.seller_client = Client()
        self.delivery_client = Client()

        self.buyer_client.login(username='buyer_test', password='test123')
        self.seller_client.login(username='seller_test', password='test123')
        self.delivery_client.login(username='delivery_test', password='test123')

    def test_01_dashboards_load(self):
        """اختبار تحميل لوحات التحكم"""
        r1 = self.buyer_client.get(reverse('accounts:buyer_dashboard'))
        r2 = self.seller_client.get(reverse('accounts:seller_dashboard'))
        r3 = self.delivery_client.get(reverse('accounts:delivery_dashboard'))
        self.assertEqual(r1.status_code, 200, "لوحة المشتري لا تعمل")
        self.assertEqual(r2.status_code, 200, "لوحة البائع لا تعمل")
        self.assertEqual(r3.status_code, 200, "لوحة التوصيل لا تعمل")
        print("  [PASS] Dashboards load OK")

    def test_02_create_transaction(self):
        """اختبار إنشاء صفقة"""
        self.seller_client.post(reverse('transactions:create'), {
            'product_name': 'هاتف تجريبي',
            'description': 'وصف تجريبي',
            'amount': '10000',
            'delivery_company': self.delivery.id,
        })
        self.assertEqual(Transaction.objects.count(), 1, "الصفقة لم تُنشأ")
        transaction = Transaction.objects.first()
        self.assertEqual(transaction.status, 'PENDING', "الحالة خاطئة")
        self.assertIsNotNone(transaction.code, "الكود لم يُولَّد")
        print(f"  [PASS] Transaction created with code: {transaction.code}")

    def test_03_join_transaction(self):
        """اختبار انضمام المشتري"""
        self.seller_client.post(reverse('transactions:create'), {
            'product_name': 'هاتف تجريبي',
            'description': 'وصف',
            'amount': '10000',
            'delivery_company': self.delivery.id,
        })
        transaction = Transaction.objects.first()
        self.buyer_client.post(reverse('transactions:join'), {
            'code': transaction.code
        })
        transaction.refresh_from_db()
        self.assertEqual(transaction.buyer, self.buyer, "المشتري لم ينضم")
        print("  [PASS] Buyer joined transaction")

    def test_04_fund_transaction(self):
        """اختبار تمويل الصفقة"""
        self.seller_client.post(reverse('transactions:create'), {
            'product_name': 'هاتف تجريبي',
            'description': 'وصف',
            'amount': '10000',
            'delivery_company': self.delivery.id,
        })
        transaction = Transaction.objects.first()
        transaction.buyer = self.buyer
        transaction.save()

        self.buyer_client.post(reverse('transactions:fund', args=[transaction.pk]))
        transaction.refresh_from_db()
        self.buyer.wallet.refresh_from_db()

        self.assertEqual(transaction.status, 'FUNDED', "الصفقة لم تُموَّل")
        self.assertEqual(
            self.buyer.wallet.frozen_balance,
            Decimal('10000'),
            "المبلغ لم يُجمَّد"
        )
        print("  [PASS] Transaction funded, 10000 frozen")

    def test_05_ship_transaction(self):
        """اختبار تأكيد الشحن"""
        self.seller_client.post(reverse('transactions:create'), {
            'product_name': 'هاتف تجريبي',
            'description': 'وصف',
            'amount': '10000',
            'delivery_company': self.delivery.id,
        })
        transaction = Transaction.objects.first()
        transaction.buyer = self.buyer
        transaction.status = 'FUNDED'
        transaction.save()

        self.seller_client.post(reverse('transactions:ship', args=[transaction.pk]))
        transaction.refresh_from_db()
        self.assertEqual(transaction.status, 'SHIPPED', "الشحن لم يُؤكَّد")
        print("  [PASS] Shipment confirmed")

    def test_06_confirm_delivery(self):
        """اختبار تأكيد الاستلام"""
        self.seller_client.post(reverse('transactions:create'), {
            'product_name': 'هاتف تجريبي',
            'description': 'وصف',
            'amount': '10000',
            'delivery_company': self.delivery.id,
        })
        transaction = Transaction.objects.first()
        transaction.buyer = self.buyer
        transaction.status = 'SHIPPED'
        transaction.save()

        self.buyer_client.post(reverse('transactions:confirm_delivery', args=[transaction.pk]))
        transaction.refresh_from_db()
        self.assertEqual(transaction.status, 'DELIVERED', "الاستلام لم يُؤكَّد")
        print("  [PASS] Delivery confirmed")

    def test_07_complete_and_commission(self):
        """اختبار تحرير الأموال والعمولة"""
        self.seller_client.post(reverse('transactions:create'), {
            'product_name': 'هاتف تجريبي',
            'description': 'وصف',
            'amount': '10000',
            'delivery_company': self.delivery.id,
        })
        transaction = Transaction.objects.first()
        transaction.buyer = self.buyer
        transaction.status = 'DELIVERED'
        transaction.save()

        self.buyer.wallet.frozen_balance = Decimal('10000')
        self.buyer.wallet.balance = Decimal('40000')
        self.buyer.wallet.save()

        seller_balance_before = self.seller.wallet.balance

        self.delivery_client.post(reverse('transactions:complete', args=[transaction.pk]))
        transaction.refresh_from_db()
        self.seller.wallet.refresh_from_db()
        self.buyer.wallet.refresh_from_db()

        # 10000 دج → 1.5% = 150 دج عمولة، البائع يستلم 9850 دج
        expected_commission = Decimal('150')
        expected_seller_receives = Decimal('9850')

        self.assertEqual(transaction.status, 'COMPLETED', "الصفقة لم تكتمل")
        self.assertEqual(
            self.seller.wallet.balance - seller_balance_before,
            expected_seller_receives,
            f"البائع لم يستلم الصحيح: توقعنا {expected_seller_receives}"
        )
        # رصيد المشتري يجب أن ينخفض (40000 - 10000 = 30000)
        self.assertEqual(
            self.buyer.wallet.balance,
            Decimal('30000'),
            f"رصيد المشتري خاطئ: توقعنا 30000 وجدنا {self.buyer.wallet.balance}"
        )
        self.assertEqual(self.buyer.wallet.frozen_balance, Decimal('0'), "frozen المشتري لم يُصفَّر")
        platform = PlatformWallet.get_instance()
        self.assertEqual(
            platform.balance,
            expected_commission,
            f"عمولة AmanPay خاطئة: توقعنا {expected_commission}"
        )
        print(f"  [PASS] Complete OK — buyer -10000 (30000) — seller +{expected_seller_receives} — commission {expected_commission}")

    def test_08_wallet_history(self):
        """اختبار سجل الرصيد"""
        response = self.buyer_client.get(reverse('transactions:wallet_history'))
        self.assertEqual(response.status_code, 200, "سجل الرصيد لا يعمل")
        print("  [PASS] Wallet history OK")

    def test_09_language_switch(self):
        """اختبار تبديل اللغة"""
        r_ar = self.buyer_client.get(reverse('accounts:buyer_dashboard'))
        self.assertEqual(r_ar.status_code, 200, "Arabic dashboard failed")
        r_fr = self.buyer_client.get('/fr/dashboard/buyer/')
        self.assertEqual(r_fr.status_code, 200, "French dashboard failed")
        print("  [PASS] Language switching OK")

    def test_10_commission_rates(self):
        """اختبار شرائح العمولة"""
        from accounts.models import calculate_commission
        c1 = calculate_commission(5000)
        self.assertEqual(c1['rate'], 2.0, "Tier 1 rate wrong")
        self.assertEqual(c1['commission'], 100.0, "Tier 1 commission wrong")

        c2 = calculate_commission(10000)
        self.assertEqual(c2['rate'], 1.5, "Tier 2 rate wrong")
        self.assertEqual(c2['commission'], 150.0, "Tier 2 commission wrong")

        c3 = calculate_commission(30000)
        self.assertEqual(c3['rate'], 1.0, "Tier 3 rate wrong")
        self.assertEqual(c3['commission'], 300.0, "Tier 3 commission wrong")
        print("  [PASS] Commission tiers correct")

    def test_11_withdraw_no_balance_inflation(self):
        """تحقق أن الانسحاب لا يُضاعف الرصيد"""
        self.seller_client.post(reverse('transactions:create'), {
            'product_name': 'منتج اختبار',
            'description': 'وصف',
            'amount': '10000',
            'delivery_company': self.delivery.id,
        })
        transaction = Transaction.objects.first()
        transaction.buyer = self.buyer
        transaction.status = 'FUNDED'
        transaction.save()

        self.buyer.wallet.frozen_balance = Decimal('10000')
        self.buyer.wallet.balance = Decimal('50000')
        self.buyer.wallet.save()
        balance_before = self.buyer.wallet.balance

        self.buyer_client.post(reverse('transactions:withdraw', args=[transaction.pk]))
        self.buyer.wallet.refresh_from_db()

        self.assertEqual(
            self.buyer.wallet.balance,
            balance_before,
            f"الانسحاب ضاعف الرصيد: قبل={balance_before} بعد={self.buyer.wallet.balance}"
        )
        self.assertEqual(self.buyer.wallet.frozen_balance, Decimal('0'), "frozen لم يُصفَّر")
        print(f"  [PASS] Withdraw correct — balance unchanged at {self.buyer.wallet.balance}")

    def test_12_insufficient_balance_blocked(self):
        """تحقق أن التمويل يُرفض عند نقص الرصيد"""
        self.seller_client.post(reverse('transactions:create'), {
            'product_name': 'منتج غالي',
            'description': 'وصف',
            'amount': '999999',
            'delivery_company': self.delivery.id,
        })
        transaction = Transaction.objects.first()
        transaction.buyer = self.buyer
        transaction.save()

        self.buyer_client.post(reverse('transactions:fund', args=[transaction.pk]))
        transaction.refresh_from_db()

        self.assertEqual(transaction.status, 'PENDING', "الصفقة مُوِّلت رغم نقص الرصيد!")
        self.buyer.wallet.refresh_from_db()
        self.assertEqual(self.buyer.wallet.frozen_balance, Decimal('0'), "frozen تغيّر رغم الرفض")
        print("  [PASS] Insufficient balance correctly blocked")

    def test_13_amount_below_min_rejected(self):
        """تحقق أن صفقة بمبلغ < 10,000 دج تُرفض من النموذج"""
        before = Transaction.objects.count()
        self.seller_client.post(reverse('transactions:create'), {
            'product_name': 'منتج صغير',
            'description': 'وصف',
            'amount': '9999',
            'delivery_company': self.delivery.id,
        })
        self.assertEqual(
            Transaction.objects.count(), before,
            "صفقة بمبلغ أقلّ من الحدّ الأدنى أُنشئت رغم الرفض المتوقّع"
        )
        print("  [PASS] Amount < 10,000 correctly rejected")

    def test_14_amount_above_max_rejected(self):
        """تحقق أن صفقة بمبلغ > 1,000,000 دج تُرفض من النموذج"""
        before = Transaction.objects.count()
        self.seller_client.post(reverse('transactions:create'), {
            'product_name': 'منتج باهظ',
            'description': 'وصف',
            'amount': '1000001',
            'delivery_company': self.delivery.id,
        })
        self.assertEqual(
            Transaction.objects.count(), before,
            "صفقة بمبلغ أكبر من الحدّ الأقصى أُنشئت رغم الرفض المتوقّع"
        )
        print("  [PASS] Amount > 1,000,000 correctly rejected")

    def test_15_amount_within_range_accepted(self):
        """تحقق أن صفقة بمبلغ 50,000 دج (داخل النطاق) تُقبل"""
        before = Transaction.objects.count()
        self.seller_client.post(reverse('transactions:create'), {
            'product_name': 'منتج عادي',
            'description': 'وصف',
            'amount': '50000',
            'delivery_company': self.delivery.id,
        })
        self.assertEqual(
            Transaction.objects.count(), before + 1,
            "صفقة بمبلغ صحيح ضمن النطاق لم تُنشأ"
        )
        latest = Transaction.objects.first()
        self.assertEqual(latest.amount, Decimal('50000.00'), "المبلغ المُسجَّل خاطئ")
        print("  [PASS] Amount 50,000 (within range) accepted")
