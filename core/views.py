from django.shortcuts import render, redirect, reverse
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
            subject = 'Password Reset Request - NOCEN DSSN'
            message = render_to_string('account/password_reset_email.html', {
                'user': user,
                'reset_url': reset_url,
            })
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'support@nocendssn.com',
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


def about_us(request):
    return render(request, 'about.html', {'active_page': 'about'})


def admissions_page(request):
    return render(request, 'admissions.html', {'active_page': 'admissions'})


def academics_page(request):
    return render(request, 'academics.html', {'active_page': 'academics'})


def contact_page(request):
    return render(request, 'contact.html', {'active_page': 'contact'})


def buy_pin(request):
    from .models import SchoolConfiguration, AcademicSession, Term, Pin
    
    config = SchoolConfiguration.load()
    current_session = AcademicSession.objects.filter(is_current=True).first()
    terms = Term.objects.filter(academic_session=current_session) if current_session else Term.objects.none()
    
    # Get last purchased pin if student is logged in
    last_pin = None
    user_role = None
    user_initials = 'U'
    if request.user.is_authenticated:
        user_role = request.user.role
        user_initials = ''.join([n[0].upper() for n in (request.user.get_full_name() or request.user.username).split()[:2]])
        if request.user.role == 'student':
            last_pin = Pin.objects.filter(student=request.user).order_by('-created_at').first()

    context = {
        'active_page': 'payments',
        'user_role': user_role,
        'user_initials': user_initials,
        'config': config,
        'sessions': AcademicSession.objects.all(),
        'terms': terms,
        'current_session': current_session,
        'last_pin': last_pin,
        'pin_price_formatted': f"{config.pin_price:,.2f}",
    }
    return render(request, 'account/buy-pin.html', context)


def payment_confirmation(request):
    """Display payment confirmation page with bank details and upload form."""
    from .models import SchoolConfiguration, AcademicSession, Term
    
    if request.method != 'POST':
        messages.error(request, "Please fill in the form to proceed.")
        return redirect('buy_pin_page')
    
    student_id = request.POST.get('student_id')
    session_id = request.POST.get('session_id')
    term_id = request.POST.get('term_id')
    
    if not all([student_id, session_id, term_id]):
        messages.error(request, "Please fill in all required fields.")
        return redirect('buy_pin_page')
    
    try:
        session = AcademicSession.objects.get(id=session_id)
        term = Term.objects.get(id=term_id)
        config = SchoolConfiguration.load()
        
        # Get user info for sidebar
        user_role = None
        user_initials = 'U'
        if request.user.is_authenticated:
            user_role = request.user.role
            user_initials = ''.join([n[0].upper() for n in (request.user.get_full_name() or request.user.username).split()[:2]])
        
        context = {
            'active_page': 'payments',
            'user_role': user_role,
            'user_initials': user_initials,
            'student_id': student_id,
            'session': session,
            'term': term,
            'config': config,
            'pin_price': f"{config.pin_price:,.2f}",
        }
        return render(request, 'account/payment_confirmation.html', context)
    except (AcademicSession.DoesNotExist, Term.DoesNotExist):
        messages.error(request, "Invalid session or term selected.")
        return redirect('buy_pin_page')


def submit_payment_proof(request):
    """Handle payment proof submission for manual payments."""
    from .models import Payment, Term, AcademicSession, CustomUser, SchoolConfiguration
    
    if request.method != 'POST':
        return redirect('buy_pin_page')
    
    student_id = request.POST.get('student_id')
    session_id = request.POST.get('session_id')
    term_id = request.POST.get('term_id')
    proof = request.FILES.get('proof')
    
    if not all([student_id, session_id, term_id, proof]):
        messages.error(request, "Please upload proof of payment.")
        return redirect('buy_pin_page')
    
    try:
        session = AcademicSession.objects.get(id=session_id)
        term = Term.objects.get(id=term_id)
        config = SchoolConfiguration.load()
        
        # Find or identify the student
        student = None
        if request.user.is_authenticated and request.user.role == 'student':
            student = request.user
        else:
            # Try to find student by admission number
            student = CustomUser.objects.filter(username=student_id, role='student').first()
        
        if not student:
            # Create payment even without linked student (admin will match later)
            pass
        
        # Create Payment record
        import uuid
        payment = Payment(
            student=student,
            amount=config.pin_price,
            method='manual',
            term=term,
            academic_session=session,
            status='pending',
            proof_of_payment=proof,
            reference=f"MAN-{uuid.uuid4().hex[:8].upper()}"
        )
        payment.save()
        
        messages.success(request, "Payment proof submitted successfully! Your PIN will be issued after admin approval.")
        return redirect('payment_pending')
        
    except Exception as e:
        messages.error(request, f"Error submitting payment: {str(e)}")
        return redirect('buy_pin_page')


# ============================================
# STUDENT PAGES
# ============================================

@login_required
def student_dashboard(request):
    from django.db.models import Avg, Count
    from .models import StudentResult, Attendance, Term, Pin, Payment
    
    user = request.user
    if user.role != 'student':
        messages.warning(request, "Access restricted to students.")
        return redirect('home')
        
    # Student Profile data
    profile = getattr(user, 'student_profile', None)
    student_class = profile.class_level if profile else "N/A"
    
    # 1. Attendance Stats
    attendance_qs = Attendance.objects.filter(student=user)
    total_days = attendance_qs.count()
    present_days = attendance_qs.filter(status='Present').count()
    attendance_rate = int((present_days / total_days) * 100) if total_days > 0 else 0
    
    # 2. Academic Stats (Current Session/Term ideally, currently global for simplicity or latest)
    # Let's get stats for the current session/term if available, or just all time
    # For dashboard, maybe an overall average is good
    results = StudentResult.objects.filter(student=user)
    avg_score = results.aggregate(Avg('total'))['total__avg'] or 0
    total_subjects = results.values('subject').distinct().count()
    
    # Position (Simple ranking based on average of totals - heavy query for production but fine for MVP)
    # For now, let's keep position static or "-" if too complex to calculate efficiently on every load
    position = "-" 
    
    # 3. Get all purchased PINs for this student
    pins = Pin.objects.filter(student=user).order_by('-created_at')
    
    # 4. Get pending payments
    pending_payments = Payment.objects.filter(student=user, status='pending').order_by('-created_at')

    context = {
        'user_role': user.role,
        'user_name': user.get_full_name() or user.username,
        'user_initials': ''.join([n[0].upper() for n in (user.get_full_name() or user.username).split()[:2]]),
        'active_page': 'dashboard',
        'student_name': user.first_name,
        
        'student_class': student_class,
        'current_term': "2nd Term", # Placeholder or fetch from Global Config
        'attendance_rate': attendance_rate,
        'avg_score': int(avg_score),
        'total_subjects': total_subjects,
        'position': position,
        
        # New: PINs and Payments
        'pins': pins,
        'pending_payments': pending_payments,
    }
    return render(request, 'account/student-dashboard.html', context)


