"""
corpus_spec.py — SINGLE SOURCE OF TRUTH for the synthetic MRPL demo corpus.

Every generated document reads its facts from this file. That is deliberate:
it means tag numbers, dates, readings and document IDs are *consistent across
all 12 documents*, which is what makes multi-hop questions work in the demo
("this pump is vibrating -> what's the procedure -> has it happened before ->
do we have the spare?").

Everything here is FABRICATED. It is modelled on real refinery document
formats but contains no actual MRPL data. Say this openly to judges.
"""

from datetime import date

# ---------------------------------------------------------------------------
# Plant / unit identity
# ---------------------------------------------------------------------------
PLANT = {
    "company": "Mangalore Refinery and Petrochemicals Limited",
    "short": "MRPL",
    "site": "Katipalla, Mangaluru, Karnataka",
    "unit_code": "CDU-2",
    "unit_name": "Crude Distillation Unit - 2",
    "capacity": "3.0 MMTPA",
    "doc_class": "CONFIDENTIAL - INTERNAL USE ONLY",
    "synthetic_notice": (
        "SYNTHETIC DOCUMENT - generated for SIH26117 prototype evaluation. "
        "Not an actual MRPL record."
    ),
}

# ---------------------------------------------------------------------------
# People (fictional)
# ---------------------------------------------------------------------------
PEOPLE = {
    "shift_incharge": "R. Kulkarni",
    "rot_eng": "S. Pai",
    "dgm_ops": "A. Fernandes",
    "safety_officer": "N. Bhat",
    "panel_op": "M. Shetty",
    "planner": "K. Rao",
    "reliability": "P. D'Souza",
    "insp_eng": "V. Nayak",
}

# ---------------------------------------------------------------------------
# Equipment register
# ---------------------------------------------------------------------------
EQUIPMENT = [
    {"tag": "P-2104A", "desc": "CDU-2 Column Bottoms (RCO) Pump - A",
     "type": "Centrifugal, API 610 BB2", "driver_kw": 250, "service_temp_c": 345,
     "status": "Standby"},
    {"tag": "P-2104B", "desc": "CDU-2 Column Bottoms (RCO) Pump - B",
     "type": "Centrifugal, API 610 BB2", "driver_kw": 250, "service_temp_c": 345,
     "status": "Running"},
    {"tag": "P-2101A", "desc": "CDU-2 Crude Charge Pump - A",
     "type": "Centrifugal, API 610 BB2", "driver_kw": 400, "service_temp_c": 120,
     "status": "Running"},
    {"tag": "P-2101B", "desc": "CDU-2 Crude Charge Pump - B",
     "type": "Centrifugal, API 610 BB2", "driver_kw": 400, "service_temp_c": 120,
     "status": "Standby"},
    {"tag": "P-2107A", "desc": "CDU-2 Kerosene Product Pump - A",
     "type": "Centrifugal, API 610 OH2", "driver_kw": 75, "service_temp_c": 190,
     "status": "Running"},
    {"tag": "C-2101", "desc": "CDU-2 Atmospheric Distillation Column",
     "type": "Trayed column, 42 trays", "driver_kw": 0, "service_temp_c": 355,
     "status": "In service"},
    {"tag": "F-2101", "desc": "CDU-2 Crude Charge Heater",
     "type": "Fired heater, 4 pass", "driver_kw": 0, "service_temp_c": 370,
     "status": "In service"},
    {"tag": "E-2107", "desc": "CDU-2 Crude / RCO Heat Exchanger",
     "type": "Shell & tube, AES", "driver_kw": 0, "service_temp_c": 340,
     "status": "In service"},
    {"tag": "V-2103", "desc": "CDU-2 Naphtha Reflux Drum",
     "type": "Horizontal vessel", "driver_kw": 0, "service_temp_c": 95,
     "status": "In service"},
    {"tag": "PSV-2141", "desc": "Relief valve, P-2104 discharge header",
     "type": "Conventional spring, 1.5J2", "driver_kw": 0, "service_temp_c": 345,
     "status": "In service"},
]

# ---------------------------------------------------------------------------
# Vibration limits (ISO 10816-3 style, Group 1 rigid mounting)
# ---------------------------------------------------------------------------
VIB_LIMITS = {
    "normal_max_mm_s": 4.5,
    "alert_mm_s": 7.1,
    "trip_mm_s": 11.0,
    "standard": "ISO 10816-3, Group 1, rigid mounting",
    "bearing_temp_alert_c": 85,
    "bearing_temp_trip_c": 95,
}

