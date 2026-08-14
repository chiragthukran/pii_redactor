"""
NER based detectors, for the PII types that don't have a fixed pattern:
person names, company names, and addresses.

Uses spaCy's small English model (en_core_web_sm). Went with the small
model over the larger trf/lg ones mainly for speed - this document has
1000+ paragraphs and we run it through NER once, so processing time adds
up. Small model is less accurate than the transformer based one but was
good enough after checking against a sample (see evaluation_report.md).
"""

import re
import spacy
from detectors.stoplist import ORG_STOPLIST, PERSON_STOPLIST, COMPANY_SUFFIXES

_nlp = spacy.load("en_core_web_sm")

# Indian PIN code is 6 digits - used as a signal that we are inside an
# address, not for direct redaction on its own. this document writes
# some of them with a space in the middle (eg "410 501") so allow that.
PIN_RE = re.compile(r"\b\d{3}\s?\d{3}\b")

# lines that introduce an address block - matching on the cue phrase lets
# us grab the surrounding text as one address rather than relying purely
# on spacy's GPE/LOC tags, which tend to only catch the city/state part
# and miss the street-level details.
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
            # skip single-word matches, too many false hits from random
            # capitalised words (headings, defined terms) being tagged
            # PERSON by the small model
            if len(ent.text.strip().split()) >= 2:
                results.append((ent.start_char, ent.end_char, ent.text))
    return results


def find_companies(text):
    """Returns list of (start, end, text) for ORG entities, minus the
    legal/regulatory stoplist terms.

    RHP documents capitalize a LOT of defined legal terms (Company,
    Board, Offer, Promoters etc) and spacy tags most of these as ORG
    since they look like proper nouns. Stoplist above catches the ones
    we found by testing, but that list will never be complete for a
    document like this. So on top of the stoplist, also require the
    match to either end in a recognisable company suffix (Limited, LLP,
    Bank etc) or be at least 2 words AND not purely alphabetic-only
    generic looking (crude, but cuts down a chunk of the remaining
    noise). This trades some recall for precision - documented as a
    known limitation in the README.
    """
    doc = _nlp(text)
    results = []
    for ent in doc.ents:
        raw = ent.text.strip()
        low = raw.lower()
        if low in ORG_STOPLIST:
            continue
        if not any(c.isalpha() for c in raw):
            continue  # currency symbols etc picked up as ORG sometimes
        if any(c.isdigit() for c in raw):
            # dates and amounts ("May 6, 2025", "Fiscal 2025") get
            # tagged ORG a lot by the small model. real company names
            # in this doc never had digits in them, so this is a safe
            # cut that removes a big chunk of the noise found in testing
            continue
        has_suffix = any(low.endswith(suf) or f"{suf} " in low for suf in COMPANY_SUFFIXES)
        if has_suffix or len(raw.split()) >= 2:
            results.append((ent.start_char, ent.end_char, ent.text))
    return results


GEO_CUE_RE = re.compile(
    r"\b(India|Maharashtra|Mumbai|Pune)\b", re.IGNORECASE
)


def find_addresses(text):
    """Grabs the text after an address-introducing cue phrase, up to the
    next semicolon or period. Works well for the "Registered Office:" /
    "Corporate Office:" style labels used at the top of the document.

    Problem found during evaluation (see evaluation_report.md): most of
    the addresses in this document (bank/registrar/legal-counsel contact
    blocks) are NOT written with one of those cue words - they are just
    a bare address split across a couple of lines, e.g.:
        "801-804, Wing A, Building No. 3 Inspire BKC G Block"
        "Bandra East, Mumbai - 400 051 Maharashtra, India"
    First version of this only matched the cue-labelled ones and scored
    0% recall on this whole category when tested against the sample.

    Added a fallback: if a paragraph has no cue phrase, but it does have
    a PIN-code-shaped number together with a geography word (India /
    Maharashtra / Mumbai / Pune), treat the whole paragraph as an
    address. This still won't catch the earlier line of a 2-line address
    (the "Wing A, Building No. 3" part above stays unredacted since it's
    a separate paragraph with no PIN code in it) - that's a real
    remaining limitation, noted in the README, not something this
    fallback fixes. But it's a lot better than catching nothing.
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
