# Custom migration: Replace class_level (CharField) with assigned_class (ForeignKey)
# Step 1: Add assigned_class field
# Step 2: Migrate data from class_level text to assigned_class FK
# Step 3: Remove old class_level field

import django.db.models.deletion
from django.db import migrations, models


def migrate_class_level_to_assigned_class(apps, schema_editor):
    """
    Migrate existing class_level text values to assigned_class ForeignKey.
    Matching logic:
    1. Try exact match on ClassInfo.name (e.g. "JSS 1A")
    2. Fallback to ClassInfo.level match (e.g. "JSS 1" → first ClassInfo with that level)
    3. If no match, leave assigned_class as NULL
    """
    StudentProfile = apps.get_model('core', 'StudentProfile')
    ClassInfo = apps.get_model('core', 'ClassInfo')
    
    for profile in StudentProfile.objects.all():
        if not profile.class_level:
            continue
        
        class_level_text = profile.class_level.strip()
        
        # Try exact match on name first (e.g. "JSS 1A")
        class_obj = ClassInfo.objects.filter(name=class_level_text).first()
        
        if not class_obj:
            # Fallback: match on level (e.g. "JSS 1" → picks first ClassInfo with that level)
            class_obj = ClassInfo.objects.filter(level=class_level_text).first()
        
        if class_obj:
            profile.assigned_class = class_obj
            profile.save(update_fields=['assigned_class'])


def reverse_migration(apps, schema_editor):
    """Reverse: Copy assigned_class name back to class_level text field."""
    StudentProfile = apps.get_model('core', 'StudentProfile')
    
    for profile in StudentProfile.objects.select_related('assigned_class').all():
        if profile.assigned_class:
            profile.class_level = profile.assigned_class.level
            profile.save(update_fields=['class_level'])


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_classinfo_form_teacher_staffprofile_qualification_and_more'),
    ]

    operations = [
        # Step 1: Add new FK field (alongside the existing class_level)
        migrations.AddField(
            model_name='studentprofile',
            name='assigned_class',
            field=models.ForeignKey(
                blank=True,
                help_text='The specific class section this student belongs to (e.g. JSS 1A)',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='students',
                to='core.classinfo',
            ),
        ),
        # Step 2: Migrate data
        migrations.RunPython(
            migrate_class_level_to_assigned_class,
            reverse_migration,
        ),
        # Step 3: Remove old text field
        migrations.RemoveField(
            model_name='studentprofile',
            name='class_level',
        ),
    ]
