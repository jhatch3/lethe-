"""
generate.py — Orchestrator for synthetic medical bill generation.

Calls the Anthropic Messages API N times with controlled variation across
specialty, error type, and demographic dimensions, then saves each bill as
a JSON file in the output directory. Filenames are NOT assigned here —
that happens in render.py based on the is_clean flag inside each JSON.

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    python generate.py --count 1000 --output bills_json/ --concurrency 8

Then:
    python render.py --input bills_json/ --output bills_pdf/

Cost estimate: ~$15-25 for 1000 bills with claude-sonnet-4-6.
Time estimate: ~30-60 minutes at concurrency 8.
"""
from __future__ import annotations
import argparse
import asyncio
import json
import os
import random
import time
from pathlib import Path
from typing import Any

import anthropic  # pip install anthropic

# ─────────────────────────────────────────────────────────────────────────────
# Variation matrix
# ─────────────────────────────────────────────────────────────────────────────

SPECIALTIES = [
    "family_medicine", "emergency_medicine", "orthopedics", "cardiology",
    "dermatology", "ob_gyn", "pediatrics", "psychiatry", "radiology",
    "pathology", "anesthesiology", "general_surgery", "oncology",
    "physical_therapy", "urology", "gastroenterology", "ophthalmology",
    "ent", "neurology", "dental_oral_surgery",
]

ERROR_TYPES = [
    "UPCODE", "DUPLICATE", "UNBUNDLE", "MODIFIER_25_ABUSE", "MODIFIER_59_ABUSE",
    "PHANTOM_SERVICE", "UNITS_EXCEED_MUE", "NCCI_PAIR", "DIAGNOSIS_MISMATCH",
    "STALE_CODE", "WRONG_POS", "BILATERAL_NO_50", "GLOBAL_PERIOD_VIOLATION",
    "BALANCE_BILL_COVERED", "INFLATED_CHARGE",
]

# Specialty → which errors are plausible (avoid e.g. BILATERAL_NO_50 in psychiatry)
SPECIALTY_ERROR_HINTS: dict[str, list[str]] = {
    "psychiatry": ["UPCODE", "DUPLICATE", "MODIFIER_25_ABUSE", "INFLATED_CHARGE", "BALANCE_BILL_COVERED", "PHANTOM_SERVICE", "STALE_CODE"],
    "physical_therapy": ["UNITS_EXCEED_MUE", "DUPLICATE", "INFLATED_CHARGE", "PHANTOM_SERVICE", "BALANCE_BILL_COVERED", "STALE_CODE"],
    "pathology": ["UNBUNDLE", "DUPLICATE", "INFLATED_CHARGE", "STALE_CODE", "NCCI_PAIR"],
    # All other specialties get the full catalog
}

REGIONS = [
    "Pacific Northwest", "West Coast", "Southwest", "Mountain West",
    "Midwest", "South", "Southeast", "Northeast", "Mid-Atlantic",
]

AGE_RANGES = ["0-12", "13-25", "26-45", "46-65", "66-85"]

SEED_HINTS = [
    "after-hours visit", "workers comp claim", "second opinion",
    "telehealth follow-up", "urgent care referral", "post-op check",
    "annual physical", "rural clinic", "academic medical center",
    "freestanding ASC", "concierge practice", "community hospital",
    "specialty referral", "inpatient consult", "screening exam",
]

# UB-04 vs CMS-1500: institutional bills weight toward ER, surgery, oncology, anesthesia, radiology
UB04_SPECIALTIES = {"emergency_medicine", "general_surgery", "oncology", "anesthesiology", "radiology", "orthopedics"}


# ─────────────────────────────────────────────────────────────────────────────
# Prompt
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT_PATH = Path(__file__).parent.parent / "prompt" / "system_prompt.txt"

USER_PROMPT_TEMPLATE = """\
Generate one synthetic medical bill with the following parameters:

specialty: {specialty}
bill_type: {bill_type}
is_clean: {is_clean}
patient_age_range: {age_range}
patient_sex: {sex}
geographic_region: {region}
seed_hint: {seed}
{error_directive}

Output JSON only, matching the schema in your system prompt. No commentary."""