@login_required
def student_result(request):
    """
    View for students to check their results.
    Requires a valid PIN for the selected term.
    """
    from .models import Term, Pin, StudentResult, ClassInfo, StudentProfile, AcademicSession
    from django.db.models import Sum, Avg, Count, F
    
    user = request.user
    if not user.role == 'student':
        messages.error(request, "Access denied. Student only.")
        return redirect('home')

    current_session = AcademicSession.objects.filter(is_current=True).first()
    terms = Term.objects.filter(academic_session=current_session) if current_session else Term.objects.none()
    
    selected_term_id = request.GET.get('term_id')
    manual_pin_code = request.GET.get('pin_code', '').strip()
    
    results = []
    stats = {}
    
    if selected_term_id:
        try:
            term = Term.objects.get(id=selected_term_id)
            
            # 1. Check if student already has a valid active PIN for this term
            # OR if they provided a valid manual PIN
            has_access = False
            
            # Check existing owned pins
            existing_pin = Pin.objects.filter(student=user, term=term, status='active').first()
            if existing_pin:
                has_access = True
            
            # If no existing pin, check valid manual pin entry
            if not has_access and manual_pin_code:
                # Find a pin with this code that is either unused (no student) or belongs to this student
                # Use flexible matching for formatted vs unformatted
                # If generated as XXXX-XXXX-XXXX, user might enter XXXXXXXXXXXX or vice versa
                # Let's clean the input and db value for comparison
                
                # Simple exact match for now based on improved format
                pin_candidate = Pin.objects.filter(code=manual_pin_code, term=term, status='active').first()
                
                if pin_candidate:
                    if pin_candidate.student and pin_candidate.student != user:
                        messages.error(request, "This PIN has already been used by another student.")
                    else:
                        # Valid PIN. If not assigned, assign to student
                        if not pin_candidate.student:
                            pin_candidate.student = user
                            pin_candidate.save()
                        has_access = True
                        messages.success(request, "PIN accepted!")
                else:
                     messages.error(request, "Invalid PIN code for this term.")

            if has_access:
                results = StudentResult.objects.filter(student=user, term=term)
                
                # Calculate stats
                total_score = results.aggregate(Sum('total'))['total__sum'] or 0
                count = results.count()
                average = round(total_score / count, 2) if count > 0 else 0
                
                # Determine grade
                if average >= 75: grade = 'A'
                elif average >= 60: grade = 'B'
                elif average >= 50: grade = 'C'
                elif average >= 40: grade = 'D'
                else: grade = 'F'
                
                # Determine class from results (use the first result's class)
                first_result = results.first()
                if first_result and first_result.student_class:
                     result_class_name = first_result.student_class.name
                     result_class_id = first_result.student_class.id
                else:
                     result_class_name = user.student_profile.class_level
                     # Try to find the ID if possible, else None (limitations of legacy data)
                     result_class_obj = ClassInfo.objects.filter(name=result_class_name).first()
                     result_class_id = result_class_obj.id if result_class_obj else None

                # Calculate Class Stats (Positions & Averages)
                # We need all results for this class and term to calculate stats
                class_results = StudentResult.objects.filter(
                    term=term, 
                    student_class__name=result_class_name
                ).select_related('student', 'subject')

                # 1. Subject Stats (Average & Position per subject)
                subject_stats = {}
                # Group by subject
                from collections import defaultdict
                subject_scores = defaultdict(list)
                
                for res in class_results:
                    subject_scores[res.subject_id].append(res.total)
                
                for res in results:
                    scores = subject_scores.get(res.subject_id, [])
                    scores.sort(reverse=True)
                    
                    # Position
                    try:
                        position = scores.index(res.total) + 1
                        # Handle ties (optional, simple ranking)
                        if 10 <= position % 100 <= 20: suffix = 'th'
                        else: suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(position % 10, 'th')
                        position_str = f"{position}{suffix}"
                    except ValueError:
                        position_str = "-"
                        
                    # Class Average
                    avg = round(sum(scores) / len(scores)) if scores else 0
                    
                    subject_stats[res.subject_id] = {
                        'position': position_str,
                        'average': avg,
                        'highest': scores[0] if scores else 0,
                        'lowest': scores[-1] if scores else 0
                    }

                # 2. Overall Class Stats
                # Group totals by student
                student_totals = defaultdict(int)
                for res in class_results:
                    student_totals[res.student_id] += res.total
                
                # Convert to list and sort
                sorted_totals = sorted(student_totals.values(), reverse=True)
                my_total = student_totals.get(user.id, 0)
                
                try:
                    overall_pos = sorted_totals.index(my_total) + 1
                    if 10 <= overall_pos % 100 <= 20: suffix = 'th'
                    else: suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(overall_pos % 10, 'th')
                    overall_position = f"{overall_pos}{suffix}"
                except ValueError:
                    overall_position = "-"
                
                class_size = len(student_totals)
                class_average_score = round(sum(sorted_totals) / class_size, 1) if class_size else 0

                stats = {
                    'total_score': total_score,
                    'average': average,
                    'count': count,
                    'grade': grade,
                    'position': overall_position,
                    'class_size': class_size,
                    'class_average': class_average_score
                }
            elif not manual_pin_code and not existing_pin:
                 messages.warning(request, "You need a valid PIN to view results for this term.")
                 # return redirect('buy_pin_page') # Optional: auto-redirect
                 
        except Term.DoesNotExist:
            messages.error(request, "Invalid term selected.")
            
    context = {
        'active_page': 'results',
        'user_role': user.role,
        'user_initials': ''.join([n[0].upper() for n in (user.get_full_name() or user.username).split()[:2]]),
        'terms': terms,
        'results': results,
        'subject_stats': locals().get('subject_stats', {}),
        'result_class': locals().get('result_class_name', user.student_profile.class_level if hasattr(user, 'student_profile') else ''),
        'selected_term_id': int(selected_term_id) if selected_term_id else None,
        'stats': stats,
        'student_profile': user.student_profile,
    }
    return render(request, 'account/student-result.html', context)


# ============================================
# ADMIN/STAFF PAGES
# ============================================

@login_required
def admin_dashboard(request):
    from .models import CustomUser, Payment, Pin, Attendance, FeePayment
    from django.db.models import Sum, Count
    from django.utils import timezone
    from datetime import timedelta
    
    user = request.user
    
    # Get real stats
    total_students = CustomUser.objects.filter(role='student').count()
    total_staff = CustomUser.objects.filter(role__in=['teacher', 'staff', 'admin']).count()
    
    # Attendance today
    today = timezone.now().date()
    today_attendance = Attendance.objects.filter(date=today)
    total_today = today_attendance.count()
    present_today = today_attendance.filter(status='Present').count()
    attendance_rate = round((present_today / total_today * 100) if total_today > 0 else 0)
    
    # Fees collected - from approved payments
    total_collected = Payment.objects.filter(status='approved').aggregate(total=Sum('amount'))['total'] or 0
    fee_payments = FeePayment.objects.filter(status='approved').aggregate(total=Sum('amount_paid'))['total'] or 0
    total_collected += float(fee_payments) if fee_payments else 0
    
    # Pending approvals
    pending_payments = Payment.objects.filter(status='pending').count()
    pending_fee_payments = FeePayment.objects.filter(status='pending').count()
    
    # Recent activity
    recent_payments = Payment.objects.filter(status='approved').order_by('-created_at')[:3]
    
    context = {
        'user_role': user.role,
        'user_name': user.get_full_name() or user.username,
        'user_initials': ''.join([n[0].upper() for n in (user.get_full_name() or user.username).split()[:2]]),
        'active_page': 'dashboard',
        'total_students': total_students,
        'total_staff': total_staff,
        'attendance_rate': attendance_rate,
        'total_collected': total_collected,
        'pending_payments': pending_payments + pending_fee_payments,
        'recent_payments': recent_payments,
    }
    return render(request, 'custom_admin/admin-dashboard.html', context)


