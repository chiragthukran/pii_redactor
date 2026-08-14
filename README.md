# PII Redaction Tool

Redacts PII from the Red Herring Prospectus (or any similar docx) and replaces
it with fake but realistic looking values, consistently (same real name/email/etc
always maps to the same fake one throughout the document).

## How to run

```
pip install python-docx spacy faker
python -m spacy download en_core_web_sm
python3 redact.py Red_Herring_Prospectus.docx Red_Herring_Prospectus_REDACTED.docx
```

Prints a count of how many of each PII type got redacted when it's done.

To run the evaluation report:
```
python3 evaluate.py
```

## Approach

Hybrid regex + NER, not one or the other.

- **Regex** for email, phone, IP, SSN, credit card, date of birth. These all
  have a fixed shape so a plain pattern match is more reliable here than a ML
  model would be. Credit card numbers also get run through a Luhn checksum on
  top of the regex, otherwise random 13-16 digit numbers (this doc has a lot
  of those - CINs, ISINs, registration numbers) get flagged as cards.
  Dates of birth only get flagged if there's a "date of birth" / "born on" /
  "DOB" type word within ~40 characters, because this document has hundreds
  of other dates (incorporation dates, resolution dates, offer dates) that
  aren't anyone's DOB - a bare date regex alone would false-positive on
  basically every date in the document.

- **NER (spaCy, en_core_web_sm)** for names, company names, and addresses,
  since these don't follow a fixed pattern. Used the small model over the
  bigger transformer based one mainly for speed on a 1000+ paragraph doc.

- Everything gets mapped through a fake-value cache (`faker_map.py`) so a
  name/email/etc that shows up 20 times in the document becomes the same
  fake value every time, not a different random one each time.

- Addresses are handled a bit differently - see "address detection" below,
  this needed a couple of iterations.

## Why not just use Presidio

Considered it, it's a legit option for this and would have saved time. Went
with a custom build instead mainly because:
1. this document is Indian (phone format, addresses, no real SSNs since
   India uses PAN/Aadhaar not SSN) - Presidio's default recognizers are
   tuned for US/UK, so custom recognizers would have been needed either way.
2. writing the detection logic directly made it a lot easier to explain
   *why* something got flagged or missed for the evaluation report below -
   debugging your own regex/NER logic is more transparent than debugging a
   third party library's internals for this kind of writeup.

## Company/name detection - the precision problem

Ran the company (ORG) detector on the raw document first and got 1772 hits,
way more than could possibly be real. Checked what was actually being
flagged and it was mostly capitalized legal "defined terms" that Indian RHP
documents use constantly - "Company", "Board", "Offer", "Promoters",
"Prospectus", things like that get capitalized throughout this kind of
document and spaCy tags a lot of them as ORG because they look like proper
nouns in that position.

Fixed this in two ways:
1. built a stoplist of the specific terms found by testing (see
   `detectors/stoplist.py`) - this is a bit hacky, it was built by literally
   running the detector, looking at what came out, and manually deciding
   term by term whether it was a real company or a legal defined-term.
   Won't generalize perfectly to a different document.
2. added a rule that a match only counts as a company if it either ends in
   a company suffix (Limited, LLP, Bank, etc) or is at least 2 words and
   doesn't contain digits (dates and monetary amounts were also getting
   tagged ORG a lot - "Fiscal 2025", "May 6, 2025" - real company names in
   this doc never had digits in them so this was a safe cut).

This got the count down from 1772 to ~960, and precision from very bad to
still-not-great-but-honest (see evaluation report - company precision came
out to 20% on the tested sample). Company/org names are the weakest part of
this tool and that's the honest result, not something I'm hiding.

Names have a smaller but similar issue: went with requiring at least 2
words for a PERSON match, which avoids single-word false positives but
means a name split with a slash instead of "and" (e.g.
"Kishan Rastogi/Abhijit Diwan") sometimes gets caught as one combined
entity instead of two, or one of the two gets missed. Also noticed
**names written in ALL CAPS don't get reliably detected** - the document
has a promoters list with names in all caps and mixed case in the same
sentence, and only the mixed-case ones consistently got caught. This is a
spaCy NER weakness, not something addressed here - documenting it rather
than pretending it's not there.

## Address detection

First version only matched addresses that were explicitly labelled
("Registered Office:", "Corporate Office:", "Address:") which is how the
company's own address is written at the top of the document. Ran the
evaluation and got 0% recall on addresses, because it turns out almost none
of the *other* addresses in the document (banks, registrar, legal counsel
contact blocks) use that labelling - they're just written as a bare address
block.

Added a fallback: if a paragraph has no cue phrase but has something that
looks like an Indian PIN code (6 digits, sometimes written with a space in
the middle - "410 501") together with a geography word (India / Maharashtra
/ Mumbai / Pune), treat the whole paragraph as an address. Recall went from
0% to 75% on the evaluation sample after this.

Known remaining issue: this only catches whichever single paragraph has the
PIN code in it. A lot of addresses in this document are split across 2-4
paragraphs (building name on one line, city+PIN on the next), and only the
PIN-bearing line gets redacted - the rest of the address stays untouched.
Also, when the PIN-bearing line also has a phone number or email in it
(happens a few times), the address match gets thrown out entirely because
of how overlapping matches are resolved - see `resolve_overlaps()` in
redact.py, it currently rejects a whole match if the paragraph priority
order already claimed any part of that span, but the address fallback grabs
the entire paragraph as one span so a small overlap kills the entire
address, not just the overlapping part. Didn't fix this - would need
address to be extracted as a sub-span (the address text specifically) not
the whole paragraph, ran out of time to do this cleanly.

## Ticket/order numbers

Assignment mentions being explicit about whether things like ticket/order
numbers count as sensitive. This document doesn't have ticket/order numbers
(it's a prospectus, not a support log) but it does have the equivalent -
CIN (Corporate Identity Number), SEBI registration numbers, ISIN codes.
Decision: **not treated as PII** here, same reasoning the assignment gives
for order numbers - these identify a company/registration, not a person,
and they're public regulatory filings info by design. Documented this
choice rather than silently deciding it.

## Code structure

```
redact.py                 - main script, ties everything together
detectors/regex_detectors.py  - email, phone, ip, ssn, credit_card, dob
detectors/ner_detectors.py    - person, company, address (spaCy based)
detectors/stoplist.py         - legal/regulatory terms to exclude
faker_map.py               - keeps real->fake mapping consistent
evaluate.py                - precision/recall/accuracy against the manual sample
```

To add a new PII type: write a `find_x(text) -> [(start, end, text), ...]`
function in whichever detectors file fits, add it to `DETECTOR_ORDER` in
redact.py (position matters - earlier = higher priority when spans
overlap), add a branch in `faker_map.get_fake()` for what kind of fake
value to generate.

## Known false positives/negatives (summary)

- Company/org: lowest precision by far (~20% on tested sample) - legal
  defined-terms in this kind of document look too much like proper nouns.
- Person names: names joined with "/" instead of "and" sometimes collapse
  into one match or lose the second name. ALL CAPS names often missed
  entirely.
- Addresses: only the PIN-code-bearing line of a multi-line address gets
  redacted; the rest of a split address can remain in the output.
- Email/phone: very reliable, 100%/100% on the tested sample - these have
  a fixed enough shape that regex handles them well.
