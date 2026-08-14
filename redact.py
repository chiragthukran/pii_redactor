"""
main script. reads the input docx paragraph by paragraph, runs all the
detectors on the text, handles overlapping matches, replaces the matches
with fake values and then saves a new docx.

run: python3 redact.py input.docx output.docx
"""

import sys
from docx import Document

from detectors.regex_detectors import (
    find_emails, find_phones, find_ips, find_ssns, find_credit_cards, find_dobs,
)
from detectors.ner_detectors import find_people, find_companies, find_addresses
from faker_map import get_fake


# order is important here. when two detectors find overlapping text, the
# one which comes first gets priority.
# address is kept before person/company because it can be a much bigger
# match and person/company detectors can also detect parts of an address.
# regex detectors are also generally more reliable, so they get priority
# over the NER based ones.
DETECTOR_ORDER = [
    ("email", find_emails),
    ("phone", find_phones),
    ("ip", find_ips),
    ("ssn", find_ssns),
    ("credit_card", find_credit_cards),
    ("dob", find_dobs),
    ("address", find_addresses),
    ("person", find_people),
    ("company", find_companies),
]


def resolve_overlaps(all_matches):
    """keeps matches which dont overlap with something that already has
    higher priority. all_matches should already be in priority order."""
    kept = []
    for category, start, end, text in all_matches:
        overlap = False
        for _, ks, ke, _ in kept:
            if start < ke and end > ks:  # ranges overlap
                overlap = True
                break
        if not overlap:
            kept.append((category, start, end, text))
    return kept


def redact_paragraph_text(text):
    all_matches = []
    for category, fn in DETECTOR_ORDER:
        for start, end, matched_text in fn(text):
            all_matches.append((category, start, end, matched_text))

    kept = resolve_overlaps(all_matches)

    # replace from right to left so replacing one value doesnt change
    # the positions of the matches which are before it.
    kept.sort(key=lambda m: m[1], reverse=True)

    redacted = text
    count_by_type = {}
    for category, start, end, matched_text in kept:
        fake_value = get_fake(category, matched_text)
        redacted = redacted[:start] + fake_value + redacted[end:]
        count_by_type[category] = count_by_type.get(category, 0) + 1

    return redacted, count_by_type


def redact_docx(input_path, output_path):
    doc = Document(input_path)
    total_counts = {}

    def process_paragraph(paragraph):
        if not paragraph.text.strip():
            return

        new_text, counts = redact_paragraph_text(paragraph.text)

        for k, v in counts.items():
            total_counts[k] = total_counts.get(k, 0) + v

        if new_text != paragraph.text:
            # docx can split one paragraph into multiple runs because of
            # formatting, spell check etc. replacing the text directly can
            # mess up the formatting.
            #
            # simplest reliable way here is to put the new text in the
            # first run and clear the other runs. this can remove some
            # run-level formatting differences, but the document stays
            # readable and valid.
            if paragraph.runs:
                paragraph.runs[0].text = new_text
                for r in paragraph.runs[1:]:
                    r.text = ""
            else:
                paragraph.text = new_text

    for p in doc.paragraphs:
        process_paragraph(p)

    # a lot of prospectus content is inside tables too, like financial
    # statements and contact details. so process table paragraphs also.
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    process_paragraph(p)

    doc.save(output_path)
    return total_counts


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: python3 redact.py input.docx output.docx")
        sys.exit(1)

    counts = redact_docx(sys.argv[1], sys.argv[2])
    print("done. redaction counts by type:")
    for k, v in sorted(counts.items()):
        print(f"  {k}: {v}")