# ---------------------------------------------------------------------------
# THE SPINE OF THE STORY: P-2104B degrades through 2026 and fails on 29 Aug.
# vibration overall velocity, mm/s RMS, monthly reading, DE bearing horizontal
# ---------------------------------------------------------------------------
VIB_READINGS = {
    # tag: [(month, vib_mm_s, bearing_temp_c), ...]
    "P-2104B": [
        ("2026-01", 3.9, 68), ("2026-02", 4.0, 69), ("2026-03", 4.1, 70),
        ("2026-04", 4.6, 72), ("2026-05", 5.2, 75), ("2026-06", 6.4, 79),
        ("2026-07", 7.8, 86), ("2026-08", 9.6, 91),
    ],
    "P-2104A": [
        ("2026-01", 2.8, 61), ("2026-02", 2.7, 60), ("2026-03", 2.9, 62),
        ("2026-04", 2.8, 61), ("2026-05", 3.0, 63), ("2026-06", 2.9, 62),
        ("2026-07", 3.1, 64), ("2026-08", 3.0, 63),
    ],
    "P-2101A": [
        ("2026-01", 3.2, 58), ("2026-02", 3.3, 59), ("2026-03", 3.1, 58),
        ("2026-04", 3.4, 60), ("2026-05", 3.5, 61), ("2026-06", 3.3, 60),
        ("2026-07", 3.6, 62), ("2026-08", 3.8, 64),
    ],
    "P-2101B": [
        ("2026-01", 2.5, 55), ("2026-02", 2.6, 56), ("2026-03", 2.4, 55),
        ("2026-04", 2.6, 56), ("2026-05", 2.7, 57), ("2026-06", 2.5, 56),
        ("2026-07", 2.6, 57), ("2026-08", 2.5, 56),
    ],
    "P-2107A": [
        ("2026-01", 4.0, 66), ("2026-02", 4.2, 67), ("2026-03", 4.1, 66),
        ("2026-04", 4.3, 68), ("2026-05", 4.4, 69), ("2026-06", 4.2, 68),
        ("2026-07", 4.5, 70), ("2026-08", 4.6, 71),
    ],
}

# ---------------------------------------------------------------------------
# Documents metadata (drives filenames + citation strings)
# ---------------------------------------------------------------------------
DOCS = {
    "sop": {"id": "SOP-CDU2-014", "rev": "Rev 4", "effective": "2026-02-15",
            "title": "Pump Changeover - Hot Standby, Column Bottoms Service",
            "owner": PEOPLE["dgm_ops"], "next_review": "2028-02-14"},
    "incident": {"id": "INC-2026-0042", "date": "2026-08-29",
                 "title": "Mechanical Seal Failure and Hydrocarbon Release, P-2104B",
                 "severity": "Category 3 - Process Safety Event (Tier 2)"},
    "moc": {"id": "MOC-2026-0087", "raised": "2026-09-01",
            "title": "Upgrade of Mechanical Seal Arrangement, P-2104A/B",
            "status": "Pending Technical Review",
            "target_completion": "2026-10-15"},
    "hazop": {"id": "HAZOP-CDU2-2024", "node": "Node 7",
              "title": "Column Bottoms Circuit - Action Tracking Register",
              "revalidation_due": "2029-06-30"},
    "circular": {"id": "SC-2026-11", "issued": "2026-09-01",
                 "title": "Restriction on Hot Work - CDU-2 Column Bottoms Circuit",
                 "valid_to": "2026-11-30"},
    "ops": {"id": "OPS-MR-2026-08", "period": "August 2026",
            "title": "CDU-2 Monthly Operations Performance Report"},
    "vib": {"id": "VIB-CDU2-2026",
            "title": "CDU-2 Rotating Equipment Vibration and Bearing Temperature Log"},
    "wo": {"id": "WO-HIST-CDU2", "title": "CDU-2 Work Order History 2025-2026"},
    "spares": {"id": "SPR-ROT-001",
               "title": "Rotating Equipment Critical Spares Inventory"},
    "training": {"id": "TRN-CDU2-MATRIX",
                 "title": "CDU-2 Operator Competency and Certification Matrix"},
    "std": {"id": "ENG-STD-SUMM-119",
            "title": "Internal Engineering Summary - Hot Service Pump Requirements"},
    "handover": {"id": "SHL-2026-08-27", "date": "2026-08-27",
                 "title": "CDU-2 Shift Handover Log - Night Shift"},
    "pid": {"id": "PID-CDU2-003",
            "title": "CDU-2 Column Bottoms Circuit - Simplified Flow Schematic"},
}

