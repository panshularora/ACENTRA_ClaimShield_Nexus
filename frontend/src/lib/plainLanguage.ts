/** Plain SIU wording for scores, findings, and the evidence drawer. */

export const SOURCE_PLAIN: Record<string, string> = {
  claim: "Paid claim header (who billed, which member, when it was paid)",
  claim_line: "Each service on a paid claim (code, units, dollars, date)",
  member: "Member file (including date of death when it is on record)",
  provider: "Provider enrollment (specialty, type, location)",
  eligibility_span: "Coverage dates",
  evv_visit: "Home-visit check-in records",
  inpatient_stay: "Hospital admit and discharge dates",
  rx_fill: "Pharmacy fills",
  exclusion_record: "Exclusion list (matched on NPI and name)",
  referral: "Who referred whom",
  ownership_link: "Who owns which NPI",
  owner: "Owner names on file",
  contact_point: "Shared phone, email, or bank details",
  location: "Practice address",
  investigation: "Earlier SIU outcomes on this provider",
};

export const FIELD_PLAIN: Record<string, string> = {
  code: "service code",
  dos: "date of service",
  member_id: "member",
  n_peers: "how many similar providers we compared",
  peer_median: "typical value for similar providers",
  robust_z: "how far this sits from similar providers",
  edge_kinds: "how the providers are linked",
  owner_id: "owner on file",
};

export interface FindingCopy {
  title: string;
  what: string;
  check: string;
  source: string;
}

