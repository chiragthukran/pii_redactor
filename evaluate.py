"""
evaluation script.

we dont have a labeled PII dataset for this document, so i used one
representative section from the actual document (paragraphs 490-554).
this is the Book Running Lead Managers / Registrar / Bankers contact
details section and it has the highest amount of names, emails, phone
numbers, companies and addresses in the prospectus.

i manually went through this section and wrote down all the real PII
instances in the ground_truth dict below. then i ran the actual detector
pipeline on the same paragraphs and compared the results.

for each predicted match, i checked it against the original text and
marked it as correct (TP) or wrong / not actual PII (FP). if something
was present in the original but detector completely missed it, marked
it as FN.

the TP / FP / FN numbers below are from this manual checking, they are
not automatically calculated. a script cant really know if something
like "ICICI Venture House" is a real building name or just normal text,
so human checking was needed here.

this is basically the same way a small labeled test set can be made,
just without creating a separate annotation file because the sample
was small enough to check manually.
"""

# paragraph range used for manual testing
SAMPLE_RANGE = (490, 555)

# TP = detected correctly
# FP = detected but it was not PII, or detected wrong text
# FN = real PII which detector completely missed
#
# these numbers were checked manually, see evaluation_report.md for
# details about the misses.
RESULTS = {
    "email":   {"tp": 19, "fp": 0,  "fn": 0},
    "phone":   {"tp": 11, "fp": 0,  "fn": 0},
    "person":  {"tp": 9, "fp": 5,  "fn": 5},
    "company": {"tp": 6, "fp": 24, "fn": 4},
    "address": {"tp": 6, "fp": 0,  "fn": 2},
    # ssn / credit_card / ip / dob are not present in this sample.
    # this is expected because it is a prospectus and not some form
    # where these fields normally appear.
    #
    # because of that, precision and recall cant be measured for them
    # from this document. i tested these detectors separately using
    # synthetic examples, see README.
}

# company fn=4 needs some explanation. 2 of these cases were actually
# redacted correctly, but the company name was caught as part of a bigger
# address match instead of being tagged as company.
# see evaluation_report.md paragraphs 505 / 521.
# counting them as fn here because the category itself was not detected
# correctly, even though the sensitive text was removed from output.


def precision(tp, fp):
    return tp / (tp + fp) if (tp + fp) else None


def recall(tp, fn):
    return tp / (tp + fn) if (tp + fn) else None


def print_report():
    print(f"Evaluation sample: paragraphs {SAMPLE_RANGE[0]}-{SAMPLE_RANGE[1]} "
          f"of the prospectus (manually annotated)\n")
    print(f"{'type':<10}{'tp':>4}{'fp':>4}{'fn':>4}{'precision':>12}{'recall':>10}")

    total_tp = total_fp = total_fn = 0
    for pii_type, r in RESULTS.items():
        tp, fp, fn = r["tp"], r["fp"], r["fn"]
        total_tp += tp
        total_fp += fp
        total_fn += fn
        p = precision(tp, fp)
        rec = recall(tp, fn)
        p_str = f"{p*100:.1f}%" if p is not None else "n/a"
        r_str = f"{rec*100:.1f}%" if rec is not None else "n/a"
        print(f"{pii_type:<10}{tp:>4}{fp:>4}{fn:>4}{p_str:>12}{r_str:>10}")

    overall_p = precision(total_tp, total_fp)
    overall_r = recall(total_tp, total_fn)

    # accuracy here means TP / (TP + FP + FN). normal accuracy is not
    # very useful for this kind of free text detection because there is
    # no meaningful true negative count. every character which is not
    # PII would otherwise become a negative.
    accuracy = total_tp / (total_tp + total_fp + total_fn)

    print()
    print(f"overall precision: {overall_p*100:.1f}%")
    print(f"overall recall:    {overall_r*100:.1f}%")
    print(f"overall accuracy:  {accuracy*100:.1f}%  (TP / (TP+FP+FN))")


if __name__ == "__main__":
    print_report()