from django.urls import path
from . import views

urlpatterns = [
    # Employee views
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('', views.dashboard, name='dashboard'),
    path('clock/', views.clock_view, name='clock'),
    path('history/', views.history_view, name='history'),
    path('leave/', views.leave_view, name='leave'),
    path('profile/', views.profile_view, name='profile'),

    # Admin Panel views
    path('admin-panel/', views.admin_overview, name='admin_overview'),
    path('admin-panel/logs/', views.admin_logs, name='admin_logs'),
    path('admin-panel/leave/', views.admin_leave_approval, name='admin_leave'),
    path('admin-panel/users/', views.admin_users, name='admin_users'),
    path('admin-panel/reports/', views.admin_reports, name='admin_reports'),
]