export const FINDING_PLAIN: Record<string, FindingCopy> = {
  duplicate: {
    title: "Possible duplicate payment",
    what: "The same member, provider, service and date show up more than once.",
    check: "Open the claim lines and see if one is a correction or an extra payment.",
    source: "Paid claim lines",
  },
  ptp_pair: {
    title: "Two codes that usually should not both be paid",
    what: "A pair of services on the same day is on a list of codes that normally do not pay together.",
    check: "See whether a modifier or a second visit explains the pair.",
    source: "Paid claim lines",
  },
  unit_cap: {
    title: "Units above the usual cap",
    what: "Units on a line sit above the cap we use for this service.",
    check: "Confirm units, minutes, and whether the cap applies to this setting.",
    source: "Paid claim lines",
  },
  after_death: {
    title: "Service after date of death",
    what: "A paid line has a date of service after the member's date of death on file.",
    check: "Confirm the death date and the service date on the claim image.",
    source: "Paid claims and the member file",
  },
  daily_minutes_cap: {
    title: "More hours billed in a day than usually fit",
    what: "Minutes billed for one clinician-day add up above a plausible working day.",
    check: "Add the minutes across lines and confirm who rendered each one.",
    source: "Paid claim lines",
  },
  inpatient_overlap: {
    title: "Outpatient service during a hospital stay",
    what: "An outpatient or community service is dated while the member was admitted.",
    check: "Compare admit/discharge with the service date.",
    source: "Paid claims and hospital stays",
  },
  evv_missing: {
    title: "Home visit with no check-in record",
    what: "A home-health line was paid and we have no matching visit check-in.",
    check: "Ask for the visit record or a reason the check-in is missing.",
    source: "Paid claims and visit check-ins",
  },
  excluded_party: {
    title: "Possible match to the exclusion list",
    what: "The billing NPI and name agree with an exclusion record, and the service is after the exclusion date.",
    check: "Confirm NPI, legal name, and the exclusion date on the list.",
    source: "Paid claims, provider file, and the exclusion list",
  },
  excluded_owner: {
    title: "Owner may be on the exclusion list",
    what: "An owner tied to this NPI matches an exclusion record on name, date of birth and address.",
    check: "Confirm the ownership share and the exclusion record.",
    source: "Ownership records and the exclusion list",
  },
  doctor_shopping: {
    title: "Many prescribers and pharmacies for one member",
    what: "Opioid fills for one member come from several prescribers and pharmacies in a short window.",
    check: "Review the fill list and whether care is coordinated.",
    source: "Pharmacy fills",
  },
  sex_implausible: {
    title: "Service unusual for the sex on file",
    what: "The procedure is uncommon for the member's recorded sex. Bypass codes such as modifier KX were checked.",
    check: "Confirm sex on file and whether the code is correct.",
    source: "Paid claims and the member file",
  },
  pos_mismatch: {
    title: "Place of service does not match the visit type",
    what: "An office visit code was billed with a hospital or ambulance place of service.",
    check: "Confirm where the visit happened.",
    source: "Paid claim lines",
  },
  ambulance_overlap: {
    title: "Long ambulance trips on the same crew-day",
    what: "Several long recorded trips sit on one crew-day.",
    check: "Compare start and end times across the trips.",
    source: "Paid claim lines",
  },
  clone_billing: {
    title: "Many identical services on the same day",
    what: "The same service was billed across many members on one day, far above similar providers.",
    check: "Sample the lines and see if the dates and members are real.",
    source: "Paid claim lines",
  },
  stay_compression: {
    title: "Same-day high-level hospital stay",
    what: "A high-DRG facility claim has the same admit and discharge day.",
    check: "Confirm admit, discharge, and the DRG on the claim.",
    source: "Paid claims and hospital stays",
  },
  mileage_padding: {
    title: "Ambulance mileage above the urban norm",
    what: "Recorded mileage is above the cap we use for urban trips.",
    check: "Compare mileage with the pickup and drop-off.",
    source: "Paid claim lines",
  },
  identity_ring: {
    title: "Shared owner, tax ID, or contact across NPIs",
    what: "Several NPIs share an owner, tax ID, or contact. They are reviewed together.",
    check: "Map the shared links and which NPI billed the flagged lines.",
    source: "Provider, ownership, and contact records",
  },
  referral_monopoly: {
    title: "Referrals concentrated on one receiver",
    what: "A large share of referrals from this source go to one receiving NPI.",
    check: "See whether specialty or geography explains the concentration.",
    source: "Referral records and paid claims",
  },
  em_upcode_z: {
    title: "Highest-level office visits vs similar providers",
    what: "This provider bills the top office-visit level more often than similar providers.",
    check: "Sample charts for those visit levels. A difference from peers is a reason to look, not a conclusion.",
    source: "Paid claim lines compared with similar providers",
  },
  hh_iqr: {
    title: "Home-health volume above similar providers",
    what: "Visit volume sits well above similar home-health providers.",
    check: "Sample visits and match them to check-in records. Volume alone is not a finding.",
    source: "Paid claims compared with similar providers",
  },
  genetic_mill: {
    title: "High genetic-testing volume",
    what: "Genetic-test orders are high versus similar providers.",
    check: "Sample orders for medical necessity documentation. Volume is a reason to look.",
    source: "Paid claims compared with similar providers",
  },
};

export function findingCopy(kind: string | undefined, fallbackTitle: string): FindingCopy {
  if (kind && FINDING_PLAIN[kind]) return FINDING_PLAIN[kind];
  return {
    title: fallbackTitle,
    what: "A paid-claim check flagged this pattern. A person still has to review it.",
    check: "Open the supporting claim lines and see whether a simple explanation fits.",
    source: "Paid claims",
  };
}

export function sourcePlain(table: string, role?: string): string {
  return SOURCE_PLAIN[table] ?? role ?? table.replaceAll("_", " ");
}

export function fieldPlain(field: string): string {
  return FIELD_PLAIN[field] ?? field.replaceAll("_", " ");
}

export function kindTitle(kind: string): string {
  switch (kind) {
    case "alert":
      return "What we noticed";
    case "line":
      return "One paid claim line";
    case "claim":
      return "A paid claim";
    case "provider":
      return "Provider on this case";
    case "node":
      return "Linked party";
    case "edge":
      return "How two parties are linked";
    case "metric":
      return "Case scores";
    case "precedent":
      return "Earlier similar case";
    default:
      return "Evidence";
  }
}
