"""
keeps one fake value for each real value. so if "Sarthak Malvadkar" comes
50 times in the document, it will get the same fake name every time
instead of getting a different random name each time.

otherwise the redacted document can become confusing and the mapping
can look wrong even if each replacement is technically correct.

using faker to generate fake values so they look like realistic data.
this also matches the assignment example where a real name is replaced
with a believable fake name instead of just "[REDACTED]".
"""

from faker import Faker

_fake = Faker()
Faker.seed(42)  # keeps same output every time we run the script

_maps = {
    "person": {},
    "company": {},
    "email": {},
    "phone": {},
    "address": {},
    "ip": {},
    "ssn": {},
    "credit_card": {},
    "dob": {},
}


def get_fake(category, real_value):
    key = real_value.strip()
    m = _maps[category]
    if key not in m:
        if category == "person":
            m[key] = _fake.name()
        elif category == "company":
            m[key] = _fake.company()
        elif category == "email":
            m[key] = _fake.email()
        elif category == "phone":
            m[key] = _fake.phone_number()
        elif category == "address":
            m[key] = _fake.address().replace("\n", ", ")
        elif category == "ip":
            m[key] = _fake.ipv4()
        elif category == "ssn":
            m[key] = _fake.ssn()
        elif category == "credit_card":
            m[key] = _fake.credit_card_number()
        elif category == "dob":
            m[key] = _fake.date(pattern="%d %B %Y")
    return m[key]


def get_all_mappings():
    """used for README/manual checking to see what was mapped to what"""
    return _maps