# ---------------------------------------------------------------------------
# Incident detail
# ---------------------------------------------------------------------------
INCIDENT = {
    "occurred": "2026-08-29 03:40 hrs",
    "reported": "2026-08-29 03:52 hrs",
    "location": "CDU-2, Grade level, Pump house bay 3",
    "equipment": "P-2104B",
    "release_qty": "Approximately 40 litres of Reduced Crude Oil (RCO)",
    "release_temp": "341 degC",
    "injuries": "Nil",
    "fire": "Nil. Area gas tested and found safe at 04:15 hrs.",
    "production_impact": (
        "Unit throughput reduced by 12% for 6 hours 20 minutes to permit "
        "changeover to P-2104A. Estimated loss 1,840 MT of crude processed."
    ),
    "immediate_cause": (
        "Failure of the inboard mechanical seal (single seal, API 682 "
        "Category 1, Arrangement 1) on P-2104B, resulting in loss of "
        "containment at the seal chamber."
    ),
    "five_why": [
        ("Why did RCO release at the pump?",
         "The inboard mechanical seal faces lost contact and the seal chamber "
         "leaked to atmosphere."),
        ("Why did the seal faces lose contact?",
         "Excessive shaft dynamic movement caused the flexible face to lift "
         "off the seat intermittently."),
        ("Why was shaft movement excessive?",
         "Pump-to-driver coupling alignment had drifted to 0.19 mm parallel "
         "offset against a specification of 0.05 mm maximum."),
        ("Why was the misalignment not corrected?",
         "Overall vibration crossed the 7.1 mm/s alert limit in July 2026 but "
         "no corrective work order was raised; the reading was recorded and "
         "signed off as 'monitor'."),
        ("Why was no work order raised on an alert-level reading?",
         "The vibration log has no automatic escalation rule, and the "
         "monthly reliability review for July 2026 was deferred. The seal "
         "flush (API Plan 52) reservoir was also below minimum level, which "
         "was not on any routine check sheet."),
    ],
    "root_causes": [
        "Systemic: no mandatory escalation from an alert-level vibration "
        "reading to a corrective work order.",
        "Systemic: API Plan 52 seal pot level not included in any operator "
        "or technician routine check sheet.",
        "Design: single unpressurised seal (Category 1 / Arrangement 1) is "
        "marginal for 345 degC RCO service; dual pressurised arrangement is "
        "the appropriate selection.",
        "Human factors: the Shift In-Charge on duty held a lapsed 'Pump "
        "Changeover - Hot Standby' competency certification (expired "
        "2026-07-31), which extended the changeover duration.",
    ],
    "capa": [
        ("CAPA-0042-1",
         "Raise a Management of Change to upgrade P-2104A/B to API 682 "
         "Category 2, Arrangement 3 dual pressurised seals with API Plan 53B "
         "barrier fluid system.", PEOPLE["rot_eng"], "2026-09-05", "Complete",
         "Raised as MOC-2026-0087 on 2026-09-01."),
        ("CAPA-0042-2",
         "Amend SOP-CDU2-014 to require laser alignment check with 0.05 mm "
         "parallel offset tolerance recorded before returning any bottoms "
         "pump to service.", PEOPLE["dgm_ops"], "2026-09-20", "In Progress",
         "Draft Rev 5 under review."),
        ("CAPA-0042-3",
         "Add API Plan 52 / 53B seal pot level to the operator shift round "
         "check sheet for all CDU-2 hot service pumps.", PEOPLE["panel_op"],
         "2026-09-12", "In Progress", ""),
        ("CAPA-0042-4",
         "Configure a mandatory escalation rule: any overall vibration "
         "reading at or above 7.1 mm/s auto-generates a corrective work "
         "order within 24 hours.", PEOPLE["reliability"], "2026-10-01",
         "Not Started", ""),
        ("CAPA-0042-5",
         "Re-certify all CDU-2 shift in-charges on Pump Changeover - Hot "
         "Standby and block roster assignment on lapsed certification.",
         PEOPLE["dgm_ops"], "2026-09-30", "In Progress",
         "2 of 6 personnel currently lapsed."),
    ],
}