@login_required
def manage_students(request):
    from django.core.paginator import Paginator
    from django.db.models import Q
    from .models import CustomUser, ClassInfo
    
    user = request.user
    
    # Base Query
    students_list = CustomUser.objects.filter(role='student').order_by('last_name')
    classes = ClassInfo.objects.all()
    
    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        students_list = students_list.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(student_profile__admission_number__icontains=search_query) |
            Q(student_profile__parent_name__icontains=search_query)
        )
    
    # Filters
    selected_class = request.GET.get('class_level')
    if selected_class:
        students_list = students_list.filter(student_profile__class_level=selected_class)
        
    # Pagination
    paginator = Paginator(students_list, 20) # 20 students per page
    page_number = request.GET.get('page')
    students = paginator.get_page(page_number)
    
    context = {
        'user_role': user.role,
        'user_name': user.get_full_name() or user.username,
        'user_initials': ''.join([n[0].upper() for n in (user.get_full_name() or user.username).split()[:2]]),
        'active_page': 'students',
        'breadcrumb_parent': 'Students',
        'breadcrumb_current': 'Directory',
        
        'students': students,
        'classes': classes,
        'search_query': search_query,
        'selected_class': selected_class,
    }
    return render(request, 'custom_admin/manage-students.html', context)


@login_required
def add_student(request):
    from .models import CustomUser, StudentProfile, ClassInfo
    
    if request.method == 'POST':
        try:
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            username = request.POST.get('username') or f"STD{CustomUser.objects.count() + 1000}"
            email = request.POST.get('email', '')
            class_level = request.POST.get('class_level')
            parent_name = request.POST.get('parent_name')
            parent_phone = request.POST.get('parent_phone')
            
            # Simple validation
            if not (first_name and last_name):
                 raise ValueError("First Name and Last Name are required.")
                 
            # Create User
            user = CustomUser.objects.create_user(
                username=username,
                email=email,
                password='password123', # Default password
                first_name=first_name,
                last_name=last_name,
                role='student'
            )
            
            # Create Profile
            StudentProfile.objects.create(
                user=user,
                class_level=class_level,
                parent_name=parent_name,
                parent_phone=parent_phone
            )
            
            messages.success(request, f"Student {first_name} {last_name} added successfully.")
            return redirect('manage_students')
            
        except Exception as e:
            messages.error(request, f"Error adding student: {str(e)}")
            
    return redirect('manage_students')


@login_required
def edit_student(request, student_id):
    from .models import CustomUser
    
    try:
        student = CustomUser.objects.get(id=student_id, role='student')
        
        if request.method == 'POST':
            student.first_name = request.POST.get('first_name')
            student.last_name = request.POST.get('last_name')
            student.email = request.POST.get('email')
            student.save()
            
            profile = student.student_profile
            profile.class_level = request.POST.get('class_level')
            profile.parent_name = request.POST.get('parent_name')
            profile.parent_phone = request.POST.get('parent_phone')
            profile.save()
            
            messages.success(request, "Student details updated.")
            return redirect('manage_students')
            
    except CustomUser.DoesNotExist:
        messages.error(request, "Student not found.")
        
    return redirect('manage_students')


@login_required
def delete_student(request, student_id):
    from .models import CustomUser
    
    if request.method == 'POST':
        try:
            student = CustomUser.objects.get(id=student_id, role='student')
            student.delete()
            messages.success(request, "Student deleted successfully.")
        except CustomUser.DoesNotExist:
            messages.error(request, "Student not found.")
            
    return redirect('manage_students')


@login_required
def promote_students(request):
    from .models import CustomUser, ClassInfo
    
    if request.method == 'POST':
        try:
            current_class = request.POST.get('current_class')
            target_class = request.POST.get('target_class')
            
            if not (current_class and target_class):
                raise ValueError("Please select both current and target classes.")
                
            if current_class == target_class:
                 raise ValueError("Target class cannot be the same as current class.")
            
            # Update students
            updated_count = CustomUser.objects.filter(
                role='student', 
                student_profile__class_level=current_class
            ).update(
                # We can't update related fields directly in update() for some DBs/Django versions cleanly directly on OneToOne in bulk easily in one go for fields on related model efficiently without filtering on related model directly
                # However, for simplicity let's do it via the Profile model directly
            )
            
            # Correct approach for related model bulk update
            from .models import StudentProfile
            updated_count = StudentProfile.objects.filter(class_level=current_class).update(class_level=target_class)
            
            messages.success(request, f"Successfully promoted {updated_count} students from {current_class} to {target_class}.")
            
        except Exception as e:
            messages.error(request, f"Error promoting students: {str(e)}")
            
    return redirect('manage_students')


@login_required
def enter_marks(request):
    from .models import ClassInfo, Subject, Term, AcademicSession, StudentResult, CustomUser
    
    user = request.user
    
    # Fetch filter options
    classes = ClassInfo.objects.all()
    subjects = Subject.objects.all()
    
    # Get current session & terms
    current_session = AcademicSession.objects.filter(is_current=True).first()
    terms = Term.objects.filter(academic_session=current_session) if current_session else Term.objects.none()
    
    # Selected filters from GET request
    selected_class_id = request.GET.get('class_id')
    selected_subject_id = request.GET.get('subject_id')
    selected_term_id = request.GET.get('term_id')
    
    students = []
    existing_results_map = {}
    
    if selected_class_id and selected_subject_id and selected_term_id:
        # Fetch students in the selected class
        # Assuming we need to link students to classes later, currently using role='student'
        # For now, let's filter by student profile class_level matching the selected class name/level
        try:
             selected_class = ClassInfo.objects.get(id=selected_class_id)
             # Filter subjects assigned to this class
             subjects = selected_class.subjects.all()
             
             students = CustomUser.objects.filter(
                 role='student', 
                 student_profile__class_level=selected_class.level
             ).order_by('last_name')
             
             # Fetch existing results
             results = StudentResult.objects.filter(
                 student__in=students,
                 subject_id=selected_subject_id,
                 term_id=selected_term_id
             )
             existing_results_map = {res.student_id: res for res in results}
             
        except ClassInfo.DoesNotExist:
            messages.error(request, "Selected class not found.")
            
    # Combine student and result data for the template
    student_data = []
    for student in students:
        student_data.append({
            'student': student,
            'result': existing_results_map.get(student.id)
        })
    
    if request.method == 'POST':
        try:
            class_id = request.POST.get('class_id')
            subject_id = request.POST.get('subject_id')
            term_id = request.POST.get('term_id')
            
            if not (class_id and subject_id and term_id):
                 raise ValueError("Missing required filter data.")

            student_ids = request.POST.getlist('student_ids')
            
            for student_id in student_ids:
                ca1 = int(request.POST.get(f'ca1_{student_id}', 0) or 0)
                ca2 = int(request.POST.get(f'ca2_{student_id}', 0) or 0)
                ca3 = int(request.POST.get(f'ca3_{student_id}', 0) or 0)
                ca4 = int(request.POST.get(f'ca4_{student_id}', 0) or 0)
                exam = int(request.POST.get(f'exam_{student_id}', 0) or 0)
                
                # Update or Create Result
                StudentResult.objects.update_or_create(
                    student_id=student_id,
                    subject_id=subject_id,
                    term_id=term_id,
                    defaults={
                        'student_class_id': class_id,
                        'ca1': ca1,
                        'ca2': ca2,
                        'ca3': ca3,
                        'ca4': ca4,
                        'exam': exam,
                        'recorded_by': user
                    }
                )
            
            messages.success(request, "Marks saved successfully!")
            return redirect(f"{reverse('enter_marks')}?class_id={class_id}&subject_id={subject_id}&term_id={term_id}")
            
        except Exception as e:
            messages.error(request, f"Error saving marks: {str(e)}")
    
    
    context = {
        'user_role': user.role,
        'user_name': user.get_full_name() or user.username,
        'user_initials': ''.join([n[0].upper() for n in (user.get_full_name() or user.username).split()[:2]]),
        'active_page': 'marks',
        'breadcrumb_parent': 'Academic',
        'breadcrumb_current': 'Enter Marks',
        
        'classes': classes,
        'subjects': subjects,
        'terms': terms,
        'current_session': current_session,
        
        'selected_class_id': int(selected_class_id) if selected_class_id else None,
        'selected_subject_id': int(selected_subject_id) if selected_subject_id else None,
        'selected_term_id': int(selected_term_id) if selected_term_id else None,
        
        'student_data': student_data,
    }
    return render(request, 'custom_admin/enter-mark.html', context)


