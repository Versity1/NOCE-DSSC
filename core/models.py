from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils import timezone
import uuid
import random

# Role choices for user groups
ROLE_CHOICES = [
    ('student', 'Student'),
    ('teacher', 'Teacher'),
    ('staff', 'Staff'),
    ('admin', 'Admin'),
]


class CustomUser(AbstractUser):
    """
    Custom User model with role-based authentication.
    Extends Django's AbstractUser to add role functionality.
    """
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='student',
        help_text='User role determines access level and dashboard redirect'
    )
    phone = models.CharField(max_length=20, blank=True, null=True)
    
    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
    
    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"
    
    @property
    def is_student(self):
        return self.role == 'student'
    
    @property
    def is_teacher(self):
        return self.role == 'teacher'
    
    @property
    def is_staff_member(self):
        return self.role == 'staff'
    
    @property
    def is_admin_user(self):
        return self.role == 'admin'
    
    def get_dashboard_url(self):
        """Returns the appropriate dashboard URL based on user role."""
        from django.urls import reverse
        dashboard_map = {
            'admin': 'admin_dashboard',
            'teacher': 'admin_dashboard',
            'staff': 'admin_dashboard',
            'student': 'student_dashboard',
        }
        return reverse(dashboard_map.get(self.role, 'home'))


# Optional: Role-specific profile models for extended data
class StudentProfile(models.Model):
    """Extended profile for students."""
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='student_profile',
        limit_choices_to={'role': 'student'}
    )
    admission_number = models.CharField(max_length=50, unique=True, blank=True, null=True)
    class_level = models.CharField(max_length=50, blank=True)
    
    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
    ]
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    house = models.CharField(max_length=50, blank=True, help_text="e.g. Red House")
    
    parent_name = models.CharField(max_length=100, blank=True)
    parent_phone = models.CharField(max_length=20, blank=True)
    
    def __str__(self):
        return f"Student Profile: {self.user.get_full_name()}"


class TeacherProfile(models.Model):
    """Extended profile for teachers."""
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='teacher_profile',
        limit_choices_to={'role': 'teacher'}
    )
    employee_id = models.CharField(max_length=50, unique=True, blank=True, null=True)
    department = models.CharField(max_length=100, blank=True)
    subjects = models.CharField(max_length=255, blank=True, help_text='Comma-separated list of subjects')
    qualification = models.CharField(max_length=200, blank=True, help_text='e.g. B.Ed, M.Sc')
    
    def __str__(self):
        return f"Teacher Profile: {self.user.get_full_name()}"


class StaffProfile(models.Model):
    """Extended profile for non-teaching staff."""
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='staff_profile',
        limit_choices_to={'role': 'staff'}
    )
    employee_id = models.CharField(max_length=50, unique=True, blank=True, null=True)
    department = models.CharField(max_length=100, blank=True)
    position = models.CharField(max_length=100, blank=True)
    qualification = models.CharField(max_length=200, blank=True, help_text='e.g. OND, HND, B.Sc')
    
    def __str__(self):
        return f"Staff Profile: {self.user.get_full_name()}"


# ============================================
# ACADEMICS MODELS
# ============================================

class AcademicSession(models.Model):
    """Manages academic sessions (e.g., 2025/2026)."""
    name = models.CharField(max_length=20, unique=True, help_text="e.g. 2025/2026")
    is_current = models.BooleanField(default=False)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.is_current:
            # Set all other sessions to False
            AcademicSession.objects.exclude(id=self.id).update(is_current=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Term(models.Model):
    """Manages terms within a session (First, Second, Third)."""
    TERM_CHOICES = [
        ('First', 'First Term'),
        ('Second', 'Second Term'),
        ('Third', 'Third Term'),
    ]
    name = models.CharField(max_length=20, choices=TERM_CHOICES)
    academic_session = models.ForeignKey(AcademicSession, on_delete=models.CASCADE, related_name='terms')
    is_current = models.BooleanField(default=False)

    class Meta:
        unique_together = ['name', 'academic_session']

    def save(self, *args, **kwargs):
        if self.is_current:
            # Set all other terms to False
            Term.objects.exclude(id=self.id).update(is_current=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} - {self.academic_session.name}"


class ClassInfo(models.Model):
    """Manages classes (e.g., JSS 1, SS 1, etc.)."""
    LEVEL_CHOICES = [
        ('JSS 1', 'JSS 1'),
        ('JSS 2', 'JSS 2'),
        ('JSS 3', 'JSS 3'),
        ('SS 1', 'SS 1'),
        ('SS 2', 'SS 2'),
        ('SS 3', 'SS 3'),
    ]
    name = models.CharField(max_length=50, unique=True, help_text="e.g. JSS 1A")
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES)
    subjects = models.ManyToManyField('Subject', related_name='classes', blank=True)
    form_teacher = models.OneToOneField(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='form_class',
        limit_choices_to={'role': 'teacher'},
        help_text='Teacher assigned as form teacher for this class'
    )
    
    class Meta:
        verbose_name_plural = "Classes"
        ordering = ['name']

    def __str__(self):
        return self.name


