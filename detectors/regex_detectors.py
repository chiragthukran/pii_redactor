"""
Regex based detectors.

These are for PII types that follow a fixed, predictable pattern - so a
plain regex is enough and is actually more reliable than a ML/NER model
for these. NER is used separately (ner_detectors.py) for the free-form
stuff like names and addresses where there is no fixed pattern.

Each function returns a list of (start, end, matched_text) tuples so the
caller can slice these out of the paragraph text and replace them.
"""

import re


# --- Email -------------------------------------------------------------
EMAIL_RE = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)

def find_emails(text):
    return [(m.start(), m.end(), m.group()) for m in EMAIL_RE.finditer(text)]


# --- Phone numbers -------------------------------------------------------
# This document is Indian, so numbers mostly show up as "+91 20 4505 3237"
# or "+91 9876543210" or sometimes with dashes. Kept it fairly loose on
# purpose to catch the different spacing styles used across the document,
# then filtered by digit count so things like page numbers don't match.
PHONE_RE = re.compile(
    r"(\+?\d{1,3}[\s-]?)?(\(?\d{2,4}\)?[\s-]?){2,4}\d{3,4}"
)

def find_phones(text):
    results = []
    for m in PHONE_RE.finditer(text):
        digits = re.sub(r"\D", "", m.group())
        # a real phone number (with or without country code) has 10-13
        # digits. shorter matches are usually page refs / section numbers,
        # longer matches are usually CIN / registration numbers.
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
    """Luhn checksum - used to cut down false positives on random 13-16
    digit numbers (this document has a lot of those - CINs, ISINs,
    registration numbers etc, none of which are actual card numbers)."""
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
# dates by themselves are NOT enough - this document has hundreds of dates
# (incorporation dates, board resolution dates, offer dates etc) that are
# not anyone's DOB. So only flag a date if a DOB-ish word appears close by.
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
