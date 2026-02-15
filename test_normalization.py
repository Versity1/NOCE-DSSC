import re

def clean_pin(pin):
    return re.sub(r'[^a-zA-Z0-9]', '', pin).upper()

test_cases = [
    "1234-5678-9012",
    "1234  5678  9012",
    "1234.5678.9012",
    " 1234-5678-9012 ",
    "123456789012",
    "abcd-efgh-ijkl"
]

for tc in test_cases:
    cleaned = clean_pin(tc)
    print(f"'{tc}' -> '{cleaned}' (Len: {len(cleaned)})")
