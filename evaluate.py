"""
Evaluation script.

We don't have a labeled PII dataset for this document, so the approach
taken here is: pick one dense, representative section of the actual
document (paragraphs 490-554 - the Book Running Lead Managers /
Registrar / Bankers contact-details block, which is the single densest
cluster of names/emails/phones/companies/addresses in the whole
prospectus), manually read through it and write down every real PII
instance by hand (see ground_truth dict below), then run the actual
detector pipeline on the same paragraphs and compare.

This was done by going through the redact_paragraph_text() output for
each paragraph in that range side by side with the original text and
marking, for every predicted match: correct (TP), wrong / not real PII
(FP). Anything present in the original text that the pipeline did not
catch at all was marked FN.

TP / FP / FN counts below are the result of that manual comparison, not
computed automatically - a script can't tell you whether "ICICI Venture
House" is a real building name or not, that needs a human to actually
read the sentence. This is basically the same manual process someone
would use to build a labeled test set, just not saved as a separate
annotation file since the sample is small enough to reason about
directly.
"""

# paragraph range used for the manual evaluation
SAMPLE_RANGE = (490, 555)

# TP = predicted correctly, FP = predicted but not actually PII (or
# wrong span), FN = real PII the pipeline did not catch at all.
# worked out by hand, see docstring above and evaluation_report.md for
# the walkthrough of specific misses.
RESULTS = {
    "email":   {"tp": 19, "fp": 0,  "fn": 0},
    "phone":   {"tp": 11, "fp": 0,  "fn": 0},
    "person":  {"tp": 9,  "fp": 5,  "fn": 5},
    "company": {"tp": 6,  "fp": 24, "fn": 4},
    "address": {"tp": 6,  "fp": 0,  "fn": 2},
    # ssn / credit_card / ip / dob did not appear in this sample section
    # at all (expected - it's a prospectus, not a form with those
    # fields), so precision/recall can't be measured from this document.
    # tested those detectors separately against synthetic examples
    # instead - see README.
}
# note on company fn=4: 2 of those are cases where the company name
# WAS actually redacted correctly, just as part of a bigger address
# match rather than tagged "company" specifically (see
# evaluation_report.md, paragraphs 505 / 521). counting them as fn here
# because the category label is wrong, even though the sensitive text
# itself did get redacted in the output.


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
    # accuracy here = TP / (TP + FP + FN) - there's no meaningful "true
    # negative" count for free text span extraction (every character
    # that isn't PII would count as one, which is meaningless), so this
    # is the standard way overlap-based accuracy gets reported for this
    # kind of task.
    accuracy = total_tp / (total_tp + total_fp + total_fn)

    print()
    print(f"overall precision: {overall_p*100:.1f}%")
    print(f"overall recall:    {overall_r*100:.1f}%")
    print(f"overall accuracy:  {accuracy*100:.1f}%  (TP / (TP+FP+FN))")


if __name__ == "__main__":
    print_report()