# ---------------------------------------------------------------------------
# MOC detail
# ---------------------------------------------------------------------------
MOC = {
    "change_type": "Permanent - Engineering / Hardware",
    "risk_rank": "Medium",
    "driver": (
        "Corrective action CAPA-0042-1 arising from incident INC-2026-0042 "
        "dated 2026-08-29."
    ),
    "existing": (
        "API 682 Category 1, Arrangement 1 (single unpressurised) cartridge "
        "seal with API Plan 52 external reservoir. Seal kit part SK-682-2104."
    ),
    "proposed": (
        "API 682 Category 2, Arrangement 3 (dual pressurised) cartridge seal "
        "with API Plan 53B bladder accumulator barrier fluid system. Seal kit "
        "part SK-682-2104-A3."
    ),
    "justification": [
        "RCO service at 345 degC with a flash point below the operating "
        "temperature; a leak path to atmosphere is a Tier 2 process safety "
        "risk.",
        "Arrangement 3 contains any inboard face failure within the barrier "
        "fluid, converting a loss of containment into an alarm.",
        "Plan 53B removes the operator-dependent reservoir top-up that was "
        "a contributing factor in INC-2026-0042.",
    ],
    "impacts": [
        ("Process", "No change to process conditions or unit yields."),
        ("Piping", "Removal of Plan 52 reservoir piping; new 53B accumulator "
                   "skid, 0.9 m x 0.6 m footprint, at grade adjacent to pump."),
        ("Electrical", "New level and pressure transmitters, 2 x 4-20 mA "
                       "loops to DCS. Two new DCS alarm points required."),
        ("SOP", "SOP-CDU2-014 requires revision (Rev 5) for barrier fluid "
                "pre-start checks."),
        ("Training", "2 hour refresher for all CDU-2 shift personnel before "
                     "commissioning."),
        ("Cost", "Estimated INR 34.6 lakh for both pumps including spares."),
    ],
    "approvals": [
        ("Originator", PEOPLE["rot_eng"], "2026-09-01", "Signed"),
        ("Reviewer - Process", PEOPLE["reliability"], "2026-09-02", "Signed"),
        ("Reviewer - Safety (HAZOP screening)", PEOPLE["safety_officer"],
         "2026-09-03", "Signed with comment"),
        ("Reviewer - Inspection", PEOPLE["insp_eng"], "", "Pending"),
        ("Approver - DGM Operations", PEOPLE["dgm_ops"], "", "Pending"),
    ],
    "safety_comment": (
        "Concur with the upgrade. Note that Safety Circular SC-2026-11 "
        "restricts hot work in this area until 2026-11-30; the accumulator "
        "skid tie-in must therefore be scheduled inside the CDU-2 planned "
        "shutdown window or a separate deviation must be approved."
    ),
    "blocker": (
        "Long lead item: seal kit SK-682-2104-A3 shows zero stock against a "
        "minimum of 2. Vendor lead time is 45 days. See SPR-ROT-001."
    ),
}

# ---------------------------------------------------------------------------
# HAZOP Node 7 actions  (id, deviation, cause, consequence, safeguard,
#                        recommendation, owner, due, status)
# ---------------------------------------------------------------------------
HAZOP_ACTIONS = [
    ("H7-01", "More Flow", "Control valve FCV-2141 fails open",
     "Overload of downstream E-2107, tube vibration",
     "Flow high alarm FAH-2141 at DCS",
     "Confirm FCV-2141 fail-safe position on next overhaul",
     PEOPLE["insp_eng"], "2025-11-30", "Closed"),
    ("H7-02", "No Flow", "Both P-2104A and P-2104B unavailable",
     "Column bottoms level high, potential carryover to C-2101 flash zone",
     "Level high-high trip LSHH-2101 trips F-2101",
     "Verify LSHH-2101 trip test frequency is 6 monthly, not annual",
     PEOPLE["reliability"], "2026-03-31", "Closed"),
    ("H7-03", "High Pressure", "Blocked discharge with pump running",
     "Overpressure of discharge header above design 24 kg/cm2g",
     "PSV-2141 on discharge header",
     "Re-rate PSV-2141: relief load recalculation shows required capacity "
     "exceeds installed capacity by an estimated 8%",
     PEOPLE["insp_eng"], "2026-06-30", "OVERDUE"),
    ("H7-04", "Loss of Containment", "Mechanical seal failure in hot RCO "
     "service", "Hydrocarbon release at grade, potential auto-ignition",
     "Area gas detectors GD-2104-1/2, fire water monitor coverage",
     "Review seal selection against API 682 for services above 300 degC",
     PEOPLE["rot_eng"], "2026-09-30", "In Progress"),
    ("H7-05", "High Temperature", "E-2107 bypass valve passing",
     "RCO to storage above 150 degC, tank blanketing concern",
     "Temperature high alarm TAH-2107",
     "Include E-2107 bypass valve in the passing-valve survey scope",
     PEOPLE["planner"], "2026-12-31", "Not Started"),
    ("H7-06", "Reverse Flow", "Non-return valve NRV-2104B fails to seat",
     "Reverse rotation of standby pump, coupling damage",
     "NRV-2104A/B, discharge isolation procedure in SOP-CDU2-014",
     "Add NRV-2104A/B to the 4 yearly strip-and-inspect register",
     PEOPLE["insp_eng"], "2027-03-31", "Not Started"),
]

