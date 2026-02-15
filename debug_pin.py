from core.models import Pin, Term, CustomUser
from django.db.models import Q

target_pin = "1626-5769-3389"

print(f"--- DEBUGGING PIN: {target_pin} ---")

# 1. Search for the PIN
pins = Pin.objects.filter(
    Q(code__iexact=target_pin) | 
    Q(code__contains=target_pin)
)

if not pins.exists():
    print("RESULT: PIN NOT FOUND in database.")
    # List a few pins to see format
    print("Sample PINs:", list(Pin.objects.values_list('code', flat=True)[:5]))
else:
    for pin in pins:
        print(f"FOUND PIN: {pin.code}")
        print(f"  - ID: {pin.id}")
        print(f"  - Term: {pin.term.name} (ID: {pin.term.id})")
        print(f"  - Session: {pin.academic_session.name}")
        print(f"  - Status: {pin.status}")
        print(f"  - Assigned Student: {pin.student.username if pin.student else 'None'}")
        
        if pin.student:
            print(f"    - Student Name: {pin.student.get_full_name()}")

print("--- END DEBUG ---")
