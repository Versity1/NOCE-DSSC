from django.urls import path
from . import views

urlpatterns = [
    # Public pages
    path('', views.home, name='home'),
    path('buy-pin/', views.buy_pin, name='buy_pin'),
    
    # Authentication
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('password-reset/', views.password_reset_request, name='password_reset'),
    path('password-reset/confirm/<uidb64>/<token>/', views.password_reset_confirm, name='password_reset_confirm'),
    
    # Student pages
    path('student/dashboard/', views.student_dashboard, name='student_dashboard'),
    path('student/result/', views.student_result, name='student_result'),
    
    # Admin/Staff pages
    path('admin-portal/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-portal/students/', views.manage_students, name='manage_students'),
    path('admin-portal/students/add/', views.add_student, name='add_student'),
    path('admin-portal/students/edit/<int:student_id>/', views.edit_student, name='edit_student'),
    path('admin-portal/students/delete/<int:student_id>/', views.delete_student, name='delete_student'),
    path('admin-portal/students/promote/', views.promote_students, name='promote_students'),
    path('admin-portal/attendance/', views.attendance, name='attendance'),
    path('admin-portal/attendance/save/', views.save_attendance, name='save_attendance'),
    path('admin-portal/marks/', views.enter_marks, name='enter_marks'),
    path('admin-portal/marks/upload/', views.upload_marks_csv, name='upload_marks_csv'),
    path('manage-subjects/', views.manage_subjects, name='manage_subjects'),
    path('admin-portal/broadsheet/', views.broadsheet, name='broadsheet'),
    path('admin-portal/fees/', views.fees_payments, name='fees_payments'),
    path('admin-portal/attendance/', views.attendance, name='attendance'),
    path('admin-portal/library/', views.library, name='library'),
    path('admin-portal/transport/', views.transport, name='transport'),
    
    # Payments & Pins
    path('buy-pin/', views.buy_pin_page, name='buy_pin_page'),
    path('payment/initiate/', views.initiate_payment, name='initiate_payment'),
    path('payment/verify/', views.verify_payment, name='verify_payment'),
    path('admin-portal/payments/', views.admin_payments, name='admin_payments'),
    path('admin-portal/payments/approve/<int:payment_id>/', views.approve_payment, name='approve_payment'),
    path('admin-portal/sales-report/', views.admin_sales_report, name='admin_sales_report'),
    
    # Configuration
    path('admin-portal/settings/', views.manage_configuration, name='manage_configuration'),
]