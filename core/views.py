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