@login_required
def upload_marks_csv(request):
    import csv
    import io
    from .models import ClassInfo, Subject, Term, StudentResult, CustomUser
    
    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']
        
        # Check if it's a csv file
        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'Please upload a CSV file.')
            return redirect('enter_marks')
        
        # Get filter data from form
        class_id = request.POST.get('class_id')
        subject_id = request.POST.get('subject_id')
        term_id = request.POST.get('term_id')
        
        if not (class_id and subject_id and term_id):
            messages.error(request, 'Please select Class, Subject, and Term before uploading.')
            return redirect('enter_marks')

        try:
            data_set = csv_file.read().decode('UTF-8')
            io_string = io.StringIO(data_set)
            next(io_string) # Skip header
            
            for column in csv.reader(io_string, delimiter=',', quotechar='"'):
                # Expected format: Username/AdmissionNo, CA1, CA2, CA3, CA4, Exam
                # Adjust index based on your CSV template
                if len(column) < 6:
                    continue
                    
                username = column[0].strip()
                ca1 = int(column[1] or 0)
                ca2 = int(column[2] or 0)
                ca3 = int(column[3] or 0)
                ca4 = int(column[4] or 0)
                exam = int(column[5] or 0) # Exam is now at index 5
                
                try:
                    student = CustomUser.objects.get(username=username, role='student')
                    
                    StudentResult.objects.update_or_create(
                        student=student,
                        subject_id=subject_id,
                        term_id=term_id,
                        defaults={
                            'student_class_id': class_id,
                            'ca1': ca1,
                            'ca2': ca2,
                            'ca3': ca3,
                            'ca4': ca4,
                            'exam': exam,
                            'recorded_by': request.user
                        }
                    )
                except CustomUser.DoesNotExist:
                    # Log error or skip
                    continue
                    
            messages.success(request, 'Marks uploaded successfully.')
            
        except Exception as e:
            messages.error(request, f'Error processing CSV: {str(e)}')
            
        return redirect(f"{reverse('enter_marks')}?class_id={class_id}&subject_id={subject_id}&term_id={term_id}")
    
    return redirect('enter_marks')


@login_required
def broadsheet(request):
    from .models import ClassInfo, Subject, Term, AcademicSession, StudentResult, CustomUser
    from django.db.models import Sum, Avg
    
    user = request.user
    classes = ClassInfo.objects.all()
    
    # Get current session & terms
    current_session = AcademicSession.objects.filter(is_current=True).first()
    terms = Term.objects.filter(academic_session=current_session) if current_session else Term.objects.none()
    
    selected_class_id = request.GET.get('class_id')
    selected_term_id = request.GET.get('term_id')
    
    broadsheet_data = []
    subjects = []
    
    if selected_class_id and selected_term_id:
        try:
            selected_class = ClassInfo.objects.get(id=selected_class_id)
            # Get valid subjects for this class level (or all for now)
            subjects = Subject.objects.all()
            
            # Get students
            students = CustomUser.objects.filter(
                 role='student', 
                 student_profile__class_level=selected_class.level
             ).order_by('last_name')
             
            # Build broadsheet data
            for student in students:
                results = StudentResult.objects.filter(
                    student=student, 
                    term_id=selected_term_id,
                    student_class_id=selected_class_id
                )
                result_map = {res.subject_id: res for res in results}
                
                subject_scores = []
                total_score = 0
                subject_count = 0
                
                for subject in subjects:
                    if subject.id in result_map:
                        res = result_map[subject.id]
                        score = res.total
                        grade = res.grade
                        subject_scores.append({'score': score, 'grade': grade})
                        total_score += score
                        subject_count += 1
                    else:
                        subject_scores.append({'score': '-', 'grade': '-'})
                
                average = round(total_score / subject_count, 1) if subject_count > 0 else 0
                
                broadsheet_data.append({
                    'student': student,
                    'scores': subject_scores,
                    'total': total_score,
                    'average': average
                })
            
            # Sort by Average/Total for position
            broadsheet_data.sort(key=lambda x: x['total'], reverse=True)
            
            # Assign positions
            current_pos = 1
            for data in broadsheet_data:
                data['position'] = current_pos
                current_pos += 1
                
        except ClassInfo.DoesNotExist:
            messages.error(request, "Selected class not found.")

    context = {
        'user_role': user.role,
        'user_name': user.get_full_name() or user.username,
        'user_initials': ''.join([n[0].upper() for n in (user.get_full_name() or user.username).split()[:2]]),
        'active_page': 'broadsheet', 
        'breadcrumb_parent': 'Academic',
        'breadcrumb_current': 'Broadsheet',
        
        'classes': classes,
        'terms': terms,
        'subjects': subjects,
        'current_session': current_session,
        
        'selected_class_id': int(selected_class_id) if selected_class_id else None,
        'selected_term_id': int(selected_term_id) if selected_term_id else None,
        
        'broadsheet_data': broadsheet_data,
    }

    return render(request, 'custom_admin/broadsheet.html', context)


@login_required
def manage_subjects(request):
    from .models import ClassInfo, Subject
    
    user = request.user
    classes = ClassInfo.objects.all()
    subjects = Subject.objects.all()
    
    selected_class_id = request.GET.get('class_id')
    selected_class = None
    assigned_subject_ids = []
    
    if selected_class_id:
        try:
            selected_class = ClassInfo.objects.get(id=selected_class_id)
            assigned_subject_ids = list(selected_class.subjects.values_list('id', flat=True))
        except ClassInfo.DoesNotExist:
             messages.error(request, "Selected class not found.")
    
    if request.method == 'POST':
        try:
            class_id = request.POST.get('class_id')
            if not class_id:
                raise ValueError("No class selected.")
                
            selected_class = ClassInfo.objects.get(id=class_id)
            
            # Get list of selected subject IDs
            subject_ids = request.POST.getlist('subject_ids')
            
            # Update ManyToMany relationship
            selected_class.subjects.set(subject_ids)
            selected_class.save()
            
            messages.success(request, f"Subjects updated for {selected_class.name} successfully!")
            return redirect(f"{reverse('manage_subjects')}?class_id={class_id}")
            
        except Exception as e:
            messages.error(request, f"Error updating subjects: {str(e)}")
            
    context = {
        'user_role': user.role,
        'user_name': user.get_full_name() or user.username,
        'user_initials': ''.join([n[0].upper() for n in (user.get_full_name() or user.username).split()[:2]]),
        'active_page': 'manage_subjects',
        'breadcrumb_parent': 'Academic',
        'breadcrumb_current': 'Manage Subjects',
        
        'classes': classes,
        'subjects': subjects,
        'selected_class_id': int(selected_class_id) if selected_class_id else None,
        'assigned_subject_ids': assigned_subject_ids,
    }
    return render(request, 'custom_admin/manage_subjects.html', context)


