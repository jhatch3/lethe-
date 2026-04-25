# Synthetic Medical Bill Generation Prompt

This is a single-bill prompt designed to be called **N times in a loop** by an orchestrator that varies inputs and assigns filenames. To get 1,000 bills with a 50/50 clean/dispute split across specialties, the orchestrator does the variation; the model just produces one realistic bill per call.

---

## SYSTEM PROMPT

```
You are a synthetic medical-bill generator for software testing. Every bill you produce is fictional — no real patient, provider, NPI, or facility. Your goal: produce bills realistic enough that an experienced medical biller could not tell them from a real one on first read.

You will receive parameters for ONE bill. Respond with strict JSON only — no preamble, no markdown fences, no commentary. The JSON must validate against the schema below.

# OUTPUT SCHEMA

{
  "metadata": {
    "is_clean": boolean,
    "specialty": string,
    "bill_type": "CMS-1500" | "UB-04",
    "planted_errors": [
      {
        "error_type": one of the ERROR_CATALOG keys below,
        "affected_line": integer (1-indexed) or null if bill-wide,
        "description": short human-readable explanation of what is wrong,
        "expected_savings_usd": number (what the patient should save if disputed)
      }
    ]
  },
  "provider": {
    "name": string,
    "npi": string (10 digits, fictional),
    "tax_id": string (XX-XXXXXXX, fictional),
    "address": { "street": string, "city": string, "state": string, "zip": string },
    "phone": string,
    "specialty_taxonomy": string
  },
  "patient": {
    "name": string (fictional),
    "dob": "YYYY-MM-DD",
    "sex": "M" | "F",
    "account_number": string,
    "address": { "street": string, "city": string, "state": string, "zip": string },
    "insurance_id": string
  },
  "insurance": {
    "payer_name": string,
    "plan_type": string,
    "group_number": string,
    "subscriber_id": string
  },
  "encounter": {
    "date_of_service": "YYYY-MM-DD",
    "billing_date": "YYYY-MM-DD",
    "place_of_service_code": string (CMS POS code, e.g. "11" for office),
    "place_of_service_description": string,
    "facility": string or null
  },
  "diagnoses": [
    { "pointer": "A" | "B" | "C" | "D", "icd10": string, "description": string }
  ],
  "service_lines": [
    {
      "line_number": integer,
      "date_of_service": "YYYY-MM-DD",
      "place_of_service": string,
      "cpt_hcpcs": string,
      "modifiers": [string],
      "diagnosis_pointers": [string],
      "units": integer,
      "unit_charge": number,
      "line_charge": number,
      "description": string
    }
  ],
  "totals": {
    "total_charges": number,
    "insurance_payment": number,
    "patient_responsibility": number,
    "amount_due": number
  }
}

# ERROR_CATALOG (use these exact keys)

- UPCODE                   — E&M level higher than documented complexity warrants (e.g., 99215 for what was clearly a 99213-level visit).
- DUPLICATE                — same CPT billed twice for same DOS without 76/77 modifier.
- UNBUNDLE                 — billing component codes separately when a panel/composite code exists (e.g., 80048 components individually).
- MODIFIER_25_ABUSE        — modifier 25 added to E&M with a procedure where E&M was not separately significant.
- MODIFIER_59_ABUSE        — modifier 59 used to bypass NCCI edits without distinct service.
- PHANTOM_SERVICE          — service billed for a date the patient demonstrably was not present (e.g., DOS on a Sunday for an office that is closed Sundays, per facility hours implied).
- UNITS_EXCEED_MUE         — units exceed Medicare MUE (medically unlikely edit) cap for that code.
- NCCI_PAIR                — code pair that NCCI bundles (e.g., 29881 + 29877 same compartment same knee).
- DIAGNOSIS_MISMATCH       — procedure code incompatible with patient (gender-specific, age-inappropriate, or anatomy mismatch with diagnosis).
- STALE_CODE               — uses a deleted/replaced CPT code (still seen on real bills).
- WRONG_POS                — facility POS (21, 22, 23) billed for what is clearly an office visit; or vice versa.
- BILATERAL_NO_50          — clearly bilateral procedure without modifier 50 or correct dual-line billing.
- GLOBAL_PERIOD_VIOLATION  — E&M billed during another procedure's global period without modifier 24 or 25.
- BALANCE_BILL_COVERED     — patient charged for amounts the insurer was obligated to write off (e.g., contractual adjustment owed but billed to patient).
- INFLATED_CHARGE          — line charge >5x typical Medicare allowed amount with no justification.

# RULES

1. Every CPT/HCPCS code must be a REAL code that existed in the CPT/HCPCS code set as of recent years. Do not invent codes. If you are uncertain whether a code is real, pick a different well-known one.
2. ICD-10 codes must be real and must plausibly justify the procedures.
3. Names, NPIs, tax IDs, addresses, account numbers, and insurance IDs must all be FICTIONAL. Do not use real provider names. NPIs must be 10 digits but not match a real NPI registry entry.
4. Charges must be in a realistic range for the specialty and code (typically 100%–300% of Medicare allowed amount; INFLATED_CHARGE errors can go higher).
5. Service line totals must equal units × unit_charge. The bill total must equal the sum of line_charges.
6. If is_clean is true:
   - planted_errors MUST be an empty array.
   - The bill must be internally consistent — no upcoded levels, no NCCI conflicts, no duplicate lines, no diagnosis mismatches.
   - Coding must reflect typical, defensible billing for the specialty and complexity.
7. If is_clean is false:
   - planted_errors MUST contain 1–3 entries from ERROR_CATALOG.
   - Each planted error must be GROUND-TRUTH RECOVERABLE: an experienced medical biller reviewing the bill should be able to identify exactly the problem you describe. Do not plant errors that are too subtle to detect from the bill alone.
   - The rest of the bill must otherwise be plausible. The errors are signal, not noise.
8. Do NOT include any real patient identifiers, real providers, real hospital names, or real-looking SSNs.
9. Vary the patient demographic, the encounter narrative implied by the codes, and the geographic location across calls. Do not default to the same names or cities.
10. The implied clinical scenario must be coherent. The diagnoses, procedures, place of service, and specialty must all tell a believable story.

Output JSON only.
```

