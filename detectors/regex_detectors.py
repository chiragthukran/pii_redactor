"""
regex based detectors.

these are used for PII which follow some fixed pattern, so regex works
better here and is also more reliable than using ML/NER for these things.
NER is used separately in ner_detectors.py for stuff like names and
address where there is no fixed pattern.

each function return list of (start, end, matched_text), so caller can
take that part from paragraph and replace it.
"""

import re


# --- Email -------------------------------------------------------------
EMAIL_RE = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)

def find_emails(text):
    return [(m.start(), m.end(), m.group()) for m in EMAIL_RE.finditer(text)]


# --- Phone numbers -------------------------------------------------------
# this document is indian, so phone numbers mostly look like
# "+91 20 4505 3237" or "+91 9876543210". sometimes there are dashes also.
# kept regex a little loose so different spacing formats can be matched,
# then checking digit count so page numbers dont get picked up.
PHONE_RE = re.compile(
    r"(\+?\d{1,3}[\s-]?)?(\(?\d{2,4}\)?[\s-]?){2,4}\d{3,4}"
)

def find_phones(text):
    results = []
    for m in PHONE_RE.finditer(text):
        digits = re.sub(r"\D", "", m.group())
        # normal phone number with or without country code should have
        # 10-13 digits. smaller numbers are mostly page/section numbers
        # and bigger ones can be CIN or registration numbers.
        if 10 <= len(digits) <= 13:
            results.append((m.start(), m.end(), m.group()))
    return results


# --- IP address ----------------------------------------------------------
IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")

def find_ips(text):
    results = []
    for m in IP_RE.finditer(text):
        octets = m.group().split(".")
        if all(0 <= int(o) <= 255 for o in octets):
            results.append((m.start(), m.end(), m.group()))
    return results


# --- SSN (US format, kept for completeness per assignment spec) ----------
SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")

def find_ssns(text):
    return [(m.start(), m.end(), m.group()) for m in SSN_RE.finditer(text)]


# --- Credit card numbers --------------------------------------------------
CC_RE = re.compile(r"\b(?:\d[ -]?){13,16}\b")

def _luhn_ok(number_str):
    """luhn checksum. used to remove false positives from random 13-16
    digit numbers. this document have many CIN, ISIN and registration
    numbers, so just checking digit count will give lots of wrong matches."""
    digits = [int(d) for d in number_str if d.isdigit()]
    if not (13 <= len(digits) <= 19):
        return False
    checksum = 0
    parity = len(digits) % 2
    for i, d in enumerate(digits):
        if i % 2 == parity:
            d *= 2
            if d > 9:
                d -= 9
        checksum += d
    return checksum % 10 == 0

def find_credit_cards(text):
    results = []
    for m in CC_RE.finditer(text):
        if _luhn_ok(m.group()):
            results.append((m.start(), m.end(), m.group()))
    return results


# --- Date of birth ---------------------------------------------------------
# date alone is not enough because this document have many dates like
# incorporation date, board resolution date, offer date etc. most of them
# are not DOB. so only mark date when some DOB related word is nearby.
DATE_RE = re.compile(
    r"\b\d{1,2}(?:st|nd|rd|th)?[\s/-]"
    r"(?:January|February|March|April|May|June|July|August|September|"
    r"October|November|December|\d{1,2})"
    r"[\s/-]\d{2,4}\b",
    re.IGNORECASE,
)
DOB_CUE_RE = re.compile(r"date of birth|born on|d\.?o\.?b\.?", re.IGNORECASE)

def find_dobs(text):
    results = []
    for m in DATE_RE.finditer(text):
        window_start = max(0, m.start() - 40)
        window = text[window_start:m.end()]
        if DOB_CUE_RE.search(window):
            results.append((m.start(), m.end(), m.group()))
    return results