@login_required
def fees_payments(request):
    from .models import FeePayment, CustomUser
    from django.db.models import Sum, Count
    
    user = request.user
    
    # Get stats
    total_collected = FeePayment.objects.filter(status='approved').aggregate(total=Sum('amount_paid'))['total'] or 0
    outstanding = FeePayment.objects.filter(status__in=['pending', 'declined']).aggregate(total=Sum('balance'))['total'] or 0
    fully_paid = FeePayment.objects.filter(status='approved', balance=0).values('student').distinct().count()
    defaulters = CustomUser.objects.filter(role='student').exclude(
        fee_payments__status='approved'
    ).count()
    
    # Recent payments
    recent_payments = FeePayment.objects.select_related('student', 'fee_structure', 'fee_structure__fee_type').order_by('-created_at')[:20]
    
    context = {
        'user_role': user.role,
        'user_name': user.get_full_name() or user.username,
        'user_initials': ''.join([n[0].upper() for n in (user.get_full_name() or user.username).split()[:2]]),
        'active_page': 'fees',
        'breadcrumb_parent': 'Finance',
        'breadcrumb_current': 'Fees & Payments',
        'total_collected': total_collected,
        'outstanding': outstanding,
        'fully_paid': fully_paid,
        'defaulters': defaulters,
        'recent_payments': recent_payments,
    }
    return render(request, 'custom_admin/fees-and-payments.html', context)


@login_required
def attendance(request):
    from datetime import date
    from .models import ClassInfo, CustomUser, Attendance
    
    user = request.user
    today = date.today()
    
    # Get filters
    class_filter = request.GET.get('class_name') # Changed from class_level
    date_filter = request.GET.get('date', str(today))
    
    classes = ClassInfo.objects.all()
    students = []
    attendance_records = {} # Map student_id to status
    
    stats = {
        'present': 0,
        'absent': 0,
        'late': 0,
        'rate': 0
    }
    
    selected_class_obj = None
    if class_filter:
        try:
             selected_class_obj = ClassInfo.objects.get(name=class_filter) # Filter by unique Name (JSS 1A)
             
             # Fetch students in that class. 
             # Since StudentProfile only has 'class_level' (e.g. JSS 1), we fetch all students in that Level.
             # Ideally we should match exact class but Profile doesn't support it yet.
             students = CustomUser.objects.filter(role='student', student_profile__class_level=selected_class_obj.level).order_by('last_name')
             
             # Fetch existing attendance for this specific ClassInfo object
             records = Attendance.objects.filter(class_info=selected_class_obj, date=date_filter)
             for record in records:
                 attendance_records[record.student.id] = {
                     'status': record.status, 
                     'remark': record.remark
                 }
                 
             # Compute stats
             total_marked = records.count()
             if total_marked > 0:
                 stats['present'] = records.filter(status='Present').count()
                 stats['absent'] = records.filter(status='Absent').count()
                 stats['late'] = records.filter(status='Late').count()
                 stats['rate'] = int((stats['present'] / total_marked) * 100)
                 
        except ClassInfo.DoesNotExist:
            pass

    context = {
        'user_role': user.role,
        'user_name': user.get_full_name() or user.username,
        'user_initials': ''.join([n[0].upper() for n in (user.get_full_name() or user.username).split()[:2]]),
        'active_page': 'attendance',
        'breadcrumb_parent': 'Academic',
        'breadcrumb_current': 'Attendance Register',
        
        'classes': classes,
        'students': students,
        'attendance_records': attendance_records,
        'selected_class': class_filter, # This is now the Name (e.g. JSS 1A)
        'selected_date': date_filter,
        'stats': stats,
    }
    return render(request, 'custom_admin/attendance-register.html', context)


@login_required
def save_attendance(request):
    from .models import ClassInfo, CustomUser, Attendance
    
    if request.method == 'POST':
        try:
            class_name = request.POST.get('class_name') # Changed from class_level
            date_str = request.POST.get('date')
            
            if not class_name:
                messages.error(request, "Class not specified.")
                return redirect('attendance')

            selected_class_obj = ClassInfo.objects.get(name=class_name)
            # Fetch same students as GET view
            students = CustomUser.objects.filter(role='student', student_profile__class_level=selected_class_obj.level)
            
            for student in students:
                status_key = f"status_{student.id}"
                remark_key = f"remark_{student.id}"
                
                status = request.POST.get(status_key)
                remark = request.POST.get(remark_key, '')
                
                if status:
                    Attendance.objects.update_or_create(
                        student=student,
                        date=date_str,
                        defaults={
                            'class_info': selected_class_obj,
                            'status': status,
                            'remark': remark,
                            'marked_by': request.user
                        }
                    )
            
            messages.success(request, "Attendance saved successfully.")
            return redirect(f"{reverse('attendance')}?class_name={class_name}&date={date_str}")
            
        except Exception as e:
            messages.error(request, f"Error saving attendance: {str(e)}")
            
    return redirect('attendance')


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


# ============================================
# PAYMENT & PIN VIEWS
# ============================================

@login_required
def buy_pin_page(request):
    """View to show payment options for buying a pin."""
    from .models import AcademicSession, Term, Pin, SchoolConfiguration
    
    user = request.user
    if not user.is_student:
        messages.error(request, "Only students can purchase pins.")
        return redirect('home')
        
    current_session = AcademicSession.objects.filter(is_current=True).first()
    terms = Term.objects.filter(academic_session=current_session) if current_session else Term.objects.none()
    
    # Get user's existing pins
    pins = Pin.objects.filter(student=user).order_by('-created_at')
    
    # Get configuration
    config = SchoolConfiguration.load()
    
    context = {
        'user_role': user.role,
        'user_name': user.get_full_name() or user.username,
        'user_initials': ''.join([n[0].upper() for n in (user.get_full_name() or user.username).split()[:2]]),
        'active_page': 'payments',
        'terms': terms,
        'pins': pins,
        'price': config.pin_price,
        'config': config,
        'paystack_public_key': settings.PAYSTACK_PUBLIC_KEY if hasattr(settings, 'PAYSTACK_PUBLIC_KEY') else '',
    }
    return render(request, 'account/buy_pin.html', context)


@login_required
def manage_configuration(request):
    """Admin view to manage school configuration."""
    from .models import SchoolConfiguration
    
    user = request.user
    if not user.is_admin_user:
        messages.error(request, "Access denied.")
        return redirect('home')
        
    config = SchoolConfiguration.load()
    
    if request.method == 'POST':
        try:
            config.pin_price = request.POST.get('pin_price')
            config.bank_name = request.POST.get('bank_name')
            config.account_number = request.POST.get('account_number')
            config.account_name = request.POST.get('account_name')
            config.save()
            
            messages.success(request, "Settings updated successfully.")
        except Exception as e:
            messages.error(request, f"Error updating settings: {str(e)}")
            
        return redirect('manage_configuration')
        
    context = {
        'user_role': user.role,
        'user_name': user.get_full_name(),
        'active_page': 'settings',
        'config': config,
    }
    return render(request, 'custom_admin/school_settings.html', context)


