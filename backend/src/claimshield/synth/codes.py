"""Synthetic and HCPCS Level II codes. No CPT descriptors, no CPT code_system."""

from __future__ import annotations

CODE_SYSTEM_SYNTH = "SYNTH"
CODE_SYSTEM_HCPCS2 = "HCPCS2"
CODE_SYSTEM_NDC = "NDC-SYN"

EM_LEVELS = ["EM-EST-1", "EM-EST-2", "EM-EST-3", "EM-EST-4", "EM-EST-5"]
BH_TIMED = ["PSY-30", "PSY-45", "PSY-60"]
LAB_PANEL = "LAB-PNL-01"
LAB_COMPONENTS = ["LAB-CMP-03", "LAB-CMP-05"]
LAB_GENETIC = "LAB-GEN-01"
HOME_VISIT = "HH-VISIT"
ABA_HOUR = "ABA-60"
DME_CATH = "DME-CATH"
AMB_MILEAGE = "A0425"
AMB_ALS = "A0427"
POS_OFFICE = "11"
POS_HOME = "12"
POS_INPATIENT = "21"
POS_AMBULANCE = "41"

SPECIALTIES = {
    "professional": ["family_medicine", "internal_medicine", "cardiology", "orthopedics"],
    "facility": ["acute_hospital", "outpatient_hospital"],
    "pharmacy": ["retail_pharmacy"],
    "laboratory": ["clinical_lab"],
    "ambulance": ["ground_ambulance"],
    "behavioral_health": ["psychiatry", "aba_clinic", "sud_clinic"],
    "home_health": ["home_health_agency", "personal_care"],
    "dme": ["dme_supplier"],
}

SERVICE_LINES = list(SPECIALTIES)

UNIT_CAPS = {
    AMB_MILEAGE: 250,
    "PSY-60": 8,
    HOME_VISIT: 4,
    ABA_HOUR: 12,
}

PTP_PAIRS = [
    (LAB_PANEL, "LAB-CMP-03", 0),
    (LAB_PANEL, "LAB-CMP-05", 1),
    ("EM-EST-5", "EM-EST-3", 0),
]
