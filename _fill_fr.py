# -*- coding: utf-8 -*-
import polib

po_path = 'locale/fr/LC_MESSAGES/django.po'
mo_path = 'locale/fr/LC_MESSAGES/django.mo'

# الترجمات الفرنسية لكل النصوص الجديدة في landing
translations = {
    'وسيط مالي آمن للتجارة الإلكترونية':
        'Intermédiaire financier sécurisé pour le e-commerce',
    'لا تبِع ولا تشترِ عبر الإنترنت دون وسيط آمن':
        "Ne vendez ni n'achetez en ligne sans un intermédiaire sûr",
    'أمان باي وسيط مالي محايد يحمي البائع والمشتري في كل صفقة عبر الإنترنت.':
        'AmanPay est un intermédiaire financier neutre qui protège vendeurs et acheteurs dans chaque transaction en ligne.',
    'ابدأ الآن': 'Commencer maintenant',
    'كيف يعمل': 'Comment ça marche',
    'كيف يعمل أمان باي': 'Comment fonctionne AmanPay',
    'خمس خطوات بسيطة لإتمام صفقة آمنة':
        'Cinq étapes simples pour une transaction sécurisée',
    'اتفاق المشتري والبائع': 'Accord entre acheteur et vendeur',
    'يتفقان على الصفقة وتفاصيلها':
        'Ils conviennent de la transaction et de ses détails',
    'دفع آمن للوسيط': "Paiement sécurisé à l'intermédiaire",
    'المشتري يودع المبلغ في أمان باي': "L'acheteur dépose le montant chez AmanPay",
    'البائع يشحن المنتج': 'Le vendeur expédie le produit',
    'بعد تأكيد حجز المبلغ': 'Après confirmation du dépôt du montant',
    'المشتري يؤكد الاستلام': "L'acheteur confirme la réception",
    'بعد فحص المنتج': 'Après inspection du produit',
    'تحرير الأموال بأمان': 'Libération sécurisée des fonds',
    'المبلغ يُحوَّل للبائع': 'Le montant est transféré au vendeur',
    'لماذا أمان باي': 'Pourquoi AmanPay',
    'أمان مالي للطرفين': 'Sécurité financière pour les deux parties',
    'حماية الأموال حتى يكتمل التسليم بنجاح':
        "Protection des fonds jusqu'à livraison réussie",
    'حماية من الاحتيال': 'Protection contre la fraude',
    'لا أحد يستلم ماله إلا بعد إتمام الصفقة':
        "Personne ne reçoit l'argent avant la finalisation",
    'شفافية كاملة': 'Transparence totale',
    'كل خطوة موثّقة ومرئية لجميع الأطراف':
        'Chaque étape est documentée et visible pour toutes les parties',
    'عمولة منخفضة': 'Commission réduite',
    'ابتداءً من 1% فقط حسب حجم الصفقة':
        'À partir de 1% seulement selon le montant',
    'لمن أمان باي': "À qui s'adresse AmanPay",
    'التجار الإلكترونيون': 'Vendeurs en ligne',
    'متاجر إنستغرام وفيسبوك التي تبيع للمشترين عن بعد':
        'Boutiques Instagram et Facebook vendant à distance',
    'التجار التقليديون': 'Commerçants traditionnels',
    'أصحاب المحلات الذين بدؤوا البيع أونلاين':
        'Commerçants qui se lancent en ligne',
    'أصحاب الخدمات': 'Prestataires de services',
    'المستقلون والمصممون والمطورون وغيرهم':
        'Freelances, designers, développeurs et autres',
    'وسيط محايد': 'Intermédiaire neutre',
    'حماية مضمونة': 'Protection garantie',
    'معاملات آمنة': 'Transactions sécurisées',
    'ابدأ أول صفقة آمنة اليوم':
        'Commencez votre première transaction sécurisée aujourd\'hui',
    'وسيط مالي آمن للتجارة الإلكترونية في الجزائر':
        'Intermédiaire financier sécurisé pour le e-commerce en Algérie',
    'جامعة العربي بن مهيدي — أم البواقي':
        "Université Larbi Ben M'hidi — Oum El Bouaghi",
}

po = polib.pofile(po_path)
applied = 0
missing = []
for msgid, fr in translations.items():
    e = po.find(msgid)
    if e is None:
        missing.append(msgid)
        continue
    e.msgstr = fr
    if 'fuzzy' in e.flags:
        e.flags.remove('fuzzy')
    applied += 1

po.save(po_path)
po.save_as_mofile(mo_path)
print('applied:', applied, '/', len(translations))
if missing:
    print('MISSING from po:', len(missing))
    for m in missing[:5]:
        print('  -', m[:60])
