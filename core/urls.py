from django.contrib import admin
from django.urls import path, include
from django.conf.urls.i18n import i18n_patterns
import accounts.views as accounts_views

urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),
    path('set-language/', accounts_views.set_language_view, name='set_language'),
]

urlpatterns += i18n_patterns(
    path('admin/', admin.site.urls),
    path('', include('accounts.urls')),
    path('transactions/', include('transactions.urls')),
    path('accounts/', include('django.contrib.auth.urls')),
    prefix_default_language=False,
)
