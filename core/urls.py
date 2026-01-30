from django.urls import path
from . import views

urlpatterns = [
    # Public pages
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('buy-pin/', views.buy_pin, name='buy_pin'),
    
    # Student pages
    path('student/dashboard/', views.student_dashboard, name='student_dashboard'),
    path('student/result/', views.student_result, name='student_result'),
    
    # Admin/Staff pages
    path('admin-portal/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-portal/students/', views.manage_students, name='manage_students'),
    path('admin-portal/marks/', views.enter_marks, name='enter_marks'),
    path('admin-portal/fees/', views.fees_payments, name='fees_payments'),
    path('admin-portal/attendance/', views.attendance, name='attendance'),
    path('admin-portal/library/', views.library, name='library'),
    path('admin-portal/transport/', views.transport, name='transport'),
]