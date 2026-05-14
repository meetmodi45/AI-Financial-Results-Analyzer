
import re
def clean_number(token):
    # Fixed regex to not strip dots
    token = re.sub(r'[₹$%,]|Rs\.?', '', token)
    token = token.strip('()')
    try:
        return float(token)
    except:
        return None

print(f"3,655.80 -> {clean_number('3,655.80')}")
print(f"Rs. 3,655.80 -> {clean_number('Rs. 3,655.80')}")
print(f"(1,234.56) -> {clean_number('(1,234.56)')}")
