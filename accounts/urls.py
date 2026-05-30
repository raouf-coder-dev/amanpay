from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('', views.landing_view, name='landing'),
    path('home/', views.home_redirect_view, name='home_redirect'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('dashboard/buyer/', views.buyer_dashboard_view, name='buyer_dashboard'),
    path('dashboard/seller/', views.seller_dashboard_view, name='seller_dashboard'),
    path('dashboard/delivery/', views.delivery_dashboard_view, name='delivery_dashboard'),
    path('settings/', views.settings_view, name='settings'),
    path('admin-dashboard/', views.admin_dashboard_view, name='admin_dashboard'),
    path('admin-dashboard/platform/', views.admin_platform_wallet, name='admin_platform_wallet'),
    path('admin-dashboard/disputes/', views.admin_disputes_view, name='admin_disputes'),
    path('admin-dashboard/disputes/<int:pk>/acknowledge/', views.admin_acknowledge_dispute_view, name='admin_acknowledge_dispute'),
    path('admin-dashboard/user/<int:user_id>/', views.admin_user_detail, name='admin_user_detail'),
]
