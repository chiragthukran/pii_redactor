"""
spaCy's NER tags things as PERSON / ORG pretty aggressively, and this
document is full of legal/regulatory terms that get caught by mistake -
things like "Companies Act", "SEBI", "RoC" etc. These are not personal
or company info, they are just legal/statutory references, so we filter
them out here.

This list was built by running the NER pass once, looking at what got
flagged, and manually going through the output to see what is obviously
not real PII. This is exactly the kind of thing the assignment wants us
to be explicit about - it's a manual, judgement based step, not
something a regex or model figures out on its own.
"""

ORG_STOPLIST = {
    "sebi", "sebi icdr regulations", "companies act", "companies act, 2013",
    "companies act, 1956", "roc", "registrar of companies", "rbi",
    "reserve bank of india", "scra", "scrr", "depositories act",
    "income tax act", "fema", "sebi act", "bse", "nse", "cdsl", "nsdl",
    "sebi listing regulations", "insolvency and bankruptcy code",
    "board of directors", "our board", "our company", "the company",
    "general information document", "sebi merchant bankers regulations",
    "prevention of money laundering act", "competition act",
    "companies (amendment) act", "registered office", "corporate office",
    "registered and corporate office", "book running lead managers",
    "the book running lead managers", "anchor investors",
    # added after running on the actual document and checking the most
    # frequent ORG hits - these are all capitalized "defined terms" that
    # RHPs use constantly (Company, Board, Offer etc get capitalized
    # and treated as proper nouns throughout this style of document,
    # spacy has no way to know these are defined terms and not real
    # company names). listing the ones actually seen in this document
    # rather than guessing at a generic list.
    "company", "board", "offer", "prospectus", "shareholders",
    "promoters", "promoter group", "promoter selling shareholders",
    "the promoter selling shareholders", "the promoter group",
    "this red herring prospectus", "the draft red herring prospectus",
    "the care report", "care report", "the restated financial statements",
    "restated financial statements", "results of operations",
  "registrar", "the registrar of companies", "ind as", "statutory auditors",
    "the period/ fiscals", "cin", "group companies", "syndicate", "bidders",
    "non-institutional investors", "proposed capital expenditure",
    "life insurance companies and pension funds", "the upi mechanism",
    "upi", "registered brokers", "supa facility", "ksh",
    "the companies act", "risk factors", "mutual funds", "offer structure",
    "our management", "bid amount", "indian rupees", "the power sector",
    "the last one year", "a year", "5th floor",
    "outstanding litigation and material developments",
    "the anchor investor portion",
}

# a real company name in this kind of document almost always ends with
# one of these - used as a positive signal, not a filter, see
# ner_detectors.py for how it's combined with the stoplist above.
COMPANY_SUFFIXES = (
    "limited", "ltd", "ltd.", "llp", "inc", "inc.", "corporation", "corp",
    "bank", "co", "co.", "pvt", "pvt.", "private limited", "associates",
    "partners", "& co", "and co", "research", "consultants", "llc",
)

# words that on their own are common legal/document terms, not names -
# spacy sometimes tags these as PERSON when they show up capitalized at
# the start of a defined-term sentence.
PERSON_STOPLIST = {
    "the offer", "the company", "our company", "the board", "our board",
    "annexure", "schedule", "form", "chapter",
}