def build_plan(count: int, seed: int = 42) -> list[dict]:
    """Build a deterministic plan of N bill specs balanced across dimensions."""
    rng = random.Random(seed)
    plan: list[dict] = []

    half = count // 2
    clean_count = half
    dirty_count = count - half

    # Distribute clean bills across specialties evenly
    for i in range(clean_count):
        specialty = SPECIALTIES[i % len(SPECIALTIES)]
        plan.append({
            "is_clean": True,
            "specialty": specialty,
            "bill_type": "UB-04" if (specialty in UB04_SPECIALTIES and rng.random() < 0.4) else "CMS-1500",
            "age_range": rng.choice(AGE_RANGES),
            "sex": rng.choice(["M", "F"]),
            "region": rng.choice(REGIONS),
            "seed": rng.choice(SEED_HINTS),
            "requested_error": None,
        })

    # Distribute dirty bills across (specialty × error type) for coverage
    for i in range(dirty_count):
        specialty = SPECIALTIES[i % len(SPECIALTIES)]
        candidate_errors = SPECIALTY_ERROR_HINTS.get(specialty, ERROR_TYPES)
        # cycle errors so we get even coverage
        requested_error = candidate_errors[(i // len(SPECIALTIES)) % len(candidate_errors)]
        plan.append({
            "is_clean": False,
            "specialty": specialty,
            "bill_type": "UB-04" if (specialty in UB04_SPECIALTIES and rng.random() < 0.4) else "CMS-1500",
            "age_range": rng.choice(AGE_RANGES),
            "sex": rng.choice(["M", "F"]),
            "region": rng.choice(REGIONS),
            "seed": rng.choice(SEED_HINTS),
            "requested_error": requested_error,
        })

    rng.shuffle(plan)
    return plan


def render_user_prompt(spec: dict) -> str:
    if spec["requested_error"]:
        directive = (
            f"requested_error: {spec['requested_error']}  "
            "(plant exactly this error type; you may also plant 1 additional related error if naturally occurring)"
        )
    else:
        directive = ""
    return USER_PROMPT_TEMPLATE.format(
        specialty=spec["specialty"],
        bill_type=spec["bill_type"],
        is_clean=str(spec["is_clean"]).lower(),
        age_range=spec["age_range"],
        sex=spec["sex"],
        region=spec["region"],
        seed=spec["seed"],
        error_directive=directive,
    )


# ─────────────────────────────────────────────────────────────────────────────
# API call with retry & validation
# ─────────────────────────────────────────────────────────────────────────────

REQUIRED_TOP_KEYS = {"metadata", "provider", "patient", "insurance", "encounter", "diagnoses", "service_lines", "totals"}


def validate(bill: dict) -> tuple[bool, str]:
    if not isinstance(bill, dict):
        return False, "not a dict"
    missing = REQUIRED_TOP_KEYS - bill.keys()
    if missing:
        return False, f"missing keys: {missing}"
    if not isinstance(bill["service_lines"], list) or not bill["service_lines"]:
        return False, "no service_lines"
    if "is_clean" not in bill["metadata"]:
        return False, "metadata.is_clean missing"
    if bill["metadata"]["is_clean"] and bill["metadata"].get("planted_errors"):
        return False, "is_clean=true but planted_errors non-empty"
    if not bill["metadata"]["is_clean"] and not bill["metadata"].get("planted_errors"):
        return False, "is_clean=false but planted_errors empty"
    return True, ""


async def generate_one(
    client: anthropic.AsyncAnthropic,
    system_prompt: str,
    spec: dict,
    model: str,
    max_retries: int = 3,
) -> dict | None:
    last_err = ""
    for attempt in range(max_retries):
        try:
            resp = await client.messages.create(
                model=model,
                max_tokens=4000,
                system=system_prompt,
                messages=[{"role": "user", "content": render_user_prompt(spec)}],
            )
            text = "".join(b.text for b in resp.content if hasattr(b, "text")).strip()
            # strip markdown fences if model adds them despite instructions
            if text.startswith("```"):
                text = text.split("```", 2)[1].lstrip("json").strip()
                if text.endswith("```"):
                    text = text.rsplit("```", 1)[0].strip()
            bill = json.loads(text)
            ok, err = validate(bill)
            if ok:
                return bill
            last_err = err
        except (json.JSONDecodeError, anthropic.APIError) as e:
            last_err = str(e)
        await asyncio.sleep(1.5 * (attempt + 1))
    print(f"  ✗ Failed spec {spec}: {last_err}")
    return None


async def run(count: int, output_dir: Path, model: str, concurrency: int) -> None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise SystemExit("Set ANTHROPIC_API_KEY in your environment.")

    client = anthropic.AsyncAnthropic(api_key=api_key)
    system_prompt = SYSTEM_PROMPT_PATH.read_text()
    plan = build_plan(count)
    output_dir.mkdir(parents=True, exist_ok=True)

    sem = asyncio.Semaphore(concurrency)
    results: list[dict] = []
    completed = 0
    start = time.time()

    async def worker(idx: int, spec: dict) -> None:
        nonlocal completed
        async with sem:
            bill = await generate_one(client, system_prompt, spec, model)
            if bill:
                # Save with a temp name; render.py assigns final name
                (output_dir / f"raw_{idx:05d}.json").write_text(json.dumps(bill, indent=2))
                results.append(bill)
            completed += 1
            if completed % 20 == 0 or completed == len(plan):
                elapsed = time.time() - start
                rate = completed / elapsed if elapsed > 0 else 0
                eta = (len(plan) - completed) / rate if rate > 0 else 0
                print(f"  [{completed}/{len(plan)}] {rate:.1f}/s, ETA {eta/60:.1f} min")

    await asyncio.gather(*[worker(i, s) for i, s in enumerate(plan)])

    print(f"\nGenerated {len(results)}/{count} valid bills in {(time.time() - start)/60:.1f} min")
    print(f"Next: python render.py --input {output_dir} --output bills_pdf/")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=1000)
    ap.add_argument("--output", default="bills_json")
    ap.add_argument("--model", default="claude-sonnet-4-6")
    ap.add_argument("--concurrency", type=int, default=8)
    args = ap.parse_args()

    asyncio.run(run(args.count, Path(args.output), args.model, args.concurrency))


if __name__ == "__main__":
    main()
