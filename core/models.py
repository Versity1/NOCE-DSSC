from django.db import models
from django.contrib.auth.models import AbstractUser


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
    
    def __str__(self):
        return f"Staff Profile: {self.user.get_full_name()}"