@login_required
def initiate_payment(request):
    """Handle payment initiation (Manual or Paystack intent)."""
    from .models import Payment, Term, AcademicSession
    import uuid

    if request.method == 'POST':
        user = request.user
        amount = request.POST.get('amount')
        method = request.POST.get('method')
        term_id = request.POST.get('term_id')
        
        try:
            term = Term.objects.get(id=term_id)
            session = term.academic_session
            
            # Create Payment Record
            payment = Payment(
                student=user,
                amount=amount,
                method=method,
                term=term,
                academic_session=session,
                status='pending'
            )
            
            if method == 'manual':
                proof = request.FILES.get('proof')
                if not proof:
                    messages.error(request, "Please upload proof of payment.")
                    return redirect('buy_pin_page')
                payment.proof_of_payment = proof
                payment.save()
                messages.success(request, "Proof of payment submitted successfully! Your PIN will be issued once approved.")
                return redirect('payment_pending')
                
            elif method == 'paystack':
                # Generate reference
                ref = request.POST.get('reference') or str(uuid.uuid4()).replace('-', '')[:12].upper()
                payment.reference = ref 
                payment.save()
                
                # Initialize Paystack Transaction (Standard Flow)
                import requests
                headers = {
                    "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
                    "Content-Type": "application/json",
                }
                # Ensure amount is in kobo
                amount_kobo = int(float(amount) * 100)
                
                data = {
                    "email": user.email,
                    "amount": amount_kobo,
                    "reference": payment.reference,
                    "callback_url": request.build_absolute_uri(reverse('verify_payment')),
                }
                
                try:
                    response = requests.post('https://api.paystack.co/transaction/initialize', json=data, headers=headers)
                    
                    if response.status_code == 200:
                        res_data = response.json()
                        return redirect(res_data['data']['authorization_url'])
                    else:
                         messages.error(request, "Error initializing Paystack payment.")
                         return redirect('buy_pin_page')
                except Exception as ex:
                    messages.error(request, f"Connection error: {str(ex)}")
                    return redirect('buy_pin_page')

        except Exception as e:
            messages.error(request, f"Error initiating payment: {str(e)}")
            
    return redirect('buy_pin_page')


@login_required
def payment_success(request, pin_id):
    """Page to display the successfully purchased PIN."""
    from .models import Pin
    try:
        pin = Pin.objects.get(id=pin_id, student=request.user)
    except Pin.DoesNotExist:
        messages.error(request, "PIN not found.")
        return redirect('student_dashboard')
        
    context = {
        'pin': pin,
        'user_name': request.user.get_full_name() or request.user.username,
        'user_role': request.user.role,
        'user_initials': ''.join([n[0].upper() for n in (request.user.get_full_name() or request.user.username).split()[:2]]),
        'active_page': 'payments',
    }
    return render(request, 'account/payment-success.html', context)