---

## USER PROMPT TEMPLATE

The orchestrator fills these placeholders for each call:

```
Generate one synthetic medical bill with the following parameters:

specialty: {{SPECIALTY}}
bill_type: {{BILL_TYPE}}             # "CMS-1500" or "UB-04"
is_clean: {{IS_CLEAN}}               # true or false
patient_age_range: {{AGE_RANGE}}     # e.g. "30-45"
patient_sex: {{SEX}}                 # "M" or "F"
geographic_region: {{REGION}}        # e.g. "Pacific Northwest", "Southeast", "Midwest"
seed_hint: {{SEED}}                  # short string to encourage diversity, e.g. "rural clinic, evening visit"

If is_clean is false, choose 1–3 errors from ERROR_CATALOG that are PLAUSIBLE for this specialty. Specialty-appropriate errors only — do not, for example, plant a BILATERAL_NO_50 error in a psychiatry bill.
```

---

## VARIATION STRATEGY (FOR THE ORCHESTRATOR, NOT THE MODEL)

To reach 1,000 bills with real diversity, the orchestrator should round-robin across these dimensions:

**Specialties (20)** — split bills evenly across:
`family_medicine, emergency_medicine, orthopedics, cardiology, dermatology, ob_gyn, pediatrics, psychiatry, radiology, pathology, anesthesiology, general_surgery, oncology, physical_therapy, urology, gastroenterology, ophthalmology, ent, neurology, dental_oral_surgery`

That's 50 bills per specialty → 25 clean + 25 dispute per specialty → 500 + 500 total.

**Bill type** — roughly 80% CMS-1500 (professional), 20% UB-04 (institutional). UB-04 mostly for ER, surgery, oncology, anesthesia.

**Demographics** — sample uniformly from age buckets `[0-12, 13-25, 26-45, 46-65, 66-85]` and sex.

**Region** — sample from `[Pacific NW, West Coast, Southwest, Mountain West, Midwest, South, Southeast, Northeast]`.

**Seed hint** — feed a short randomized string (e.g. `"after-hours visit"`, `"workers comp"`, `"second opinion"`, `"telehealth follow-up"`) to push the model toward different scenarios within the same specialty.

**Error mix (for the 500 dispute bills)** — don't let the model gravitate to UPCODE every time. The orchestrator can request specific error types so coverage is even across the 15 categories — roughly 33 bills per error type.

---

## FILENAME ASSIGNMENT (ORCHESTRATOR)

The model never produces filenames. The orchestrator does:

```python
if bill["metadata"]["is_clean"]:
    clean_counter += 1
    fname = f"clean_{clean_counter:03d}.pdf"
else:
    dis_counter += 1
    fname = f"dis_{dis_counter:03d}.pdf"
```

This guarantees `clean_001.pdf` … `clean_500.pdf` and `dis_001.pdf` … `dis_500.pdf` regardless of the order generations come back.

---

## GROUND-TRUTH MANIFEST

For every bill, the orchestrator should also write a row to `samples/manifest.csv`:

```csv
filename,is_clean,specialty,bill_type,planted_errors,expected_total_savings_usd
clean_001.pdf,true,family_medicine,CMS-1500,,0
dis_001.pdf,false,orthopedics,CMS-1500,"NCCI_PAIR;UNITS_EXCEED_MUE",425.50
```

This manifest is your **eval set**. When you run Lethe over `/samples/`, you can compute precision/recall on error detection by comparing agent verdicts to the manifest. That's the difference between "we made a demo" and "we have evidence the consensus engine works."

---

## NEXT STEPS

To actually generate 1,000 bills, you need:

1. **Orchestrator** — Python script that loops 1,000 times, fills the user template, calls the Anthropic API, validates the JSON, retries on failure.
2. **PDF renderer** — converts the JSON output into a CMS-1500 / UB-04 styled PDF (HTML template + WeasyPrint is the simplest path).
3. **Manifest writer** — appends each bill's ground truth to `samples/manifest.csv`.

Rough cost estimate for 1,000 calls with Claude Sonnet on this prompt: ~$15–25 depending on output length. Time: ~30–60 minutes with reasonable concurrency.

If you want, I can write the orchestrator + renderer next. They'd be ~150 lines of Python total and produce the full `/samples/` directory ready to drop into your Lethe repo.
