"""Payer integration — actual claim filing with insurance carriers.

Today this is a stub. Real production integration requires:

  - **Stedi** (https://www.stedi.com/) — modern X12 EDI as JSON API.
    Claim status (276/277), claim filing (837), ERA (835).
  - **Change Healthcare / Optum** — legacy but ubiquitous EDI clearinghouse.
    Sandbox accounts via UnitedHealth Group developer portal.
  - **Availity** — multi-payer auth + claim portal, FHIR R4 endpoints for
    BlueCard plans (https://developer.availity.com/).
  - **Direct payer FHIR APIs** — most major plans now expose FHIR R4
    Patient/Coverage/Claim resources under CMS Interoperability Rule.

The hard work is the EDI/FHIR mapping from a redacted Lethe finding to a
properly-formed claim or appeal request. Each payer has quirks. This module
provides the abstraction layer; integrations slot in per payer.

Submission shape (rough):
    {
      payer_id: "stedi-test" | "availity" | "change-healthcare" | "<plan-fhir-base>",
      patient: { member_id, dob, plan_id },           // optional, user-supplied
      provider_npi: "1234567890",
      bill_sha256: "0x...",
      verdict: "dispute",
      disputed_codes: [{ cpt: "99214", units: 1, charge_cents: 18500, reason: "DUPLICATE" }, ...],
      attachments: { letter_html: "...", chain_proof_url: "..." },
    }
"""
