import re

def clean_option_name(raw_text):
    if not raw_text:
        return ""
    # Remove rank prefixes like '1위', '2위'
    cleaned = re.sub(r'^\d+\s*위\s*', '', raw_text.strip())
    # Clean multiple spaces/newlines
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

test_texts = [
    "1위 \n\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\tSSD 512GB",
    "2위 \n\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\tSSD 1TB",
    "SSD 2TB",
    "RAM 12GB / 256GB"
]

for t in test_texts:
    print(f"Original: {repr(t)} -> Cleaned: {repr(clean_option_name(t))}")
