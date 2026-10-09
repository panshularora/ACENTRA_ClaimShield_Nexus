"""Plain SIU wording for briefs, gaps, and lineage — scores rank work; a person decides."""

from __future__ import annotations

FINDING: dict[str, dict[str, str]] = {
    "duplicate": {
        "title": "Possible duplicate payment",
        "what": "The same member, provider, service and date show up more than once.",
        "check": "Open the claim lines and see if one is a correction or an extra payment.",
    },
    "ptp_pair": {
        "title": "Two codes that usually should not both be paid",
        "what": "A pair of services on the same day is on a list of codes that normally do not pay together.",
        "check": "See whether a modifier or a second visit explains the pair.",
    },
    "unit_cap": {
        "title": "Units above the usual cap",
        "what": "Units on a line sit above the cap we use for this service.",
        "check": "Confirm units, minutes, and whether the cap applies to this setting.",
    },
    "after_death": {
        "title": "Service after date of death",
        "what": "A paid line has a date of service after the member's date of death on file.",
        "check": "Confirm the death date and the service date on the claim image.",
    },
    "daily_minutes_cap": {
        "title": "More hours billed in a day than usually fit",
        "what": "Minutes billed for one clinician-day add up above a plausible working day.",
        "check": "Add the minutes across lines and confirm who rendered each one.",
    },
    "inpatient_overlap": {
        "title": "Outpatient service during a hospital stay",
        "what": "An outpatient or community service is dated while the member was admitted.",
        "check": "Compare admit/discharge with the service date.",
    },
    "evv_missing": {
        "title": "Home visit with no check-in record",
        "what": "A home-health line was paid and we have no matching visit check-in.",
        "check": "Ask for the visit record or a reason the check-in is missing.",
    },
    "excluded_party": {
        "title": "Possible match to the exclusion list",
        "what": "The billing NPI and name agree with an exclusion record, and the service is after the exclusion date.",
        "check": "Confirm NPI, legal name, and the exclusion date on the list.",
    },
    "excluded_owner": {
        "title": "Owner may be on the exclusion list",
        "what": "An owner tied to this NPI matches an exclusion record on name, date of birth and address.",
        "check": "Confirm the ownership share and the exclusion record.",
    },
    "doctor_shopping": {
        "title": "Many prescribers and pharmacies for one member",
        "what": "Opioid fills for one member come from several prescribers and pharmacies in a short window.",
        "check": "Review the fill list and whether care is coordinated.",
    },
    "sex_implausible": {
        "title": "Service unusual for the sex on file",
        "what": "The procedure is uncommon for the member's recorded sex, with no supporting modifier.",
        "check": "Confirm sex on file and whether the code is correct.",
    },
    "pos_mismatch": {
        "title": "Place of service does not match the visit type",
        "what": "An office visit code was billed with a hospital or ambulance place of service.",
        "check": "Confirm where the visit happened.",
    },
    "ambulance_overlap": {
        "title": "Long ambulance trips on the same crew-day",
        "what": "Several long recorded trips sit on one crew-day.",
        "check": "Compare start and end times across the trips.",
    },
    "clone_billing": {
        "title": "Many identical services on the same day",
        "what": "The same service was billed across many members on one day, far above similar providers.",
        "check": "Sample the lines and see if the dates and members are real.",
    },
    "stay_compression": {
        "title": "Same-day high-level hospital stay",
        "what": "A high-level facility claim has the same admit and discharge day.",
        "check": "Confirm admit, discharge, and the stay code on the claim.",
    },
    "mileage_padding": {
        "title": "Ambulance mileage above the urban norm",
        "what": "Recorded mileage is above the cap we use for urban trips.",
        "check": "Compare mileage with the pickup and drop-off.",
    },
    "identity_ring": {
        "title": "Shared owner, tax ID, or contact across NPIs",
        "what": "Several NPIs share an owner, tax ID, or contact. They are reviewed together.",
        "check": "Map the shared links and which NPI billed the flagged lines.",
    },
    "referral_monopoly": {
        "title": "Referrals concentrated on one receiver",
        "what": "A large share of referrals from this source go to one receiving NPI.",
        "check": "See whether specialty or geography explains the concentration.",
    },
    "em_upcode_z": {
        "title": "Highest-level office visits vs similar providers",
        "what": "This provider bills the top office-visit level more often than similar providers.",
        "check": "Sample charts for those visit levels. A difference from peers is a reason to look.",
    },
    "hh_iqr": {
        "title": "Home-health volume above similar providers",
        "what": "Visit volume sits well above similar home-health providers.",
        "check": "Sample visits and match them to check-in records. Volume alone is not a finding.",
    },
    "genetic_mill": {
        "title": "High genetic-testing volume",
        "what": "Genetic-test orders are high versus similar providers.",
        "check": "Sample orders for medical necessity documentation. Volume is a reason to look.",
    },
}

GAP_BY_KIND: dict[str, str] = {
    "evv_missing": "Ask for the home-visit check-in record for those dates.",
    "after_death": "Confirm the date of death and that the service date is after it.",
    "excluded_party": "Confirm NPI, legal name, and the exclusion date on the list.",
    "duplicate": "Pull the original and any resubmitted claim images for the same member, provider, code and date.",
    "ptp_pair": (
        "Open the claim images and see if both codes were paid the same day, and whether a modifier explains it."
    ),
    "unit_cap": "Confirm billed units against the visit notes.",
    "inpatient_overlap": "Confirm hospital admit and discharge against the outpatient date of service.",
    "clone_billing": "Sample visit notes for that day and see if the visits look real.",
    "ambulance_overlap": "Ask for trip sheets with start and end times.",
    "sex_implausible": "Confirm the sex on file and whether the procedure code is right.",
    "daily_minutes_cap": "Add minutes across that clinician-day and confirm who rendered each one.",
    "doctor_shopping": "Review the fill list across prescribers and pharmacies.",
    "excluded_owner": "Confirm the ownership share and the exclusion record.",
    "em_upcode_z": "Sample charts for the highest office-visit levels.",
    "hh_iqr": "Sample visits and match them to check-in records.",
    "genetic_mill": "Sample genetic-test orders for medical necessity notes.",
}


def finding_copy(kind: str | None, fallback: str = "Flagged pattern") -> dict[str, str]:
    if kind and kind in FINDING:
        return FINDING[kind]
    return {
        "title": fallback.replace("_", " "),
        "what": "A check flagged this pattern on paid claims. A person still has to review it.",
        "check": "Open the supporting claim lines and see whether a simple explanation fits.",
    }


def kind_title(kind: str | None, fallback: str = "Flagged pattern") -> str:
    return finding_copy(kind, fallback)["title"]
