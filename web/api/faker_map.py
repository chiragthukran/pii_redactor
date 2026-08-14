"""
Keeps one fake value per real value, so if "Sarthak Malvadkar" shows up
50 times in the document, it becomes the same fake name every time
instead of a different random one each time - otherwise the redacted
doc would be impossible to read consistently and the mapping would look
like it was doing something wrong even if the individual redactions are
technically correct.

Uses the faker library to generate the replacement values so they look
like realistic data (matches what the assignment example showed - real
name replaced with a plausible fake name, not just "[REDACTED]").
"""

from faker import Faker

_fake = Faker()
Faker.seed(42)  # reproducible output between runs

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
    """for the README/manual review - lets us dump what got mapped to what"""
    return _maps
