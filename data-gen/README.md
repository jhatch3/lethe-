# Lethe Synthetic Medical Bills

A pipeline for generating synthetic medical bills with planted, ground-truth-labeled errors. Use this directory as the contents of `/samples/` in your Lethe repo.

## What's in the box

```
lethe-samples/
├── README.md                 ← you are here
├── prompt/
│   ├── bill-generator-prompt.md  ← full prompt documentation
│   └── system_prompt.txt          ← extracted system prompt for generate.py
├── scripts/
│   ├── generate.py           ← orchestrator (calls Anthropic API in a loop)
│   └── render.py             ← JSON → PDF renderer (CMS-1500 / UB-04 layout)
├── bills_json/
│   └── seed_bills.json       ← 10 hand-crafted starter bills (5 clean + 5 dispute)
└── bills_pdf/
    ├── clean_001.pdf … clean_005.pdf
    ├── dis_001.pdf … dis_005.pdf
    └── manifest.csv          ← ground truth: filename, is_clean, specialty, planted errors, expected savings
```

The 10 bills already in `bills_pdf/` were generated directly without API calls so you can verify the renderer works end-to-end before spending on the 1,000-bill run.

## To scale to 1,000 bills

```bash
# 1. Install deps
pip install anthropic reportlab pdf2image

# 2. Set your API key
export ANTHROPIC_API_KEY=sk-ant-...

# 3. Generate JSON bills (this is the part that costs money)
python scripts/generate.py --count 1000 --output bills_json/ --concurrency 8

# 4. Render JSON → PDF + build manifest
python scripts/render.py --input bills_json/ --output bills_pdf/
```

**Cost & time estimates:**
- ~$15-25 in API calls for 1,000 bills with claude-sonnet-4-6
- ~30-60 minutes wall-clock at concurrency 8
- Output: `clean_001.pdf` … `clean_500.pdf`, `dis_001.pdf` … `dis_500.pdf`, plus `manifest.csv`

## How filenames work

`generate.py` doesn't assign filenames — it just produces JSON files with `is_clean: true/false` in the metadata. `render.py` reads each one and assigns:
- `clean_NNN.pdf` if `metadata.is_clean == true`
- `dis_NNN.pdf` if `metadata.is_clean == false`

Counters are 3-digit zero-padded. If a generation fails, retries don't create gaps in numbering because numbering happens at render time, not generation time.

## How the manifest works

`manifest.csv` is your **eval set**. For every bill, it records:
- Whether the bill is clean or has planted errors
- Which specific error types were planted
- Expected dollar savings if Lethe correctly catches and disputes the errors

When your three-agent consensus runs over `bills_pdf/`, you can compute:
- **Recall** — what fraction of planted errors did the agents catch?
- **Precision** — what fraction of agent-flagged errors were real (i.e., not flagged on clean bills)?
- **Per-error-type accuracy** — does the consensus catch UPCODE better than UNBUNDLE?
- **Dollar-weighted accuracy** — what fraction of total recoverable money did the agents identify?

This is the difference between "we built a demo" and "we have evidence the consensus engine works." It's also what judges will ask about.

## Variation strategy (in `generate.py`)

The orchestrator round-robins across:
- **20 specialties** (family medicine through dental/oral surgery)
- **15 error types** (UPCODE, DUPLICATE, UNBUNDLE, NCCI_PAIR, etc.)
- **5 age ranges** × 2 sexes
- **9 geographic regions**
- **15 seed hints** (after-hours visit, workers comp, telehealth follow-up, etc.)
- **CMS-1500 vs UB-04** weighted by specialty

For 1,000 bills with a 50/50 clean/dispute split, you get 25 clean + 25 dispute bills per specialty, with each error type appearing on roughly 33 bills (covering all 20 specialties for which it's plausible).

## Specialty-error filtering

Not all errors are plausible for all specialties. The orchestrator filters:
- Psychiatry can't have BILATERAL_NO_50 (no laterality)
- Physical therapy gets weighted toward UNITS_EXCEED_MUE (the actual common PT error)
- Pathology gets weighted toward UNBUNDLE (the actual common path error)

The `SPECIALTY_ERROR_HINTS` dict in `generate.py` controls this. Edit to taste.

## The system prompt

See `prompt/bill-generator-prompt.md` for the full annotated prompt with the JSON schema, error catalog, and rules. The bare prompt text used at runtime is in `prompt/system_prompt.txt`.

## License

The code in this directory is MIT-licensed. The synthetic bills are not copyrightable — they describe fictional patients with fictional providers and fictional charges. Ship them.
