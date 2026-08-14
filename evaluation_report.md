# Evaluation Report

## Methodology

there is no labeled PII dataset for this document, so i did the evaluation
manually on a sample instead of trying to automatically evaluate the whole
document.

1. i picked paragraphs 490-554 from the document. this is the Book Running
   Lead Managers / Registrar / Bankers contact details section. i picked
   this part because it has the highest amount of names, emails, phone
   numbers, company names and addresses in the document. around 25 of the
   documents ~30 email containing paragraphs are in or near this range, so
   this is more useful than taking a random sample because most random
   paragraphs are just legal text with little or no PII.
2. i read the original text of every paragraph in this range and manually
   wrote down all the actual PII, separated by type.
3. then i ran `redact_paragraph_text()` which is the actual function used
   by the tool, on the same paragraphs and compared the output with the
   list from step 2.
4. every predicted match was checked manually. if it was correct then TP,
   if it was wrong or not actually that type of PII then FP. anything from
   the original text which detector did not catch was counted as FN.

this was manual checking, not something calculated automatically. script
cant really know if "ICICI Venture House" is a company name or a building
name, someone has to read the actual sentence. the numbers below are from
this manual checking. `evaluate.py` only keeps these final numbers and
calculates the percentages. run it using `python3 evaluate.py`.

some judgment calls were also made while scoring:

- if a real company name was included inside a bigger *address* match
  instead of being detected as "company" (this happened twice in paragraphs
  505 and 521 with "ICICI Securities Limited"), i counted it as company FN
  even though the actual text was removed. being strict here because
  assignment asks for category wise recall.
- when two names joined with "/" were removed as one combined match, for
  example "Kishan Rastogi/Abhijit Diwan", i counted it as 1 TP + 1 FN
  instead of 2 TP because only one of the actual names was removed.

## Results

sample: paragraphs 490-554 (65 paragraphs, out of which 39 had at least
one real PII instance)

| PII type | TP | FP | FN | Precision | Recall |
|---|---|---|---|---|---|
| Email | 19 | 0 | 0 | 100.0% | 100.0% |
| Phone | 11 | 0 | 0 | 100.0% | 100.0% |
| Person | 9 | 5 | 5 | 64.3% | 64.3% |
| Company | 6 | 24 | 4 | 20.0% | 60.0% |
| Address | 6 | 0 | 2 | 100.0% | 75.0% |

**overall (micro average across these 5 categories):**

- Precision: 63.7%
- Recall: 82.3%
- Accuracy (TP / (TP+FP+FN)): 56.0%

"accuracy" is a little confusing for this type of task because this is
free text span detection and there is no useful true negative count.
basically every character which is not PII would become a negative, which
doesnt really tell much.

so i used TP / (TP+FP+FN) here. this is commonly used for overlap based
evaluation in NER type tasks. its basically showing how much of the
detected/expected PII was correct.

SSN, credit card, IP address and date of birth detectors could not be
properly evaluated on this document because none of them actually occur
in the sample. this is expected since it is a prospectus and not a form
collecting this kind of information.

i tested these four separately using some made-up examples instead. they
worked correctly there, but synthetic tests are not same as real messy
document data, so these should be considered untested by this report.

## Why company precision is so low (20%)

most of the false positives are coming from two paragraphs, 495 and 496.
there were 8 and 6 false positives respectively.

these paragraphs contain a lot of legal/procedural text and capitalized
terms like "Bid cum Application Form", "Client ID", "PAN" etc. spaCy's
small model sometimes thinks these are ORG entities.

outside these two paragraphs the company detector works better. some of
the remaining false positives are things like "Maharashtra, India" left
at the end of a paragraph after the address detector already caught the
main part somewhere else, and some building/street names like
"One World Centre" and "G Block" which spacy treated like company names.

so actual company detection is better than the 20% number might look,
but this evaluation is showing what actually happened on this sample,
not the best possible result. because of that 20% stays in the results.

## Why address recall improved from 0% to 75%

the first version of address detector only looked for text after labels
like "Registered Office:", "Corporate Office:" or "Address:".

this worked for the company address at the top of the document, but not
for the addresses in this sample. bank, registrar and legal-counsel
addresses are mostly written as normal text without these labels.

when i first tested it, it caught 0/8 addresses.

then i added a fallback. if a paragraph has a PIN-code type number and
also has a location word like India, Maharashtra, Mumbai or Pune, the
whole paragraph is treated as an address even when there is no address
label.

after running the same evaluation again, recall became 75% (6/8).

the 2 remaining misses happen because the PIN-code line also contains a
phone number in paragraphs 535 and 552. the overlap resolution currently
drops the complete address when part of it overlaps with a higher priority
match, in this case phone number. only a small part is actually overlapping
but the whole address match gets removed.

i didnt fix this here. keeping it as a known limitation in the README.

## Synthetic tests (SSN / credit card / IP / DOB)

```text
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
  -> correctly NOT redacted (fails Luhn check, so it confirms the checksum
     is actually filtering non-card numbers and not just matching every
     16 digit number)