# ---------------------------------------------------------------------------
# Spares inventory (part, desc, uom, on_hand, min, max, lead_days, vendor,
#                   unit_cost_inr, criticality, applies_to)
# ---------------------------------------------------------------------------
SPARES = [
    ("SK-682-2104", "Cartridge mech seal kit, API 682 Cat 1 Arr 1, 65 mm shaft",
     "Set", 1, 2, 4, 45, "Flowserve India Pvt Ltd", 412000, "A", "P-2104A/B"),
    ("SK-682-2104-A3", "Cartridge mech seal kit, API 682 Cat 2 Arr 3 dual "
     "pressurised, 65 mm shaft", "Set", 0, 2, 4, 45,
     "Flowserve India Pvt Ltd", 786000, "A", "P-2104A/B"),
    ("ACC-53B-09", "Bladder accumulator, Plan 53B, 8 litre, 40 bar",
     "No", 0, 1, 2, 60, "Hydac India", 293000, "A", "P-2104A/B"),
    ("BRG-7314-BECBM", "Angular contact thrust bearing pair 7314 BECBM",
     "Pair", 3, 2, 6, 21, "SKF India", 48500, "A", "P-2104A/B"),
    ("CPL-RFLEX-250", "Disc pack flexible coupling element, 250 kW class",
     "No", 2, 2, 4, 30, "Rathi Couplings", 61200, "B", "P-2104A/B"),
    ("GSK-SPW-6-300", "Spiral wound gasket, 6 in, CL300, SS316/graphite",
     "No", 24, 12, 40, 14, "Champion Seals", 1850, "C", "CDU-2 general"),
    ("SK-682-2101", "Cartridge mech seal kit, API 682 Cat 2 Arr 2, 80 mm shaft",
     "Set", 2, 2, 4, 45, "Flowserve India Pvt Ltd", 528000, "A", "P-2101A/B"),
    ("BRG-6316-C3", "Deep groove ball bearing 6316 C3", "No", 6, 4, 10, 14,
     "SKF India", 12400, "B", "CDU-2 general"),
    ("PSV-TRIM-1.5J2", "PSV trim kit, 1.5J2, nozzle and disc",
     "Set", 1, 1, 2, 90, "Anderson Greenwood", 214000, "A", "PSV-2141"),
    ("OIL-ISO-VG68", "Turbine oil ISO VG 68, 210 litre barrel", "Barrel",
     5, 3, 8, 7, "Indian Oil Corporation", 38900, "C", "CDU-2 general"),
]

# ---------------------------------------------------------------------------
# Work order history (wo, tag, date, type, description, downtime_hr,
#                     labour_hr, cost_inr, status)
# ---------------------------------------------------------------------------
WORK_ORDERS = [
    ("WO-25-11420", "P-2104B", "2025-04-18", "Preventive",
     "Annual overhaul: bearings replaced, seal refurbished, alignment done",
     36.0, 96, 684000, "Closed"),
    ("WO-25-12877", "P-2104A", "2025-06-02", "Preventive",
     "Annual overhaul: bearings replaced, coupling element replaced",
     32.0, 88, 612000, "Closed"),
    ("WO-25-14903", "P-2104B", "2025-09-11", "Corrective",
     "Seal weeping observed, Plan 52 reservoir topped up, seal faces lapped",
     8.0, 24, 96000, "Closed"),
    ("WO-25-16044", "E-2107", "2025-11-20", "Preventive",
     "Shell side cleaning during mini shutdown", 48.0, 160, 940000, "Closed"),
    ("WO-26-10233", "P-2101A", "2026-02-14", "Corrective",
     "High bearing temperature, oil changed and cooler cleaned",
     4.0, 12, 42000, "Closed"),
    ("WO-26-11876", "P-2104B", "2026-05-06", "Predictive",
     "Vibration analysis requested by reliability; report notes 1x running "
     "speed dominant, misalignment suspected. No corrective work executed.",
     0.0, 6, 18000, "Closed"),
    ("WO-26-13001", "PSV-2141", "2026-06-15", "Statutory",
     "PSV pop test and recertification; passed at set pressure 26.4 kg/cm2g",
     0.0, 8, 54000, "Closed"),
    ("WO-26-14550", "P-2107A", "2026-07-22", "Corrective",
     "Gland leak arrested, packing replaced", 6.0, 16, 38000, "Closed"),
    ("WO-26-15118", "P-2104B", "2026-08-29", "Breakdown",
     "Emergency: inboard mechanical seal failure, RCO release. Pump isolated, "
     "changeover to P-2104A. Seal kit SK-682-2104 consumed from stock.",
     14.5, 72, 1246000, "Closed"),
    ("WO-26-15203", "P-2104B", "2026-09-02", "Corrective",
     "Laser alignment correction and baseline vibration signature after seal "
     "replacement", 0.0, 18, 74000, "In Progress"),
    ("WO-26-15240", "P-2104A", "2026-09-02", "Predictive",
     "Baseline vibration signature captured post changeover, pump now lead",
     0.0, 4, 12000, "Closed"),
]

