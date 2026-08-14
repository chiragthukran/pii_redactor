"""
ner based detectors for PII which dont have a fixed pattern,
like person names, company names and addresses.

using spacy small english model (en_core_web_sm). i used the small
model instead of bigger trf/lg mainly because of speed. this document
have 1000+ paragraphs and we run NER on it once, so processing time
can add up. small model is less accurate than transformer one but
after checking some samples it was good enough (see evaluation_report.md).
"""

import re
import spacy
from detectors.stoplist import ORG_STOPLIST, PERSON_STOPLIST, COMPANY_SUFFIXES

_nlp = spacy.load("en_core_web_sm")

# indian PIN code is 6 digits. using this mainly as a signal that we are
# probably inside an address, not directly redacting the PIN itself.
# some PINs in this document have a space like "410 501", so allow that.
PIN_RE = re.compile(r"\b\d{3}\s?\d{3}\b")

# words which usually comes before an address block. using these lets us
# grab the complete address instead of only depending on spacy GPE/LOC.
# spacy usually catches city/state but can miss street level details.
ADDRESS_CUE_RE = re.compile(
    r"(Registered Office|Corporate Office|Registered and Corporate Office|"
    r"Address)\s*:\s*",
    re.IGNORECASE,
)


def find_people(text):
    """returns list of (start, end, text) for PERSON entities."""
    doc = _nlp(text)
    results = []
    for ent in doc.ents:
        if ent.label_ == "PERSON" and ent.text.strip().lower() not in PERSON_STOPLIST:
            # skipping single word matches because there were too many
            # false hits from random capitalized words, headings and
            # defined terms being detected as PERSON by the small model.
            if len(ent.text.strip().split()) >= 2:
                results.append((ent.start_char, ent.end_char, ent.text))
    return results


def find_companies(text):
    """returns list of (start, end, text) for ORG entities after removing
    the legal/regulatory terms from the stoplist.

    RHP documents have a lot of capitalized terms like Company, Board,
    Offer, Promoters etc. spacy tags many of them as ORG because they
    look like proper nouns.

    stoplist catches the ones found during testing, but it will never
    be complete. so also checking company suffixes like Limited, LLP,
    Bank etc. or allowing names with atleast 2 words.

    this is not perfect and can reduce recall, but it removes a good
    amount of the false matches. mentioned this limitation in README.
    """
    doc = _nlp(text)
    results = []
    for ent in doc.ents:
        raw = ent.text.strip()
        low = raw.lower()
        if low in ORG_STOPLIST:
            continue
        if not any(c.isalpha() for c in raw):
            continue  # sometimes currency symbols etc gets picked as ORG
        if any(c.isdigit() for c in raw):
            # dates and amounts like "May 6, 2025" and "Fiscal 2025"
            # are detected as ORG quite often by small model. company
            # names in this document dont have digits, so skipping these.
            continue
        has_suffix = any(low.endswith(suf) or f"{suf} " in low for suf in COMPANY_SUFFIXES)
        if has_suffix or len(raw.split()) >= 2:
            results.append((ent.start_char, ent.end_char, ent.text))
    return results


GEO_CUE_RE = re.compile(
    r"\b(India|Maharashtra|Mumbai|Pune)\b", re.IGNORECASE
)


def find_addresses(text):
    """finds text after an address cue like "Registered Office:" or
    "Corporate Office:" and stops at the next semicolon or period.

    during evaluation (see evaluation_report.md), found that most
    addresses in this document dont have these cue words. bank, registrar
    and legal counsel addresses are mostly just written as normal text
    across a few lines.

    example:
        "801-804, Wing A, Building No. 3 Inspire BKC G Block"
        "Bandra East, Mumbai - 400 051 Maharashtra, India"

    first version only handled cue labelled addresses and got 0% recall
    on this category in the sample.

    added a fallback where if paragraph has no cue but has a PIN code
    and a geography word like India, Maharashtra, Mumbai or Pune, the
    whole paragraph is treated as an address.

    this still wont catch the first line of a multi-line address when
    the PIN is only in the next paragraph. that part stays unredacted.
    this is a known limitation mentioned in README.
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