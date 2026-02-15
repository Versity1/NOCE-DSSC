from core.models import Pin, StudentResult, CustomUser, Term

user = CustomUser.objects.filter(username='student1').first()
if not user:
    print("User student1 not found")
else:
    print(f"--- DATA FOR {user.username} ---")
    
    # Check PINs
    pins = Pin.objects.filter(student=user)
    print(f"Owned PINs: {pins.count()}")
    for p in pins:
        print(f"  - PIN: {p.code} | Term: {p.term.name} (ID: {p.term.id}) | Session: {p.academic_session.name}")
        
    # Check Results
    results = StudentResult.objects.filter(student=user)
    print(f"\nResults in DB: {results.count()}")
    # Group results by term
    from collections import defaultdict
    term_counts = defaultdict(int)
    for r in results:
        term_counts[r.term_id] += 1
    
    for term_id, count in term_counts.items():
        term = Term.objects.get(id=term_id)
        print(f"  - Term: {term.name} (ID: {term_id}) | Session: {term.academic_session.name} | Results: {count}")

print("--- END ---")