# ---------------------------------------------------------------------------
# Training / competency matrix
# (name, role, comp_pump_changeover, comp_hot_work, comp_confined_space,
#  comp_dcs, last_refresher)
# Dates are expiry dates; "-" means not required for the role.
# ---------------------------------------------------------------------------
TRAINING = [
    (PEOPLE["shift_incharge"], "Shift In-Charge", "2026-07-31", "2027-03-15",
     "2027-01-20", "2027-06-30", "2024-08-01"),
    (PEOPLE["panel_op"], "Panel Operator", "2027-05-12", "2027-05-12",
     "2026-11-30", "2027-05-12", "2025-05-13"),
    ("D. Prabhu", "Shift In-Charge", "2026-06-30", "2027-02-28",
     "2026-12-15", "2027-04-30", "2024-07-01"),
    ("G. Hegde", "Field Operator", "2027-08-20", "2027-08-20",
     "2027-08-20", "-", "2025-08-21"),
    ("T. Moily", "Field Operator", "2027-11-05", "2027-11-05",
     "2027-02-14", "-", "2025-11-06"),
    (PEOPLE["rot_eng"], "Rotating Equipment Engineer", "2028-01-15",
     "2027-09-30", "2027-09-30", "-", "2026-01-16"),
    ("B. Amin", "Shift In-Charge", "2027-04-18", "2027-04-18",
     "2027-04-18", "2027-04-18", "2025-04-19"),
    ("L. Karkera", "Field Operator", "2027-06-22", "2027-06-22",
     "2026-10-31", "-", "2025-06-23"),
]
TRAINING_AS_OF = "2026-09-03"

# ---------------------------------------------------------------------------
# Monthly ops report figures - August 2026
# ---------------------------------------------------------------------------
OPS_REPORT = {
    "period": "August 2026",
    "kpis": [
        # (parameter, unit, target, actual, previous_month)
        ("Crude processed", "MT", "248,000", "241,300", "246,900"),
        ("Capacity utilisation", "%", "100.0", "97.3", "99.5"),
        ("On-stream factor", "%", "99.0", "96.2", "99.1"),
        ("Specific energy consumption", "MJ/MT", "60.0", "62.4", "60.8"),
        ("Fuel and loss", "% on crude", "2.10", "2.28", "2.14"),
        ("Flaring", "% on crude", "0.25", "0.31", "0.24"),
        ("Naphtha yield", "% wt", "14.2", "13.8", "14.1"),
        ("Kerosene / ATF yield", "% wt", "12.0", "11.6", "12.1"),
        ("Diesel yield", "% wt", "39.5", "38.7", "39.4"),
        ("RCO to secondary units", "% wt", "33.0", "34.5", "33.1"),
        ("Steam consumption", "MT/MT crude", "0.086", "0.091", "0.087"),
        ("Cooling water dT", "degC", "9.0", "9.8", "9.1"),
    ],
    "downtime": [
        ("2026-08-29", "P-2104B mechanical seal failure, rate cut to permit "
         "changeover to P-2104A", 6.33, "Equipment"),
        ("2026-08-11", "F-2101 pass 3 burner tip choke, rate cut", 2.50,
         "Equipment"),
        ("2026-08-04", "Crude tank changeover, off-spec slop routing", 1.25,
         "Operational"),
    ],
    "narrative": (
        "CDU-2 processed 241,300 MT of crude against a monthly plan of "
        "248,000 MT, a shortfall of 2.7%. The single largest contributor was "
        "the unplanned rate reduction on 2026-08-29 arising from the "
        "mechanical seal failure on P-2104B (refer INC-2026-0042), which "
        "accounted for an estimated 1,840 MT of lost throughput.\n\n"
        "Specific energy consumption at 62.4 MJ/MT was 4.0% adverse to the "
        "target of 60.0 MJ/MT. The deterioration is attributed to reduced "
        "preheat train efficiency across E-2107, where the calculated fouling "
        "resistance has risen for the third consecutive month, and to "
        "operation at reduced throughput during the 29 August event. Flaring "
        "at 0.31% exceeded the 0.25% target, driven almost entirely by the "
        "same event.\n\n"
        "Distillate yields were marginally below target across the board, "
        "consistent with the lighter crude slate processed in the second half "
        "of the month and with the reduced column bottoms circulation during "
        "the changeover period. RCO to secondary units was correspondingly "
        "higher at 34.5% against a target of 33.0%.\n\n"
        "Reliability focus for September 2026 is the closure of overdue HAZOP "
        "Node 7 action H7-03 relating to PSV-2141 relief capacity, and "
        "progression of MOC-2026-0087 for the P-2104A/B seal upgrade."
    ),
}