@login_required
def verify_payment(request):
    """Verify Paystack payment callback."""
    from .models import Payment, Pin
    import requests
    
    reference = request.GET.get('reference') or request.GET.get('trxref')
    
    if not reference:
        messages.error(request, "No transaction reference provided.")
        return redirect('buy_pin_page')
        
    try:
        payment = Payment.objects.get(reference=reference)
        
        if payment.status == 'approved':
             messages.info(request, "Payment already processed.")
             return redirect('buy_pin_page')
             
        # Verify with Paystack API
        headers = {
            "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        }
        response = requests.get(f"https://api.paystack.co/transaction/verify/{reference}", headers=headers)
        
        if response.status_code == 200:
            res_data = response.json()
            if res_data['data']['status'] == 'success':
                # Approve Payment
                payment.status = 'approved'
                payment.paystack_ref = str(res_data['data']['id'])
                payment.save()
                
                # Check if pin already exists for this term/session just in case?
                # Prompt says: "this pin can only be used per term". 
                # Assuming one pin per term is enough.
                
                # Generate Pin
                pin = Pin.objects.create(
                    student=payment.student,
                    term=payment.term,
                    academic_session=payment.academic_session,
                    status='active'
                )
                
                messages.success(request, "Payment successful! Your pin has been generated.")
                return redirect('payment_success', pin_id=pin.id)
            else:
                payment.status = 'declined'
                payment.save()
                messages.error(request, "Payment verification failed.")
        else:
             messages.error(request, "Unable to verify payment with Paystack.")
             
    except Payment.DoesNotExist:
        messages.error(request, "Payment record not found.")
    except Exception as e:
        messages.error(request, f"Error verifying payment: {str(e)}")
        
    return redirect('buy_pin_page')


@login_required
def admin_payments(request):
    """Admin view to manage manual payments."""
    from .models import Payment
    
    user = request.user
    if not (user.is_admin_user or user.is_staff_member): # Allow staff/bursar
        return redirect('home')
        
    pending_payments = Payment.objects.filter(status='pending', method='manual').order_by('-created_at')
    
    context = {
        'user_role': user.role,
        'user_name': user.get_full_name() or user.username,
        'user_initials': ''.join([n[0].upper() for n in (user.get_full_name() or user.username).split()[:2]]),
        'active_page': 'payments',
        'breadcrumb_current': 'Payment Approvals',
        'pending_payments': pending_payments,
    }
    return render(request, 'admin/payment_approval.html', context)


@login_required
def approve_payment(request, payment_id):
    """Admin action to approve/decline payment."""
    from .models import Payment, Pin
    
    if request.method == 'POST':
        user = request.user
        if not (user.is_admin_user or user.is_staff_member):
             return redirect('home')
             
        action = request.POST.get('action')
        
        try:
            payment = Payment.objects.get(id=payment_id)
            
            if action == 'approve':
                payment.status = 'approved'
                payment.admin_note = f"Approved by {user.username}"
                payment.save()
                
                # Generate Pin
                Pin.objects.create(
                    student=payment.student,
                    term=payment.term,
                    academic_session=payment.academic_session,
                    status='active'
                )
                messages.success(request, f"Payment approved for {payment.student.username}. Pin generated.")
                
            elif action == 'decline':
                payment.status = 'declined'
                payment.admin_note = f"Declined by {user.username}"
                payment.save()
                messages.warning(request, f"Payment declined for {payment.student.username}.")
                
        except Payment.DoesNotExist:
            messages.error(request, "Payment not found.")
            
    return redirect('admin_payments')


@login_required
def payment_pending(request):
    """Show student their pending payment status."""
    from .models import Payment, Pin
    
    user = request.user
    if not user.is_student:
        return redirect('home')
    
    # Get student's most recent pending payment
    pending_payment = Payment.objects.filter(
        student=user,
        status='pending',
        method='manual'
    ).order_by('-created_at').first()
    
    # Check if any payment was recently approved (for redirect)
    recent_approved = Payment.objects.filter(
        student=user,
        status='approved'
    ).order_by('-updated_at').first()
    
    # If the most recent approved payment was updated in last 5 minutes, check for new PIN
    if recent_approved:
        from django.utils import timezone
        from datetime import timedelta
        if recent_approved.updated_at > timezone.now() - timedelta(minutes=5):
            # Find the PIN created for this payment
            pin = Pin.objects.filter(
                student=user,
                term=recent_approved.term,
                academic_session=recent_approved.academic_session
            ).order_by('-created_at').first()
            if pin:
                return redirect('payment_success', pin_id=pin.id)
    
    # If no pending payments, redirect to buy PIN page
    if not pending_payment:
        messages.info(request, "You have no pending payments.")
        return redirect('buy_pin_page')
    
    context = {
        'user_role': user.role,
        'user_name': user.get_full_name() or user.username,
        'user_initials': ''.join([n[0].upper() for n in (user.get_full_name() or user.username).split()[:2]]),
        'active_page': 'payments',
        'payment': pending_payment,
    }
    return render(request, 'account/payment-pending.html', context)


@login_required
def admin_generate_pin(request):
    """Admin view to generate PINs on behalf of students."""
    from .models import CustomUser, AcademicSession, Term, Pin, Payment, SchoolConfiguration
    from django.utils import timezone
    from datetime import timedelta
    
    user = request.user
    if not (user.is_admin_user or user.is_staff_member):
        messages.error(request, "Access denied.")
        return redirect('home')
    
    # Get current session and terms
    current_session = AcademicSession.objects.filter(is_current=True).first()
    terms = Term.objects.filter(academic_session=current_session) if current_session else Term.objects.none()
    sessions = AcademicSession.objects.all()
    
    # Get all students for search
    students = CustomUser.objects.filter(role='student').order_by('last_name', 'first_name')
    
    # Get configuration for price
    config = SchoolConfiguration.load()
    
    # Recently generated PINs by admin
    recent_pins = Pin.objects.filter(
        created_at__gte=timezone.now() - timedelta(days=7)
    ).order_by('-created_at')[:10]
    
    generated_pin = None
    
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        term_id = request.POST.get('term_id')
        
        try:
            student = CustomUser.objects.get(id=student_id, role='student')
            term = Term.objects.get(id=term_id)
            session = term.academic_session
            
            # Check if PIN already exists for this student/term
            existing_pin = Pin.objects.filter(student=student, term=term).first()
            if existing_pin:
                messages.warning(request, f"PIN already exists for {student.get_full_name()} for {term.name}. Code: {existing_pin.code}")
            else:
                # Create payment record (marked as admin_generated)
                payment = Payment.objects.create(
                    student=student,
                    amount=config.pin_price,
                    method='manual',
                    term=term,
                    academic_session=session,
                    status='approved',
                    admin_note=f"Generated by admin: {user.username}"
                )
                
                # Generate PIN
                pin = Pin.objects.create(
                    student=student,
                    term=term,
                    academic_session=session,
                    status='active'
                )
                
                generated_pin = pin
                messages.success(request, f"PIN generated successfully for {student.get_full_name()}!")
                
        except CustomUser.DoesNotExist:
            messages.error(request, "Student not found.")
        except Term.DoesNotExist:
            messages.error(request, "Term not found.")
        except Exception as e:
            messages.error(request, f"Error generating PIN: {str(e)}")
    
    context = {
        'user_role': user.role,
        'user_name': user.get_full_name() or user.username,
        'user_initials': ''.join([n[0].upper() for n in (user.get_full_name() or user.username).split()[:2]]),
        'active_page': 'pins',
        'breadcrumb_current': 'Generate PIN',
        'students': students,
        'terms': terms,
        'sessions': sessions,
        'current_session': current_session,
        'recent_pins': recent_pins,
        'generated_pin': generated_pin,
        'config': config,
    }
    return render(request, 'admin/admin_generate_pin.html', context)


@login_required
def admin_sales_report(request):
    """Admin view for detailed sales analytics and reporting."""
    from .models import Payment, Pin, AcademicSession, Term
    from django.db.models import Sum, Count, Q
    from django.utils import timezone
    from datetime import timedelta
    from django.db.models.functions import TruncMonth, TruncDate
    
    user = request.user
    if not (user.is_admin_user or user.is_staff_member):
        return redirect('home')
        
    # Time periods
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = today_start.replace(day=1)
    year_start = today_start.replace(month=1, day=1)
    
    # Base Querysets
    sales_qs = Payment.objects.filter(status='approved')
    pins_qs = Pin.objects.all()
    
    # 1. Headline Stats
    total_sales_all_time = sales_qs.aggregate(Sum('amount'))['amount__sum'] or 0
    total_sales_today = sales_qs.filter(created_at__gte=today_start).aggregate(Sum('amount'))['amount__sum'] or 0
    total_sales_month = sales_qs.filter(created_at__gte=month_start).aggregate(Sum('amount'))['amount__sum'] or 0
    total_sales_year = sales_qs.filter(created_at__gte=year_start).aggregate(Sum('amount'))['amount__sum'] or 0
    
    total_pins_issued = pins_qs.count()
    active_pins = pins_qs.filter(status='active').count()
    used_pins = pins_qs.filter(status='used').count()
    
    # 2. Payment Method Breakdown
    method_data = sales_qs.values('method').annotate(
        count=Count('id'),
        total_amount=Sum('amount')
    )
    
    # 3. Term-wise Breakdown
    term_sales = sales_qs.values('term__name', 'academic_session__name').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-academic_session__name', 'term__name')
    
    # 4. Trend Data (Last 6 Months)
    six_months_ago = now - timedelta(days=180)
    monthly_trends = sales_qs.filter(created_at__gte=six_months_ago)\
        .annotate(month=TruncMonth('created_at'))\
        .values('month')\
        .annotate(total=Sum('amount'))\
        .order_by('month')
        
    # 5. Recent Transactions (with search/filter)
    search_q = request.GET.get('q', '')
    recent_sales = sales_qs
    if search_q:
        recent_sales = recent_sales.filter(
            Q(student__username__icontains=search_q) |
            Q(student__first_name__icontains=search_q) |
            Q(student__last_name__icontains=search_q) |
            Q(reference__icontains=search_q)
        )
    
    recent_sales = recent_sales.order_by('-created_at')[:50]
    
    context = {
        'user_role': user.role,
        'user_name': user.get_full_name() or user.username,
        'user_initials': ''.join([n[0].upper() for n in (user.get_full_name() or user.username).split()[:2]]),
        'active_page': 'sales',
        'breadcrumb_current': 'Sales Analytics',
        
        'stats': {
            'today': total_sales_today,
            'month': total_sales_month,
            'year': total_sales_year,
            'all_time': total_sales_all_time,
            'pins_issued': total_pins_issued,
            'active_pins': active_pins,
            'used_pins': used_pins,
        },
        'method_data': method_data,
        'term_sales': term_sales,
        'monthly_trends': monthly_trends,
        'sales': recent_sales,
        'search_q': search_q,
    }
    return render(request, 'admin/sales_report.html', context)


@login_required
def export_sales_csv(request):
    """Export sales data as CSV."""
    import csv
    from django.http import HttpResponse
    from .models import Payment
    
    user = request.user
    if not (user.is_admin_user or user.is_staff_member):
        messages.error(request, "Access denied.")
        return redirect('home')
    
    # Create the HttpResponse object with CSV header
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="sales_report.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Date', 'Student Name', 'Username', 'Amount', 'Method', 'Reference', 'Term', 'Session', 'Status'])
    
    # Get all approved payments
    payments = Payment.objects.filter(status='approved').order_by('-created_at')
    
    for payment in payments:
        writer.writerow([
            payment.created_at.strftime('%Y-%m-%d %H:%M'),
            payment.student.get_full_name(),
            payment.student.username,
            payment.amount,
            payment.method,
            payment.reference,
            payment.term.name if payment.term else '',
            payment.academic_session.name if payment.academic_session else '',
            payment.status,
        ])
    
    return response


# ============================================
# FEE MANAGEMENT VIEWS
# ============================================

@login_required
def manage_fee_types(request):
    """Manage fee types (add/view/delete)."""
    from .models import FeeType
    
    user = request.user
    if not (user.is_admin_user or user.is_staff_member):
        messages.error(request, "Access denied.")
        return redirect('home')
    
    fee_types = FeeType.objects.all()
    
    context = {
        'user_role': user.role,
        'user_name': user.get_full_name() or user.username,
        'user_initials': ''.join([n[0].upper() for n in (user.get_full_name() or user.username).split()[:2]]),
        'active_page': 'fee_types',
        'fee_types': fee_types,
    }
    return render(request, 'admin/fee_types.html', context)


@login_required
def add_fee_type(request):
    """Add a new fee type."""
    from .models import FeeType
    
    user = request.user
    if not (user.is_admin_user or user.is_staff_member):
        return redirect('home')
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        is_recurring = request.POST.get('is_recurring') == 'on'
        
        if name:
            FeeType.objects.create(
                name=name,
                description=description,
                is_recurring=is_recurring
            )
            messages.success(request, f"Fee type '{name}' created successfully.")
        else:
            messages.error(request, "Fee type name is required.")
    
    return redirect('manage_fee_types')


@login_required
def delete_fee_type(request, fee_type_id):
    """Delete a fee type."""
    from .models import FeeType
    
    user = request.user
    if not user.is_admin_user:
        return redirect('home')
    
    try:
        fee_type = FeeType.objects.get(id=fee_type_id)
        name = fee_type.name
        fee_type.delete()
        messages.success(request, f"Fee type '{name}' deleted.")
    except FeeType.DoesNotExist:
        messages.error(request, "Fee type not found.")
    
    return redirect('manage_fee_types')


@login_required
def manage_fee_structures(request):
    """Manage fee structures (amounts per class/term)."""
    from .models import FeeStructure, FeeType, Term, AcademicSession, ClassInfo
    
    user = request.user
    if not (user.is_admin_user or user.is_staff_member):
        return redirect('home')
    
    current_session = AcademicSession.objects.filter(is_current=True).first()
    terms = Term.objects.filter(academic_session=current_session) if current_session else Term.objects.none()
    
    selected_term_id = request.GET.get('term_id')
    structures = FeeStructure.objects.all()
    
    if selected_term_id:
        structures = structures.filter(term_id=selected_term_id)
    elif current_session:
        structures = structures.filter(term__academic_session=current_session)
    
    context = {
        'user_role': user.role,
        'user_name': user.get_full_name() or user.username,
        'user_initials': ''.join([n[0].upper() for n in (user.get_full_name() or user.username).split()[:2]]),
        'active_page': 'fee_structures',
        'structures': structures,
        'fee_types': FeeType.objects.filter(is_active=True),
        'terms': terms,
        'class_levels': ClassInfo.LEVEL_CHOICES,
        'selected_term_id': int(selected_term_id) if selected_term_id else None,
    }
    return render(request, 'admin/fee_structures.html', context)


@login_required
def add_fee_structure(request):
    """Add a new fee structure."""
    from .models import FeeStructure, FeeType, Term
    from decimal import Decimal
    
    user = request.user
    if not (user.is_admin_user or user.is_staff_member):
        return redirect('home')
    
    if request.method == 'POST':
        fee_type_id = request.POST.get('fee_type_id')
        term_id = request.POST.get('term_id')
        class_level = request.POST.get('class_level')
        amount = request.POST.get('amount')
        due_date = request.POST.get('due_date') or None
        
        try:
            fee_type = FeeType.objects.get(id=fee_type_id)
            term = Term.objects.get(id=term_id)
            
            FeeStructure.objects.update_or_create(
                fee_type=fee_type,
                term=term,
                class_level=class_level,
                defaults={
                    'amount': Decimal(amount),
                    'due_date': due_date
                }
            )
            messages.success(request, f"Fee structure for {fee_type.name} - {class_level} saved.")
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
    
    return redirect('manage_fee_structures')


@login_required
def manage_fee_payments(request):
    """View and manage student fee payments."""
    from .models import FeePayment, Term, AcademicSession
    from django.db.models import Q
    from django.utils import timezone
    
    user = request.user
    if not (user.is_admin_user or user.is_staff_member):
        return redirect('home')
    
    current_session = AcademicSession.objects.filter(is_current=True).first()
    terms = Term.objects.filter(academic_session=current_session) if current_session else Term.objects.none()
    
    # Filters
    status_filter = request.GET.get('status', '')
    term_filter = request.GET.get('term_id', '')
    search_q = request.GET.get('q', '')
    
    payments = FeePayment.objects.select_related('student', 'fee_structure', 'fee_structure__fee_type', 'fee_structure__term')
    
    if status_filter:
        payments = payments.filter(status=status_filter)
    if term_filter:
        payments = payments.filter(fee_structure__term_id=term_filter)
    if search_q:
        payments = payments.filter(
            Q(student__username__icontains=search_q) |
            Q(student__first_name__icontains=search_q) |
            Q(student__last_name__icontains=search_q) |
            Q(reference__icontains=search_q)
        )
    
    payments = payments.order_by('-created_at')[:100]
    
    # Stats
    pending_count = FeePayment.objects.filter(status='pending').count()
    approved_today = FeePayment.objects.filter(
        status='approved',
        updated_at__date=timezone.now().date()
    ).count()
    
    context = {
        'user_role': user.role,
        'user_name': user.get_full_name() or user.username,
        'user_initials': ''.join([n[0].upper() for n in (user.get_full_name() or user.username).split()[:2]]),
        'active_page': 'fee_payments',
        'payments': payments,
        'terms': terms,
        'pending_count': pending_count,
        'approved_today': approved_today,
        'status_filter': status_filter,
        'term_filter': term_filter,
        'search_q': search_q,
    }
    return render(request, 'admin/fee_payments.html', context)


@login_required
def approve_fee_payment(request, payment_id):
    """Approve or decline a fee payment."""
    from .models import FeePayment
    
    user = request.user
    if not (user.is_admin_user or user.is_staff_member):
        return redirect('home')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        admin_note = request.POST.get('admin_note', '')
        
        try:
            payment = FeePayment.objects.get(id=payment_id)
            
            if action == 'approve':
                payment.status = 'approved'
                payment.admin_note = f"Approved by {user.username}. {admin_note}"
                payment.save()
                messages.success(request, f"Payment approved for {payment.student.get_full_name()}.")
            elif action == 'decline':
                payment.status = 'declined'
                payment.admin_note = f"Declined by {user.username}. {admin_note}"
                payment.save()
                messages.warning(request, f"Payment declined for {payment.student.get_full_name()}.")
        except FeePayment.DoesNotExist:
            messages.error(request, "Payment not found.")
    
    return redirect('manage_fee_payments')

