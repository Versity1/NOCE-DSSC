from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Public pages
    path('', views.home, name='home'),
    
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
    path('buy-pin/', views.buy_pin, name='buy_pin_page'),
    path('payment/confirmation/', views.payment_confirmation, name='payment_confirmation'),
    path('payment/submit-proof/', views.submit_payment_proof, name='submit_payment_proof'),
    path('payment/initiate/', views.initiate_payment, name='initiate_payment'),
    path('payment/verify/', views.verify_payment, name='verify_payment'),
    path('payment/pending/', views.payment_pending, name='payment_pending'),
    path('payment/success/<int:pin_id>/', views.payment_success, name='payment_success'),
    path('admin-portal/payments/', views.admin_payments, name='admin_payments'),
    path('admin-portal/payments/approve/<int:payment_id>/', views.approve_payment, name='approve_payment'),
    path('admin-portal/pins/generate/', views.admin_generate_pin, name='admin_generate_pin'),
    path('admin-portal/sales-report/', views.admin_sales_report, name='admin_sales_report'),
    path('admin-portal/sales-report/export/', views.export_sales_csv, name='export_sales_csv'),
    
    # Fee Management
    path('admin-portal/fee-types/', views.manage_fee_types, name='manage_fee_types'),
    path('admin-portal/fee-types/add/', views.add_fee_type, name='add_fee_type'),
    path('admin-portal/fee-types/delete/<int:fee_type_id>/', views.delete_fee_type, name='delete_fee_type'),
    path('admin-portal/fee-structures/', views.manage_fee_structures, name='manage_fee_structures'),
    path('admin-portal/fee-structures/add/', views.add_fee_structure, name='add_fee_structure'),
    path('admin-portal/fee-payments/', views.manage_fee_payments, name='manage_fee_payments'),
    path('admin-portal/fee-payments/approve/<int:payment_id>/', views.approve_fee_payment, name='approve_fee_payment'),
    
    # Configuration
    path('admin-portal/settings/', views.manage_configuration, name='manage_configuration'),
]
# media files
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)