class Subject(models.Model):
    """Manages subjects (e.g., Mathematics, English)."""
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, blank=True, null=True, unique=True)
    is_elective = models.BooleanField(default=False)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class SubjectAssignment(models.Model):
    """Assigns a teacher to a subject, optionally for specific classes."""
    teacher = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='subject_assignments',
        limit_choices_to={'role': 'teacher'}
    )
    subject = models.ForeignKey('Subject', on_delete=models.CASCADE, related_name='assignments')
    class_info = models.ForeignKey(
        'ClassInfo',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='subject_assignments',
        help_text='Specific class for this assignment (optional)'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['teacher', 'subject', 'class_info']
        ordering = ['teacher__last_name', 'subject__name']

    def __str__(self):
        cls = f" ({self.class_info.name})" if self.class_info else ""
        return f"{self.teacher.get_full_name()} → {self.subject.name}{cls}"


class StudentResult(models.Model):
    """Stores student results for a specific subject, term, and session."""
    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE, limit_choices_to={'role': 'student'}, related_name='results')
    student_class = models.ForeignKey(ClassInfo, on_delete=models.SET_NULL, null=True, related_name='results')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='results')
    term = models.ForeignKey(Term, on_delete=models.CASCADE, related_name='results')
    
    # Marks Breakdown (4 CAs + Exam)
    ca1 = models.IntegerField(default=0, help_text="Max 10")
    ca2 = models.IntegerField(default=0, help_text="Max 10")
    ca3 = models.IntegerField(default=0, help_text="Max 10")
    ca4 = models.IntegerField(default=0, help_text="Max 10")
    exam = models.IntegerField(default=0, help_text="Max 60")
    
    total = models.IntegerField(default=0, editable=False, help_text="Max 100")
    grade = models.CharField(max_length=2, blank=True, editable=False)
    remark = models.CharField(max_length=20, blank=True)
    
    recorded_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='recorded_results')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['student', 'subject', 'term']

    def save(self, *args, **kwargs):
        # Validate limits
        self.ca1 = min(max(self.ca1, 0), 10)
        self.ca2 = min(max(self.ca2, 0), 10)
        self.ca3 = min(max(self.ca3, 0), 10)
        self.ca4 = min(max(self.ca4, 0), 10)
        self.exam = min(max(self.exam, 0), 60)
        
        # Calculate Total
        self.total = self.ca1 + self.ca2 + self.ca3 + self.ca4 + self.exam
        
        # Calculate Grade using updated scale (A, C, P, F)
        if self.total >= 70:
            self.grade = 'A'
            self.remark = 'Excellent'
        elif self.total >= 55:
            self.grade = 'C'
            self.remark = 'Credit'
        elif self.total >= 40:
            self.grade = 'P'
            self.remark = 'Pass'
        else:
            self.grade = 'F'
            self.remark = 'Fail'
            
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.student} - {self.subject} ({self.term})"


class Attendance(models.Model):
    """Tracks daily student attendance."""
    STATUS_CHOICES = [
        ('Present', 'Present'),
        ('Absent', 'Absent'),
        ('Late', 'Late'),
        ('Excused', 'Excused'),
    ]
    
    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE, limit_choices_to={'role': 'student'}, related_name='attendance_records')
    class_info = models.ForeignKey(ClassInfo, on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Present')
    remark = models.CharField(max_length=200, blank=True)
    
    marked_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='marked_attendance')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['student', 'date']
        ordering = ['-date', 'student__last_name']

    def __str__(self):
        return f"{self.student} - {self.date} ({self.status})"

