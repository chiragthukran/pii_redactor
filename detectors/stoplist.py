"""
spacy NER tags PERSON / ORG pretty aggressively. this document have a lot
of legal and regulatory words which get detected by mistake, like
"Companies Act", "SEBI", "RoC" etc.

these are not actual personal or company information, they are just
legal/statutory references, so we remove them here.

i made this list by running NER on the document, checking what was getting
flagged and then manually removing the things which were clearly not PII.
so this part is based on manual checking and judgement, model or regex
cant figure this out automatically.
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
    # added these after running the actual document and checking the
    # most common ORG matches. RHP documents use these words with capital
    # letters all the time, so spacy thinks they are proper names.
    # keeping only the ones which were actually seen in this document
    # instead of making a random generic list.
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

# real company names in this type of document usually have one of these
# words at the end. this is only used as a positive signal, not as a filter.
# check ner_detectors.py to see how this is used with the stoplist.
COMPANY_SUFFIXES = (
    "limited", "ltd", "ltd.", "llp", "inc", "inc.", "corporation", "corp",
    "bank", "co", "co.", "pvt", "pvt.", "private limited", "associates",
    "partners", "& co", "and co", "research", "consultants", "llc",
)

# these words are common legal/document terms, not actual names.
# spacy sometimes marks them as PERSON when they are capitalized at the
# beginning of a sentence or defined term, so removing them here.
PERSON_STOPLIST = {
    "the offer", "the company", "our company", "the board", "our board",
    "annexure", "schedule", "form", "chapter",
}