# ---------------------------------------------------------------------------
# Safety circular
# ---------------------------------------------------------------------------
CIRCULAR = {
    "background": (
        "On 2026-08-29 a loss of containment of Reduced Crude Oil occurred at "
        "the P-2104B seal chamber in the CDU-2 column bottoms circuit "
        "(incident INC-2026-0042). The released material was at 341 degC, "
        "which is above its auto-ignition temperature under confinement. No "
        "ignition occurred and there were no injuries."
    ),
    "restrictions": [
        "All hot work within a 15 metre radius of the CDU-2 column bottoms "
        "circuit (equipment P-2104A, P-2104B, E-2107 and associated piping "
        "from C-2101 bottoms nozzle to the E-2107 outlet) is SUSPENDED with "
        "immediate effect.",
        "Hot work in this zone may only proceed on a deviation permit "
        "countersigned by the DGM Operations and the Chief Fire and Safety "
        "Officer, supported by a documented job specific risk assessment.",
        "Continuous gas monitoring by a dedicated fire watch is mandatory for "
        "any approved deviation, with readings logged every 15 minutes.",
        "Cold cutting, mechanical bolting and blind insertion methods are to "
        "be evaluated in preference to hot work for all work in this zone.",
        "Any tie-in work arising from MOC-2026-0087 is to be scheduled within "
        "the CDU-2 planned shutdown window unless a deviation permit is "
        "approved as above.",
    ],
    "validity": (
        "This circular is effective from 2026-09-01 and remains in force "
        "until 2026-11-30 or until the closure of CAPA-0042-1 and CAPA-0042-4 "
        "of INC-2026-0042, whichever is later."
    ),
}

# ---------------------------------------------------------------------------
# Shift handover log (the SCANNED document - forces the OCR path)
# ---------------------------------------------------------------------------
HANDOVER = {
    "date": "2026-08-27",
    "shift": "Night (22:00 - 06:00)",
    "outgoing": PEOPLE["shift_incharge"],
    "incoming": "D. Prabhu",
    "rows": [
        ("22:15", "Unit stable at 96% rate. C-2101 top temp 118 degC, "
                  "flash zone 352 degC."),
        ("23:40", "P-2104B - oil mist / weeping seen at seal area. Wiped and "
                  "cleaned. Plan 52 pot level LOW, approx 20%. Topped up "
                  "manually with 2 litre."),
        ("00:30", "P-2104B vibration checked with handheld: 9.4 mm/s DE "
                  "horizontal. Above alert. Informed panel and rotating "
                  "equipment engineer on phone."),
        ("01:10", "Advised by rotating eqpt engineer to continue monitoring "
                  "and keep P-2104A ready for hot standby changeover. No work "
                  "order raised in this shift."),
        ("02:45", "F-2101 pass 3 skin temp 618 degC, within limit. Soot blow "
                  "done."),
        ("04:20", "P-2104B seal area re-checked. Slight weeping continues. "
                  "Bearing temp 91 degC."),
        ("05:50", "Handover to day shift. FLAGGED: P-2104B seal condition and "
                  "high vibration. Recommend early changeover to P-2104A."),
    ],
    "notes": (
        "P-2104A confirmed on auto-start, suction and discharge lined up, "
        "warm-up line cracked open. Ready for changeover."
    ),
}

# ---------------------------------------------------------------------------
# Internal engineering standard summary (fabricated - not a real standard text)
# ---------------------------------------------------------------------------
STD_SUMMARY = {
    "scope": (
        "This internal summary consolidates MRPL engineering practice for "
        "centrifugal pumps in hydrocarbon service above 250 degC. It is an "
        "internally authored interpretation prepared for training use and "
        "does not reproduce the text of any external standard."
    ),
    "clauses": [
        ("4.1", "Seal selection", "Pumps handling flammable liquid above "
         "260 degC, or above the fluid auto-ignition temperature, shall use a "
         "dual seal arrangement. Arrangement 3 (dual pressurised) is the "
         "default selection; Arrangement 2 (dual unpressurised) requires "
         "documented justification."),
        ("4.2", "Seal support system", "Arrangement 3 seals shall be "
         "supported by a Plan 53B or Plan 53C barrier fluid system with "
         "level and pressure transmitted to the DCS. Manually replenished "
         "Plan 52 or Plan 53A reservoirs shall not be used as the sole "
         "protection on services above 260 degC."),
        ("4.3", "Alignment", "Shaft alignment shall be verified by laser "
         "method. Maximum permissible parallel offset is 0.05 mm and maximum "
         "angular deviation is 0.05 mm per 100 mm of coupling span, measured "
         "at operating temperature where hot alignment is specified."),
        ("5.1", "Condition monitoring", "Overall vibration velocity shall be "
         "trended monthly. A reading at or above 7.1 mm/s RMS constitutes an "
         "alert condition and shall generate a corrective work order within "
         "24 hours. A reading at or above 11.0 mm/s RMS requires the pump to "
         "be removed from service at the earliest safe opportunity."),
        ("5.2", "Bearing temperature", "Bearing metal or oil temperature "
         "shall alarm at 85 degC and trip at 95 degC for pumps of 150 kW and "
         "above."),
        ("6.1", "Spares holding", "Criticality A rotating equipment shall "
         "hold a minimum of two complete seal kits per pump pair on site. "
         "Stock below minimum shall be reported in the monthly reliability "
         "review."),
        ("6.2", "Standby availability", "Where a pump pair serves a "
         "continuous process duty, the standby unit shall be maintained "
         "warm, lined up and on auto-start at all times, and shall be test "
         "run for not less than 30 minutes every 14 days."),
    ],
}

