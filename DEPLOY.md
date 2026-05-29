# نشر AmanPay على PythonAnywhere

دليل نشر مشروع **AmanPay** على PythonAnywhere.
الرابط النهائي: <https://amanpay.pythonanywhere.com>

---

## المتطلبات

- **Python 3.10+** (المشروع مُختبَر على Django 6.0.4).
- حساب **PythonAnywhere** (المستخدم: `amanpay`).
- اعتمادات المشروع في [`requirements.txt`](requirements.txt).

---

## متغيّرات البيئة المطلوبة

تُضبط في بيئة الإنتاج (ملف WSGI أو إعدادات الويب على PythonAnywhere). انظر [`.env.example`](.env.example).

| المتغيّر | الإنتاج | الوصف |
|---|---|---|
| `DJANGO_DEBUG` | `False` | يجب أن يكون `False` في الإنتاج (أي قيمة غير `True` = إنتاج). |
| `DJANGO_SECRET_KEY` | `<مفتاح عشوائي طويل>` | مفتاح سرّي للإنتاج — لا تستخدم القيمة الاحتياطية للتطوير. |
| `DATABASE_URL` | (اختياري) | الافتراضي `sqlite:///db.sqlite3`. |

توليد مفتاح سرّي:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

عند `DJANGO_DEBUG=False` تُفعَّل إعدادات الأمان تلقائياً (HSTS، كوكيز آمنة، `X-Frame-Options: DENY`، إلخ).

---

## أوامر الإعداد بعد كل نشر

من مجلد المشروع داخل الـ virtualenv:

```bash
# 1) تثبيت الاعتمادات
pip install -r requirements.txt

# 2) تطبيق الهجرات
python manage.py migrate

# 3) جمع الملفات الثابتة (WhiteNoise — تُخدَّم من staticfiles/)
python manage.py collectstatic --noinput

# 4) (اختياري) تهيئة بيانات تجريبية للعرض
python manage.py reset_demo
```

> ملاحظة: `compilemessages` (gettext) غير متوفّر على كل البيئات — تُجمَّع الترجمات الفرنسية عبر `polib`،
> وملفات `locale/fr/LC_MESSAGES/django.mo` مُولّدة بالفعل ضمن خطوات بناء الترجمة.

---

## إعداد PythonAnywhere (خطوات الويب)

> **سيُملأ لاحقاً.**

<!--
سيُكتب هنا لاحقاً:
- إنشاء/سحب الكود (git clone أو رفع)
- إنشاء virtualenv وربطه بـ Web app
- ضبط مسار الكود + Source/Working directory
- تعديل ملف WSGI (إضافة المسار + DJANGO_SETTINGS_MODULE=core.settings + متغيّرات البيئة)
- ربط Static files: URL=/static/  →  Directory=<project>/staticfiles
- Reload التطبيق
-->