class Pin(models.Model):
    """Result checker pin for students."""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('used', 'Used'),
    ]
    code = models.CharField(max_length=20, unique=True, editable=False)
    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='pins', limit_choices_to={'role': 'student'})
    term = models.ForeignKey(Term, on_delete=models.CASCADE)
    academic_session = models.ForeignKey(AcademicSession, on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    usage_count = models.IntegerField(default=0, help_text="Number of times this pin has been used")
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.code:
             # Generate a 12 digit pin formatted as XXXX-XXXX-XXXX
             raw_pin = ''.join([str(random.randint(0, 9)) for _ in range(12)])
             self.code = f"{raw_pin[:4]}-{raw_pin[4:8]}-{raw_pin[8:]}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Pin: {self.code} ({self.student})"


class Payment(models.Model):
    """Payment records for pins."""
    METHOD_CHOICES = [
        ('paystack', 'Paystack'),
        ('manual', 'Manual Deposit'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('declined', 'Declined'),
    ]
    
    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='payments', limit_choices_to={'role': 'student'})
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reference = models.CharField(max_length=100, unique=True)
    paystack_ref = models.CharField(max_length=100, blank=True, null=True)
    method = models.CharField(max_length=10, choices=METHOD_CHOICES)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    proof_of_payment = models.ImageField(upload_to='payment_proofs/', blank=True, null=True)
    term = models.ForeignKey(Term, on_delete=models.SET_NULL, null=True)    
    academic_session = models.ForeignKey(AcademicSession, on_delete=models.SET_NULL, null=True)
    admin_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.reference:
            # Generate a unique reference
            self.reference = str(uuid.uuid4()).replace('-', '')[:12].upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.student} - {self.amount} ({self.status})"


# ============================================
# CONFIGURATION MODEL
# ============================================

class SchoolConfiguration(models.Model):
    """Stores global school configuration settings."""
    pin_price = models.DecimalField(max_digits=10, decimal_places=2, default=2000.00)
    bank_name = models.CharField(max_length=100, default='First Bank')
    account_number = models.CharField(max_length=20, default='1234567890')
    account_name = models.CharField(max_length=100, default='NOCEN DSSN')
    term_duration_weeks = models.IntegerField(default=12)
    
    class Meta:
        verbose_name = "School Configuration"
        verbose_name_plural = "School Configurations"

    def __str__(self):
        return "School Settings"

    def save(self, *args, **kwargs):
        # Singleton pattern: verify if there is only one instance
        if not self.pk and SchoolConfiguration.objects.exists():
            return
        return super(SchoolConfiguration, self).save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj


# ============================================
# FEES MODELS
# ============================================

class FeeType(models.Model):
    """Types of fees (School Fees, Exam Fee, Development Levy, etc.)."""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_recurring = models.BooleanField(default=True, help_text="Charged every term")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class FeeStructure(models.Model):
    """Fee amounts per class level and term."""
    fee_type = models.ForeignKey(FeeType, on_delete=models.CASCADE, related_name='structures')
    class_level = models.CharField(max_length=20, choices=ClassInfo.LEVEL_CHOICES)
    term = models.ForeignKey(Term, on_delete=models.CASCADE, related_name='fee_structures')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    due_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['fee_type', 'class_level', 'term']
        ordering = ['term', 'class_level', 'fee_type']

    def __str__(self):
        return f"{self.fee_type.name} - {self.class_level} ({self.term})"


class FeePayment(models.Model):
    """Student fee payment records."""
    METHOD_CHOICES = [
        ('paystack', 'Paystack'),
        ('manual', 'Manual Deposit'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('declined', 'Declined'),
    ]
    
    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='fee_payments', limit_choices_to={'role': 'student'})
    fee_structure = models.ForeignKey(FeeStructure, on_delete=models.CASCADE, related_name='payments')
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    amount_due = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0, editable=False)
    method = models.CharField(max_length=10, choices=METHOD_CHOICES)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    reference = models.CharField(max_length=100, unique=True)
    paystack_ref = models.CharField(max_length=100, blank=True, null=True)
    proof_of_payment = models.ImageField(upload_to='fee_proofs/', blank=True, null=True)
    admin_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = f"FEE-{str(uuid.uuid4()).replace('-', '')[:10].upper()}"
        if not self.amount_due:
            self.amount_due = self.fee_structure.amount
        self.balance = self.amount_due - self.amount_paid
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.student} - {self.fee_structure.fee_type.name} ({self.status})"

    class Meta:
        ordering = ['-created_at']

