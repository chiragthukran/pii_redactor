# PII Redaction Tool
hi I am Chirag,
this tool removes PII from a Red Herring Prospectus (or similar docx file) and replaces it with fake but realistic looking values. same real name, email, phone etc will always get the same fake value everywhere in the document.

## How to run

```bash
pip install python-docx spacy faker
python -m spacy download en_core_web_sm
python3 redact.py Red_Herring_Prospectus.docx Red_Herring_Prospectus_REDACTED.docx
```

after running it, it prints how many PII of each type was redacted.

to run the evaluation report:

```bash
python3 evaluate.py
```

## Approach

using a hybrid approach of regex + NER instead of depending on only one of them.

- Regex is used for email, phone, IP, SSN, credit card and date of birth. these have a mostly fixed pattern, so normal regex is more reliable here than using ML model. credit cards also go through Luhn checksum after regex, otherwise random 13-16 digit numbers can get detected as cards. this document have lots of numbers like CIN, ISIN and registration numbers. DOB is only detected when words like "date of birth", "born on" or "DOB" are close to the date. otherwise almost every date in this document would get detected because there are hundreds of dates for incorporation, resolutions, offers etc.
- NER (spacy, en_core_web_sm) is used for names, company names and addresses because these dont have a fixed format. used the small model mainly because this document has 1000+ paragraphs and the bigger transformer model would take more time.
- all detected values are passed through a fake-value cache (faker_map.py). so if same name/email appears 20 times, it gets the same fake value every time instead of a new random value.
- address detection is a little different from the other PII types. details about this are below.

## Why not just use Presidio

i did consider Presidio because it is a proper option for PII detection and probably would have saved some time.

but decided to make the detector myself mainly because:

1. this document is indian, so phone numbers and addresses follow indian formats. there are also no normal SSNs because India uses things like PAN/Aadhaar instead. Presidio default recognizers are more focused on US/UK formats, so custom recognizers would still be needed.
2. with custom regex and NER logic, it is easier to explain why something was detected or missed in the evaluation report. debugging my own regex/NER rules is more transparent for this assignment than trying to explain internals of another library.

## Company/name detection - the precision problem

when i first ran the company (ORG) detector on the full document, it gave around 1772 matches, which was clearly way too many to be actual companies.

after checking the results, most of these were capitalized legal "defined terms" that are used everywhere in indian RHP documents. things like "Company", "Board", "Offer", "Promoters", "Prospectus" etc are capitalized a lot, and spacy sees them as proper nouns and sometimes tags them as ORG.

i tried to reduce this in two ways:

1. made a stoplist containing the terms found during testing (detectors/stoplist.py). basically i ran the detector, checked the output and manually decided which terms were actual company names and which were just legal defined terms. this is a little hacky and will not work perfectly on a completely different document.
2. added a rule where a company match should either end with a common company suffix like Limited, LLP, Bank etc, or have at least 2 words and no digits. dates and amounts were also getting detected as ORG a lot, like "Fiscal 2025" and "May 6, 2025". real company names in this document did not have digits, so this was a reasonable filter for this document.

this brought the number of matches down from 1772 to around 960. precision also became much better, but still not very good. in the evaluation sample company precision was only 20%.

so company/org detection is the weakest part of this tool. i am keeping this result as it is instead of hiding the bad precision.

person detection has a smaller similar problem. i require at least 2 words for a PERSON match because single words were giving many false positives. but this also means names joined with / instead of "and", like "Kishan Rastogi/Abhijit Diwan", can sometimes be detected as one entity or one of the names can be missed.

also noticed that ALL CAPS names are not detected reliably. there is a promoters list where some names are all caps and some are mixed case, and the mixed case names were detected more consistently.

this is a weakness of the spacy NER model. i didnt try to hide it and have mentioned it in the evaluation.

## Address detection

the first version only detected addresses after labels like "Registered Office:", "Corporate Office:" and "Address:". this worked for the company's own address at the top of the document.

but after running the evaluation, i found that most other addresses in the document, like bank, registrar and legal counsel addresses, dont use these labels. they are just written as normal address blocks.

so i added a fallback.

if a paragraph does not have an address cue but contains something that looks like an indian PIN code (6 digits, sometimes with a space like "410 501") and also has a location word like India, Maharashtra, Mumbai or Pune, then the whole paragraph is treated as an address.

after this change, address recall went from 0% to 75% on the evaluation sample.

there is still a known issue here. the detector only catches the paragraph containing the PIN code. many addresses in this document are split across 2-4 paragraphs, for example building name on one line and city + PIN on another line. only the PIN containing paragraph gets redacted, so other parts can remain.

another issue happens when the same PIN line also contains a phone or email. sometimes the whole address match gets removed because of overlap resolution. resolve_overlaps() in redact.py currently rejects the whole match when another higher priority match already owns part of its span.

so even if only a few characters overlap, the complete address can be removed from the matches.

i didnt fix this because the proper solution would be to detect only the actual address part instead of taking the whole paragraph as one span.

## Ticket/order numbers

the assignment asks to be clear about whether things like ticket/order numbers should be considered sensitive.

this document doesnt have ticket or order numbers because it is a prospectus, not a support log. but it does contain similar identifiers like CIN, SEBI registration numbers and ISIN codes.

**decision:** these are not treated as PII.

reason is that these identify a company or registration, not a person, and they are already public information in regulatory filings. this choice is documented instead of silently ignoring these numbers.

## Code structure

```
redact.py                     - main script, connects everything
detectors/regex_detectors.py - email, phone, ip, ssn, credit_card, dob
detectors/ner_detectors.py   - person, company, address using spacy
detectors/stoplist.py        - legal/regulatory terms to ignore
faker_map.py                 - keeps real -> fake mapping consistent
evaluate.py                  - manual sample precision/recall/accuracy
```

to add a new PII type, create a `find_x(text) -> [(start, end, text), ...]` function in the appropriate detector file.

then add it to DETECTOR_ORDER in redact.py. the position is important because earlier detectors have higher priority when spans overlap.

also add a new branch in faker_map.get_fake() for generating the fake replacement value.

## Known false positives/negatives

- **Company/org:** lowest precision by far, around 20% on the tested sample. legal defined terms in this type of document look too much like proper nouns to the general NER model.
- **Person names:** names joined with / can sometimes become one match or the second name can be missed. ALL CAPS names are also often missed.
- **Addresses:** only the PIN-code paragraph of a multi-line address gets detected, so other parts of the address can remain.
- **Email/phone:** very reliable on the tested sample, both had 100% precision and recall. these have a fixed enough format that regex works well for them.