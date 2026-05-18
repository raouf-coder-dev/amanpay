# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Commands

```bash
# Run development server
python manage.py runserver

# Database
python manage.py makemigrations
python manage.py migrate

# i18n workflow (always in this order)
python manage.py makemessages -l fr
# edit locale/fr/LC_MESSAGES/django.po
python -c "import polib; po=polib.pofile('locale/fr/LC_MESSAGES/django.po'); po.save_as_mofile('locale/fr/LC_MESSAGES/django.mo')"

# Sanity check after every change
python manage.py check
python manage.py makemigrations --check

# Create superuser
python manage.py createsuperuser
```

**Note:** GNU `compilemessages` is not available on this Windows machine — use the `polib` one-liner above instead.

## Environment

Requires a `.env` file (read by `python-decouple`):
```
SECRET_KEY=...
DEBUG=True
DATABASE_URL=sqlite:///db.sqlite3   # optional, defaults to sqlite
ALLOWED_HOSTS=127.0.0.1,localhost
```

## Architecture

### Custom User Model (`accounts.User`)

Single `User` model with a `role` field (`BUYER` / `SELLER` / `DELIVERY`). Each role has dedicated extra fields on the same model (store fields for sellers, company fields for delivery). A `Wallet` (OneToOne) is created for every user at registration with `balance=50000` DZD by default.

```
User ──OneToOne──► Wallet
                     │
                     └──FK──► WalletTransaction (audit log)
```

Role-specific registration uses three separate `ModelForm` subclasses (`BuyerRegisterForm`, `SellerRegisterForm`, `DeliveryRegisterForm`) selected at runtime in `register_view` via `session['register_role']`.

### Transaction Lifecycle

```
PENDING → FUNDED → SHIPPED → DELIVERED → COMPLETED
                                       ↘ DISPUTED
```

| Step | Who triggers | Wallet effect |
|---|---|---|
| `fund` | Buyer | `frozen_balance += amount` |
| `withdraw` | Buyer (FUNDED only) | `balance += amount`, `frozen_balance -= amount` |
| `ship` | Seller | none |
| `confirm_delivery` | Buyer | none |
| `complete` | Delivery company | buyer `frozen_balance -= amount`; seller `balance += amount` |
| `dispute` | Delivery company (on DELIVERED) | none |

Every wallet mutation logs a `WalletTransaction` record (types: CREDIT, DEBIT, FREEZE, UNFREEZE, RELEASE) with `balance_before` and `balance_after` snapshots via the `_log()` helper in `transactions/views.py`.

`Wallet.available_balance` is a `@property`: `balance - frozen_balance`.

### URL Structure

```
/                          accounts:landing
/login/                    accounts:login
/register/                 accounts:register
/dashboard/                accounts:dashboard  (redirects by role)
/dashboard/buyer/          accounts:buyer_dashboard
/dashboard/seller/         accounts:seller_dashboard
/dashboard/delivery/       accounts:delivery_dashboard
/settings/                 accounts:settings
/accounts/password_change/ (django.contrib.auth built-in)

/transactions/create/                   transactions:create
/transactions/join/                     transactions:join
/transactions/<pk>/                     transactions:detail
/transactions/<pk>/preview/             transactions:preview
/transactions/<pk>/fund/                transactions:fund
/transactions/<pk>/withdraw/            transactions:withdraw
/transactions/<pk>/ship/                transactions:ship
/transactions/<pk>/confirm-delivery/    transactions:confirm_delivery
/transactions/<pk>/complete/            transactions:complete
/transactions/<pk>/dispute/             transactions:dispute
/transactions/<pk>/review/              transactions:review
/transactions/wallet/history/           transactions:wallet_history
```

URL routing uses `i18n_patterns` with `prefix_default_language=False`, so Arabic is at `/` and French is at `/fr/`.

Language switching is via Django's built-in `/i18n/setlang/` endpoint (POST with `{% csrf_token %}`).

### Templates

All templates extend `templates/base.html`. There are no app-level template directories — everything is under the top-level `templates/` folder. `base.html` provides: Glass-card dark-mode design system, navbar with role-based home link, language switcher, avatar → settings link.

### i18n Rules

- Every visible string in HTML must be wrapped in `{% trans "" %}`.
- Every template must have `{% load i18n %}` at the top.
- French translations live in `locale/fr/LC_MESSAGES/django.po`.
- After editing `.po`: remove `#, fuzzy` flags from any entry before it will be active, then recompile with `polib`.
- After adding new strings to templates/views: run `makemessages`, add `msgstr` for all new entries, recompile.
