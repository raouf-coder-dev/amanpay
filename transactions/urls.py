from django.urls import path
from . import views

app_name = 'transactions'

urlpatterns = [
    path('create/',                              views.create_transaction,  name='create'),
    path('join/',                                views.join_transaction,    name='join'),
    path('<int:pk>/',                            views.transaction_detail,  name='detail'),
    path('<int:pk>/preview/',                    views.preview_transaction, name='preview'),
    path('<int:pk>/fund/',                       views.fund_transaction,    name='fund'),
    path('<int:pk>/withdraw/',                   views.withdraw_transaction, name='withdraw'),
    path('<int:pk>/ship/',                       views.ship_transaction,    name='ship'),
    path('<int:pk>/confirm-delivery/',           views.confirm_delivery,    name='confirm_delivery'),
    path('<int:pk>/complete/',                   views.complete_transaction, name='complete'),
    path('<int:pk>/dispute/',                    views.dispute_transaction, name='dispute'),
    path('<int:pk>/review/',                     views.review_transaction,  name='review'),
    path('wallet/history/',                      views.wallet_history,      name='wallet_history'),
]
