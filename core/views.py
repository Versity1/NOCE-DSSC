from django.shortcuts import render

# Public pages
def home(request):
    return render(request, 'home.html', {'active_page': 'home'})

def login_view(request):
    return render(request, 'account/login.html')

def buy_pin(request):
    return render(request, 'account/buy-pin.html', {'active_page': 'payments'})

# Student pages
def student_dashboard(request):
    context = {
        'user_role': 'student',
        'user_name': 'John Doe',
        'user_initials': 'JD',
        'active_page': 'dashboard',
        'student_name': 'John',
    }
    return render(request, 'account/student-dashboard.html', context)

def student_result(request):
    context = {
        'user_role': 'student',
        'user_name': 'John Doe',
        'user_initials': 'JD',
        'active_page': 'results',
        'breadcrumb_current': 'Results',
    }
    return render(request, 'account/student-result.html', context)

# Admin pages
def admin_dashboard(request):
    context = {
        'user_role': 'admin',
        'user_name': 'Mr. Adebayo',
        'user_initials': 'MA',
        'active_page': 'dashboard',
    }
    return render(request, 'custom_admin/admin-dashboard.html', context)

def manage_students(request):
    context = {
        'user_role': 'admin',
        'user_name': 'Mr. Adebayo',
        'user_initials': 'MA',
        'active_page': 'students',
        'breadcrumb_parent': 'Students',
        'breadcrumb_current': 'Directory',
    }
    return render(request, 'custom_admin/manage-students.html', context)

def enter_marks(request):
    context = {
        'user_role': 'teacher',
        'user_name': 'Mrs. Okonkwo',
        'user_initials': 'MO',
        'active_page': 'marks',
        'breadcrumb_parent': 'Academic',
        'breadcrumb_current': 'Enter Marks',
    }
    return render(request, 'custom_admin/enter-mark.html', context)

def fees_payments(request):
    context = {
        'user_role': 'admin',
        'user_name': 'Mr. Adebayo',
        'user_initials': 'MA',
        'active_page': 'fees',
        'breadcrumb_parent': 'Finance',
        'breadcrumb_current': 'Fees & Payments',
    }
    return render(request, 'custom_admin/fees-and-payments.html', context)

def attendance(request):
    context = {
        'user_role': 'teacher',
        'user_name': 'Mrs. Okonkwo',
        'user_initials': 'MO',
        'active_page': 'attendance',
        'breadcrumb_parent': 'Academic',
        'breadcrumb_current': 'Attendance',
    }
    return render(request, 'custom_admin/attendance-register.html', context)

def library(request):
    context = {
        'user_role': 'staff',
        'user_name': 'Mr. Chukwu',
        'user_initials': 'MC',
        'active_page': 'library',
        'breadcrumb_parent': 'Resources',
        'breadcrumb_current': 'Library',
    }
    return render(request, 'custom_admin/library-inventory-loan.html', context)

def transport(request):
    context = {
        'user_role': 'staff',
        'user_name': 'Mr. Ibrahim',
        'user_initials': 'MI',
        'active_page': 'transport',
        'breadcrumb_parent': 'Resources',
        'breadcrumb_current': 'Transport',
    }
    return render(request, 'custom_admin/transport-mgt.html', context)