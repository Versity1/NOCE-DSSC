from core.models import Pin, Term, CustomUser, StudentResult, AcademicSession
from django.db.models import Q

print("--- DIAGNOSTIC REPORT ---")

# 1. Current Session
current_session = AcademicSession.objects.filter(is_current=True).first()
print(f"Current Session: {current_session.name if current_session else 'NONE'} (ID: {current_session.id if current_session else '-'})")

# 2. Latest 3 Sessions
print("\nLatest Sessions:")
for s in AcademicSession.objects.order_by('-id')[:3]:
    print(f"  - {s.name} (ID: {s.id}) [Current: {s.is_current}]")

# 3. Latest 3 Terms created
print("\nLatest Terms:")
for t in Term.objects.order_by('-id')[:3]:
    print(f"  - {t.name} (ID: {t.id}) Session: {t.academic_session.name}")

# 4. Latest 5 PINs created
print("\nLatest PINs Created:")
for p in Pin.objects.order_by('-created_at')[:5]:
    try:
        student_name = p.student.username if p.student else "Unassigned"
    except:
        student_name = "Error"
    print(f"  - [{p.code}] Status: {p.status} | Term: {p.term.name} ({p.term.academic_session.name}) | Student: {student_name}")

# 5. Latest 5 Results Added
print("\nLatest Results Added:")
for r in StudentResult.objects.order_by('-id')[:5]:
    print(f"  - Student: {r.student.username if r.student else 'None'} | Subject: {r.subject.name} | Term: {r.term.name} ({r.term.academic_session.name}) | Score: {r.total}")

print("--- END REPORT ---")
