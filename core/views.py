from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.forms import SetPasswordForm
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.conf import settings
from .models import CustomUser


# ============================================
# AUTHENTICATION VIEWS
# ============================================

def login_view(request):
    """Handle user login with role-based redirect."""
    # If already logged in, redirect to dashboard
    if request.user.is_authenticated:
        return redirect(request.user.get_dashboard_url())
    
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        
        # Try to find user by username or email
        user = None
        if '@' in username:
            try:
                user_obj = CustomUser.objects.get(email=username)
                user = authenticate(request, username=user_obj.username, password=password)
            except CustomUser.DoesNotExist:
                pass
        else:
            user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')
            
            # Check for next parameter (for redirects from protected pages)
            next_url = request.GET.get('next') or request.POST.get('next')
            if next_url:
                return redirect(next_url)
            
            # Role-based redirect
            return redirect(user.get_dashboard_url())
        else:
            messages.error(request, 'Invalid username/email or password. Please try again.')
    
    return render(request, 'account/login.html')


def logout_view(request):
    """Handle user logout."""
    if request.user.is_authenticated:
        logout(request)
        messages.info(request, 'You have been logged out successfully.')
    return redirect('login')


def password_reset_request(request):
    """Handle password reset request - send email with reset link."""
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        
        try:
            user = CustomUser.objects.get(email=email)
            # Generate token and uid
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            # Build reset URL
            reset_url = request.build_absolute_uri(
                f'/password-reset/confirm/{uid}/{token}/'
            )
            
            # Send email
            subject = 'Password Reset Request - NOCE DSSC'
            message = render_to_string('account/password_reset_email.html', {
                'user': user,
                'reset_url': reset_url,
            })
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@nocedss.edu.ng',
                [email],
                fail_silently=False,
            )
            
            messages.success(
                request, 
                'Password reset instructions have been sent to your email address.'
            )
            return redirect('login')
            
        except CustomUser.DoesNotExist:
            # Don't reveal whether email exists for security
            messages.success(
                request, 
                'If an account exists with that email, password reset instructions have been sent.'
            )
            return redirect('login')
    
    return render(request, 'account/password_reset.html')


def password_reset_confirm(request, uidb64, token):
    """Handle password reset confirmation - set new password."""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = CustomUser.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
        user = None
    
    # Verify token
    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            password1 = request.POST.get('new_password1', '')
            password2 = request.POST.get('new_password2', '')
            
            if password1 and password1 == password2:
                if len(password1) < 8:
                    messages.error(request, 'Password must be at least 8 characters long.')
                else:
                    user.set_password(password1)
                    user.save()
                    messages.success(
                        request, 
                        'Your password has been reset successfully. You can now login with your new password.'
                    )
                    return redirect('login')
            else:
                messages.error(request, 'Passwords do not match. Please try again.')
        
        return render(request, 'account/password_reset_confirm.html', {
            'valid_link': True,
            'user': user,
        })
    else:
        return render(request, 'account/password_reset_confirm.html', {
            'valid_link': False,
        })


# ============================================
# PUBLIC PAGES
# ============================================

def home(request):
    return render(request, 'home.html', {'active_page': 'home'})


def buy_pin(request):
    return render(request, 'account/buy-pin.html', {'active_page': 'payments'})


# ============================================
# STUDENT PAGES
# ============================================

@login_required
def student_dashboard(request):
    user = request.user
    context = {
        'user_role': user.role,
        'user_name': user.get_full_name() or user.username,
        'user_initials': ''.join([n[0].upper() for n in (user.get_full_name() or user.username).split()[:2]]),
        'active_page': 'dashboard',
        'student_name': user.first_name or user.username,
    }
    return render(request, 'account/student-dashboard.html', context)


@login_required
def student_result(request):
    user = request.user
    context = {
        'user_role': user.role,
        'user_name': user.get_full_name() or user.username,
        'user_initials': ''.join([n[0].upper() for n in (user.get_full_name() or user.username).split()[:2]]),
        'active_page': 'results',
        'breadcrumb_current': 'Results',
    }
    return render(request, 'account/student-result.html', context)


# ============================================
# ADMIN/STAFF PAGES
# ============================================

@login_required
def admin_dashboard(request):
    user = request.user
    context = {
        'user_role': user.role,
        'user_name': user.get_full_name() or user.username,
        'user_initials': ''.join([n[0].upper() for n in (user.get_full_name() or user.username).split()[:2]]),
        'active_page': 'dashboard',
    }
    return render(request, 'custom_admin/admin-dashboard.html', context)


@login_required
def manage_students(request):
    user = request.user
    context = {
        'user_role': user.role,
        'user_name': user.get_full_name() or user.username,
        'user_initials': ''.join([n[0].upper() for n in (user.get_full_name() or user.username).split()[:2]]),
        'active_page': 'students',
        'breadcrumb_parent': 'Students',
        'breadcrumb_current': 'Directory',
    }
    return render(request, 'custom_admin/manage-students.html', context)


@login_required
def enter_marks(request):
    user = request.user
    context = {
        'user_role': user.role,
        'user_name': user.get_full_name() or user.username,
        'user_initials': ''.join([n[0].upper() for n in (user.get_full_name() or user.username).split()[:2]]),
        'active_page': 'marks',
        'breadcrumb_parent': 'Academic',
        'breadcrumb_current': 'Enter Marks',
    }
    return render(request, 'custom_admin/enter-mark.html', context)


@login_required
def fees_payments(request):
    user = request.user
    context = {
        'user_role': user.role,
        'user_name': user.get_full_name() or user.username,
        'user_initials': ''.join([n[0].upper() for n in (user.get_full_name() or user.username).split()[:2]]),
        'active_page': 'fees',
        'breadcrumb_parent': 'Finance',
        'breadcrumb_current': 'Fees & Payments',
    }
    return render(request, 'custom_admin/fees-and-payments.html', context)


@login_required
def attendance(request):
    user = request.user
    context = {
        'user_role': user.role,
        'user_name': user.get_full_name() or user.username,
        'user_initials': ''.join([n[0].upper() for n in (user.get_full_name() or user.username).split()[:2]]),
        'active_page': 'attendance',
        'breadcrumb_parent': 'Academic',
        'breadcrumb_current': 'Attendance',
    }
    return render(request, 'custom_admin/attendance-register.html', context)


@login_required
def library(request):
    user = request.user
    context = {
        'user_role': user.role,
        'user_name': user.get_full_name() or user.username,
        'user_initials': ''.join([n[0].upper() for n in (user.get_full_name() or user.username).split()[:2]]),
        'active_page': 'library',
        'breadcrumb_parent': 'Resources',
        'breadcrumb_current': 'Library',
    }
    return render(request, 'custom_admin/library-inventory-loan.html', context)


@login_required
def transport(request):
    user = request.user
    context = {
        'user_role': user.role,
        'user_name': user.get_full_name() or user.username,
        'user_initials': ''.join([n[0].upper() for n in (user.get_full_name() or user.username).split()[:2]]),
        'active_page': 'transport',
        'breadcrumb_parent': 'Resources',
        'breadcrumb_current': 'Transport',
    }
    return render(request, 'custom_admin/transport-mgt.html', context)