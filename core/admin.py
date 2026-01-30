from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, StudentProfile, TeacherProfile, StaffProfile


class CustomUserAdmin(UserAdmin):
    """Custom admin for the CustomUser model."""
    model = CustomUser
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_staff', 'is_active')
    list_filter = ('role', 'is_staff', 'is_active')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('username',)
    
    fieldsets = UserAdmin.fieldsets + (
        ('Role & Profile', {
            'fields': ('role', 'phone'),
        }),
    )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Role & Profile', {
            'fields': ('role', 'phone', 'email', 'first_name', 'last_name'),
        }),
    )


class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'admission_number', 'class_level')
    search_fields = ('user__username', 'user__first_name', 'admission_number')
    list_filter = ('class_level',)


class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'employee_id', 'department')
    search_fields = ('user__username', 'user__first_name', 'employee_id')
    list_filter = ('department',)


class StaffProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'employee_id', 'department', 'position')
    search_fields = ('user__username', 'user__first_name', 'employee_id')
    list_filter = ('department', 'position')


admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(StudentProfile, StudentProfileAdmin)
admin.site.register(TeacherProfile, TeacherProfileAdmin)
admin.site.register(StaffProfile, StaffProfileAdmin)

# Academics Models Registration
from .models import AcademicSession, Term, ClassInfo, Subject, StudentResult

@admin.register(AcademicSession)
class AcademicSessionAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_current', 'start_date', 'end_date')
    list_filter = ('is_current',)

@admin.register(Term)
class TermAdmin(admin.ModelAdmin):
    list_display = ('name', 'academic_session', 'is_current')
    list_filter = ('academic_session', 'is_current')

@admin.register(ClassInfo)
class ClassInfoAdmin(admin.ModelAdmin):
    list_display = ('name', 'level')
    list_filter = ('level',)

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_elective')
    search_fields = ('name', 'code')

@admin.register(StudentResult)
class StudentResultAdmin(admin.ModelAdmin):
    list_display = ('student', 'subject', 'student_class', 'term', 'total', 'grade')
    list_filter = ('student_class', 'subject', 'term', 'grade')
    search_fields = ('student__username', 'student__first_name', 'student__last_name')
