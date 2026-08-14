"""
NER based detectors for PII types which dont have fixed pattern,
like person names, company names and address.

using spacy small english model (en_core_web_sm). i used small model
instead of bigger trf/lg models mostly because of speed. this document
have 1000+ paragraphs and we run NER on it once, so processing time
can increase. small model is less accurate than transformer model but
after checking some samples it was good enough (see evaluation_report.md)
"""

import re
import spacy
from detectors.stoplist import ORG_STOPLIST, PERSON_STOPLIST, COMPANY_SUFFIXES

_nlp = spacy.load("en_core_web_sm")

# indian PIN code is 6 digit, we use it as a signal that text is probably
# an address, not directly for redaction. some addresses in this document
# write PIN with space in middle like "410 501", so allowing space also.
PIN_RE = re.compile(r"\b\d{3}\s?\d{3}\b")

# these are some words which comes before address block. matching these
# helps us take complete address instead of only depending on spacy GPE/LOC
# because spacy mostly catch city/state and miss the street details.
ADDRESS_CUE_RE = re.compile(
    r"(Registered Office|Corporate Office|Registered and Corporate Office|"
    r"Address)\s*:\s*",
    re.IGNORECASE,
)


def find_people(text):
    """Returns list of (start, end, text) for PERSON entities."""
    doc = _nlp(text)
    results = []
    for ent in doc.ents:
        if ent.label_ == "PERSON" and ent.text.strip().lower() not in PERSON_STOPLIST:
            # skipping single word matches because small model give lot of
            # false matches. it sometimes detect heading or other capitalized
            # words as person name, so keeping atleast 2 words.
            if len(ent.text.strip().split()) >= 2:
                results.append((ent.start_char, ent.end_char, ent.text))
    return results


def find_companies(text):
    """Returns list of (start, end, text) for ORG entities, after removing
    common legal/regulatory words.

    RHP document has lot of capitalized words like Company, Board, Offer,
    Promoters etc and spacy sometimes mark them as ORG because they look
    like proper names.

    stoplist have some of the words which we found while testing.
    also checking company suffix like Limited, LLP, Bank etc. if it
    doesnt have suffix then atleast 2 words are required.

    this is not perfect and can miss some companies, but it removes
    a good amount of false matches. mentioned this limitation in README.
    """
    doc = _nlp(text)
    results = []
    for ent in doc.ents:
        raw = ent.text.strip()
        low = raw.lower()
        if low in ORG_STOPLIST:
            continue
        if not any(c.isalpha() for c in raw):
            continue  # sometimes currency symbols etc gets detected as ORG
        if any(c.isdigit() for c in raw):
            # dates and amounts like "May 6, 2025" or "Fiscal 2025" gets
            # detected as ORG many times by small model. company names in
            # this document dont have digits, so skipping these.
            continue
        has_suffix = any(low.endswith(suf) or f"{suf} " in low for suf in COMPANY_SUFFIXES)
        if has_suffix or len(raw.split()) >= 2:
            results.append((ent.start_char, ent.end_char, ent.text))
    return results


GEO_CUE_RE = re.compile(
    r"\b(India|Maharashtra|Mumbai|Pune)\b", re.IGNORECASE
)


def find_addresses(text):
    """find address after words like "Registered Office:" or
    "Corporate Office:" and stop when next semicolon or period comes.

    while testing (see evaluation_report.md), found that many addresses
    in this document dont have these words. bank, registrar and legal
    counsel addresses are mostly written as normal text in 2-3 lines.

    example:
        "801-804, Wing A, Building No. 3 Inspire BKC G Block"
        "Bandra East, Mumbai - 400 051 Maharashtra, India"

    first version was only matching address with cue phrase and it gave
    0% recall for this type of address in sample.

    added fallback for this. if paragraph dont have cue phrase but has
    PIN code and one geography word like India, Maharashtra, Mumbai or
    Pune, then treat complete paragraph as address.

    still there is one limitation. if address is split in two paragraphs,
    first part may not have PIN code so it will not get detected. example
    "Wing A, Building No. 3" can stay unredacted. this is known limitation
    and mentioned in README.
    """
    results = []
    matched_span = None

    for cue in ADDRESS_CUE_RE.finditer(text):
        start = cue.end()
        rest = text[start:]
        stop = re.search(r"[;.](?=\s+[A-Z]|\s*$)", rest)
        end = start + stop.start() if stop else len(text)
        addr_text = text[start:end].strip()
        if addr_text and PIN_RE.search(addr_text):
            results.append((start, end, addr_text))
            matched_span = (start, end)

    if not results and PIN_RE.search(text) and GEO_CUE_RE.search(text):
        stripped = text.strip()
        if stripped:
            start = text.index(stripped)
            end = start + len(stripped)
            results.append((start, end, stripped))

    return results