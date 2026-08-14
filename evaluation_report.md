# Evaluation Report

## Methodology

No labeled PII dataset exists for this document, so evaluation was done by
hand on a sample rather than automatically on the whole thing:

1. Picked paragraphs 490-554 of the document - the Book Running Lead
   Managers / Registrar / Bankers contact-details block. Chose this section
   specifically because it's the single densest cluster of names, emails,
   phone numbers, company names and addresses anywhere in the document (25
   of the doc's ~30 email-containing paragraphs are in or near this range) -
   a much better test of the detectors than a random sample would be, since
   a random sample of this document is mostly plain legal prose with little
   to no PII in most paragraphs.
2. Read through the original text of every paragraph in that range and
   wrote down every real PII instance by hand, by type.
3. Ran `redact_paragraph_text()` (the actual function used by the tool) on
   the same paragraphs and compared the output side by side against the
   list from step 2.
4. Every predicted match was marked TP (correct) or FP (flagged but not
   actually that type of PII, or wrong text entirely). Anything from step 2
   that never showed up in the output was marked FN.

This is manual work, not something a script computed on its own - a script
can't tell you on its own whether "ICICI Venture House" is a real company
name or a building name, someone has to actually read the sentence. The
counts below are the result of that manual walkthrough (`evaluate.py` just
holds the final tallies and computes the percentages from them, run it with
`python3 evaluate.py`).

A couple of judgment calls made during scoring, noted here rather than
buried in the numbers:
- If a real company name got swept into a bigger *address* match instead of
  being tagged "company" specifically (happened twice - paragraphs 505 and
  521, "ICICI Securities Limited"), it's counted as a company FN even
  though the text itself did get redacted correctly, just under the wrong
  label. Being strict about this because the assignment asks for
  per-category recall.
- Where two names joined with "/" got redacted as a single combined match
  (e.g. "Kishan Rastogi/Abhijit Diwan" -> one fake name instead of two),
  counted as 1 TP + 1 FN, not 2 TP, since only one of the two real names is
  actually gone from the output.

## Results

Sample: paragraphs 490-554 (65 paragraphs, of which 39 contained at least
one real PII instance)

| PII type | TP | FP | FN | Precision | Recall |
|---|---|---|---|---|---|
| Email | 19 | 0 | 0 | 100.0% | 100.0% |
| Phone | 11 | 0 | 0 | 100.0% | 100.0% |
| Person | 9 | 5 | 5 | 64.3% | 64.3% |
| Company | 6 | 24 | 4 | 20.0% | 60.0% |
| Address | 6 | 0 | 2 | 100.0% | 75.0% |

**Overall (micro-averaged across the 5 categories above):**
- Precision: 63.7%
- Recall: 82.3%
- Accuracy (TP / (TP+FP+FN)): 56.0%

"Accuracy" doesn't have a clean textbook definition for a free-text span
extraction task like this one - there's no meaningful count of "true
negatives" (every character that isn't PII would count as one, which isn't
useful). Used TP / (TP+FP+FN) here, which is the standard way overlap-based
accuracy gets reported for NER-style tasks - it's really the same thing as
a micro-averaged F1 score's numerator/denominator, just phrased as a single
"how much of what I said was right" number.

SSN, credit card, IP address and date-of-birth detectors could not be
evaluated against this document because none of those actually appear in
it (expected - it's a prospectus, not a form that collects that kind of
data). Tested those four separately against made-up example sentences
instead (see the "synthetic test" section below) - they all worked
correctly there, but that's not the same as being tested against real
messy text, so treat those as untested by this report, not as validated.

## Why company precision is so low (20%)

Almost all of the false positives come from two specific paragraphs (495
and 496 - 8 and 6 false positives respectively) that are dense legal
boilerplate about grievance redressal procedures, full of capitalized
administrative terms like "Bid cum Application Form", "Client ID", "PAN"
etc that spaCy's small model tags as ORG. Outside of those two paragraphs,
company precision is meaningfully better - most of the remaining false
positives are single "Maharashtra, India" fragments left over at the end of
a paragraph after the address fallback already redacted the rest of that
address on a different line, and a handful of building/street names
("One World Centre", "G Block") that got tagged as if they were companies.

This means the real company/org detector is more precise than the 20%
number suggests *outside of dense procedural/legal paragraphs specifically*
- but this evaluation is reporting what actually happened on this sample,
not a best-case number, so 20% is what's in the table above.

## Why address recall improved from 0% to 75% mid-build

First version of the address detector only matched text after an explicit
"Registered Office:" / "Corporate Office:" / "Address:" label, since that's
how the document's own address is written at the top. Running the
evaluation against this sample showed 0/8 addresses caught, because the
bank/registrar/legal-counsel addresses in this section aren't labelled that
way at all - they're just written as a bare address block across a couple
of lines.

Fixed by adding a fallback that treats a whole paragraph as an address if
it has a PIN-code-shaped number together with a geography word (India /
Maharashtra / Mumbai / Pune), even with no label. Re-ran the same
evaluation after the fix - recall went to 75% (6/8). The 2 remaining misses
are both cases where the PIN-bearing line also contained a phone number
(paragraphs 535 and 552) - the overlap-resolution logic currently discards
an entire address match if any part of it overlaps a higher-priority match
(phone, in this case), even though only a few characters actually overlap.
Not fixed - noted as a known limitation in the README.

## Synthetic tests (SSN / credit card / IP / DOB)

```
His SSN is 123-45-6789 for verification.
  -> redacted correctly

Card number 4532 0151 1283 0366 was used for the payment.
  -> redacted correctly

Server IP address 192.168.1.105 logged the request.
  -> redacted correctly

Date of birth: 15 March 1990, as per records.
  -> redacted correctly

The company reported a random number 4111111111111234 which is not a
valid card.
  -> correctly NOT redacted (fails Luhn check, confirms the checksum is
     actually filtering out non-card numbers rather than just matching
     any 16-digit string)
```

## Honest summary

Email and phone detection are solid (100%/100% on the tested sample - not
surprising, these have a fixed enough shape that regex is close to a
solved problem for them). Address detection is decent after the mid-build
fix but still has a real gap on multi-line addresses. Person name detection
is medium - works for clearly-formatted mixed-case names, struggles with
all-caps names and slash-separated name lists. Company/org detection is the
weak point of this tool - legal documents like this one use so many
capitalized "defined terms" that look exactly like proper nouns that a
general-purpose NER model without deep customization is going to
over-flag; a production version of this would need a much bigger,
more carefully maintained stoplist, or a model fine-tuned specifically on
legal/financial filings rather than general English text.