# ---------------------------------------------------------------------------
# Golden evaluation set - drives scripts/eval_retrieval.py and the Trust tab.
# "must_cite" is matched against the source document id of retrieved chunks.
# "must_contain" are strings the correct answer should mention.
# ---------------------------------------------------------------------------
GOLDEN_QUESTIONS = [
    {
        "q": "What was the overall vibration reading on P-2104B in August 2026, "
             "and was it above the alert limit?",
        "must_cite": ["VIB-CDU2-2026"],
        "must_contain": ["9.6", "7.1"],
        "hops": 1,
    },
    {
        "q": "What was the root cause of the mechanical seal failure on P-2104B?",
        "must_cite": ["INC-2026-0042"],
        "must_contain": ["alignment", "0.19"],
        "hops": 1,
    },
    {
        "q": "What is the approved procedure to change over from P-2104B to "
             "P-2104A while CDU-2 is running?",
        "must_cite": ["SOP-CDU2-014"],
        "must_contain": ["SOP-CDU2-014", "warm"],
        "hops": 1,
    },
    {
        "q": "Do we have the seal kit in stock that MOC-2026-0087 needs?",
        "must_cite": ["SPR-ROT-001", "MOC-2026-0087"],
        "must_contain": ["SK-682-2104-A3", "45"],
        "hops": 2,
    },
    {
        "q": "Which CDU-2 personnel have a lapsed pump changeover certification?",
        "must_cite": ["TRN-CDU2-MATRIX"],
        "must_contain": ["Kulkarni", "Prabhu"],
        "hops": 1,
    },
    {
        "q": "Can we do hot work near the CDU-2 column bottoms circuit in "
             "September 2026?",
        "must_cite": ["SC-2026-11"],
        "must_contain": ["suspended", "deviation"],
        "hops": 1,
    },
    {
        "q": "Which HAZOP Node 7 actions are overdue?",
        "must_cite": ["HAZOP-CDU2-2024"],
        "must_contain": ["H7-03", "PSV-2141"],
        "hops": 1,
    },
    {
        "q": "What was CDU-2 specific energy consumption in August 2026 versus "
             "target?",
        "must_cite": ["OPS-MR-2026-08"],
        "must_contain": ["62.4", "60.0"],
        "hops": 1,
    },
    {
        "q": "What did the night shift handover log on 27 August 2026 record "
             "about P-2104B?",
        "must_cite": ["SHL-2026-08-27"],
        "must_contain": ["9.4", "Plan 52"],
        "hops": 1,
    },
    {
        "q": "What seal arrangement does MOC-2026-0087 propose and what is its "
             "approval status?",
        "must_cite": ["MOC-2026-0087"],
        "must_contain": ["Arrangement 3", "Pending"],
        "hops": 1,
    },
    {
        "q": "What does MRPL engineering practice require for vibration "
             "readings above the alert limit?",
        "must_cite": ["ENG-STD-SUMM-119"],
        "must_contain": ["24 hours", "work order"],
        "hops": 1,
    },
    {
        "q": "How much did the P-2104B breakdown work order cost and how much "
             "downtime did it cause?",
        "must_cite": ["WO-HIST-CDU2"],
        "must_contain": ["WO-26-15118", "14.5"],
        "hops": 1,
    },
    {
        "q": "P-2104B vibration has been rising all year. Was this ever flagged "
             "before the failure, and by whom?",
        "must_cite": ["SHL-2026-08-27", "WO-HIST-CDU2", "INC-2026-0042"],
        "must_contain": ["27 August", "monitor"],
        "hops": 3,
    },
    {
        "q": "The seal upgrade is approved in principle. What is actually "
             "blocking it from being executed?",
        "must_cite": ["SPR-ROT-001", "SC-2026-11", "MOC-2026-0087"],
        "must_contain": ["lead time", "hot work"],
        "hops": 3,
    },
    {
        "q": "Give me every document that mentions P-2104B.",
        "must_cite": ["INC-2026-0042", "VIB-CDU2-2026", "SOP-CDU2-014",
                      "WO-HIST-CDU2", "SHL-2026-08-27", "MOC-2026-0087"],
        "must_contain": ["P-2104B"],
        "hops": 1,
    },
]


def unit_header() -> str:
    """Common header line used on every generated document."""
    return f"{PLANT['company']} | {PLANT['site']} | {PLANT['unit_name']}"
