"""Build the HTML appeal-letter email body.

The email always contains two halves:
  1. The drafted appeal letter (Markdown rendered as <pre>-friendly HTML)
  2. A "chain verification" block listing every on-chain artifact the audit
     produced — anchor tx (Galileo), pattern index tx (Galileo), storage
     commitment tx (Galileo), Sepolia mirror tx, dispute filing tx (if
     dispute verdict). Each row links to the relevant block explorer.

Designed for plain inline-styled HTML — works in every major email client
(Gmail, Outlook, Apple Mail) without external CSS.
"""

from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional


_GALILEO_TX = "https://chainscan-galileo.0g.ai/tx/"
_SEPOLIA_TX = "https://sepolia.etherscan.io/tx/"
_SEPOLIA_ADDR = "https://sepolia.etherscan.io/address/"


def _row(label: str, value: str, link: Optional[str] = None) -> str:
    val_html = (
        f'<a href="{_html.escape(link)}" style="color:#0b6cda;text-decoration:none">'
        f'{_html.escape(value)} ↗</a>'
        if link
        else _html.escape(value)
    )
    return (
        '<tr>'
        f'<td style="padding:6px 12px 6px 0;color:#6b6b6b;vertical-align:top;font-size:13px;width:160px">{_html.escape(label)}</td>'
        f'<td style="padding:6px 0;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12px;word-break:break-all">{val_html}</td>'
        '</tr>'
    )


def _short_tx(tx: Optional[str]) -> str:
    if not tx:
        return "—"
    t = tx if tx.startswith("0x") else "0x" + tx
    if len(t) > 22:
        return f"{t[:14]}…{t[-8:]}"
    return t


def build_appeal_email_html(
    *,
    appeal_letter_markdown: str,
    bill_sha256: str,
    verdict: str,
    agree_count: int,
    total_agents: int,
    proof: Dict[str, Any],
    sender_name: str = "Lethe",
    public_url: str = "http://localhost:3000",
) -> str:
    """Compose the HTML body. `proof` is the receipt dict from the pipeline.
    `public_url` is the Lethe dashboard root, used to build the verify link.
    """
    sha = bill_sha256[:64] if bill_sha256.startswith("0x") else bill_sha256
    sha_disp = sha if sha.startswith("0x") else "0x" + sha
    verify_url = f"{public_url.rstrip('/')}/verify?sha={sha_disp}"

    # Convert the drafted letter to safe HTML (preserve linebreaks).
    letter_html = (
        '<div style="font-family:Georgia,serif;line-height:1.6;font-size:15px;color:#222;'
        'white-space:pre-wrap;background:#fafafa;padding:24px;border-left:3px solid #0b6cda;'
        'border-radius:4px">'
        f'{_html.escape(appeal_letter_markdown)}'
        '</div>'
    )

    # Chain verification table.
    rows: List[str] = []

    p = proof or {}
    if p.get("anchor_tx"):
        tx = p["anchor_tx"]
        rows.append(_row("0G Galileo · BillRegistry", _short_tx(tx), _GALILEO_TX + (tx if tx.startswith("0x") else "0x" + tx)))
    patterns = (p.get("patterns") or {})
    if patterns.get("tx"):
        tx = patterns["tx"]
        rows.append(_row("0G Galileo · PatternRegistry", _short_tx(tx), _GALILEO_TX + (tx if tx.startswith("0x") else "0x" + tx)))
    storage = patterns.get("storage") or {}
    if storage.get("tx_hash"):
        rows.append(_row("0G Storage · commitment", _short_tx(storage["tx_hash"]), storage.get("tx_link") or _GALILEO_TX + storage["tx_hash"]))
    if storage.get("root_hash"):
        rows.append(_row("0G Storage · merkle root", _short_tx(storage["root_hash"])))

    mirror = p.get("mirror") or {}
    if mirror.get("tx_hash"):
        rows.append(_row(
            "Sepolia mirror · BillRegistry",
            _short_tx(mirror["tx_hash"]),
            mirror.get("tx_link") or _SEPOLIA_TX + mirror["tx_hash"],
        ))
    elif mirror.get("status") == "duplicate" and mirror.get("registry_address"):
        rows.append(_row(
            "Sepolia mirror · already anchored",
            "(view registry events)",
            _SEPOLIA_ADDR + mirror["registry_address"] + "#events",
        ))

    dispute = p.get("dispute_filing") or {}
    if dispute.get("tx_hash"):
        rows.append(_row(
            "Sepolia · DisputeRegistry",
            _short_tx(dispute["tx_hash"]),
            dispute.get("tx_link") or _SEPOLIA_TX + dispute["tx_hash"],
        ))

    if not rows:
        rows.append(
            '<tr><td colspan="2" style="padding:8px 0;font-size:12px;color:#9b9b9b;font-style:italic">'
            'no on-chain artifacts available — coordinator is running in stub mode'
            '</td></tr>'
        )

    chain_table = (
        '<table cellspacing="0" cellpadding="0" style="width:100%;border-collapse:collapse">'
        + "".join(rows) + "</table>"
    )

    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Appeal letter · Lethe audit</title>
</head>
<body style="margin:0;padding:0;background:#f4f4f4;font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif">
  <table width="100%" cellspacing="0" cellpadding="0" style="background:#f4f4f4">
    <tr><td align="center" style="padding:40px 16px">
      <table width="640" cellspacing="0" cellpadding="0" style="background:#fff;border-radius:8px;overflow:hidden;border:1px solid #e3e3e3">

        <tr><td style="padding:32px 32px 8px">
          <div style="font-family:ui-monospace,Menlo,monospace;font-size:11px;letter-spacing:0.18em;text-transform:uppercase;color:#9b9b9b">
            {_html.escape(sender_name)} · multi-agent bill audit
          </div>
          <h1 style="margin:14px 0 4px;font-family:Georgia,serif;font-size:26px;color:#111">
            Appeal letter
          </h1>
          <div style="color:#6b6b6b;font-size:14px;line-height:1.5">
            Three independent LLM agents (GPT-4o · Claude · Gemini) analyzed an itemized
            medical bill and reached <strong>{_html.escape(str(verdict))}</strong> consensus
            ({agree_count} of {total_agents} agents). The drafted letter below is provided
            for review; all chain-verifiable artifacts are listed at the bottom.
          </div>
        </td></tr>

        <tr><td style="padding:24px 32px 8px">
          <div style="font-family:ui-monospace,Menlo,monospace;font-size:11px;letter-spacing:0.18em;text-transform:uppercase;color:#9b9b9b;margin-bottom:10px">
            Drafted appeal
          </div>
          {letter_html}
        </td></tr>

        <tr><td style="padding:8px 32px 0">
          <div style="background:#eef2ff;border:1px solid #c7d2fe;border-radius:6px;padding:14px 18px">
            <div style="font-family:ui-monospace,Menlo,monospace;font-size:10px;letter-spacing:0.2em;text-transform:uppercase;color:#4338ca;margin-bottom:4px">
              Verify this audit
            </div>
            <a href="{_html.escape(verify_url)}" style="color:#1e1b4b;font-size:14px;text-decoration:none;font-weight:500">
              {_html.escape(verify_url)} ↗
            </a>
            <div style="color:#4338ca;font-size:12px;margin-top:6px;line-height:1.5">
              Open this link to look up the audit by SHA-256 and see every on-chain artifact
              (Galileo anchor, pattern index, storage commitment, Sepolia mirror, dispute filing)
              with one click.
            </div>
          </div>
        </td></tr>

        <tr><td style="padding:24px 32px 8px">
          <div style="font-family:ui-monospace,Menlo,monospace;font-size:11px;letter-spacing:0.18em;text-transform:uppercase;color:#9b9b9b;margin-bottom:6px">
            Chain verification (raw artifacts)
          </div>
          <div style="color:#6b6b6b;font-size:13px;margin-bottom:12px;line-height:1.5">
            Bill SHA-256: <span style="font-family:ui-monospace,Menlo,monospace;font-size:12px;color:#222">{_html.escape(sha_disp)}</span>
          </div>
          {chain_table}
        </td></tr>

        <tr><td style="padding:24px 32px 32px;border-top:1px solid #efefef;color:#9b9b9b;font-size:12px;line-height:1.6">
          This email was sent because a Lethe audit reached {_html.escape(str(verdict))} consensus
          and the bill recipient or their advocate elected to submit it for review.
          Lethe never auto-submits to insurers — every send is user-initiated.
          <br/><br/>
          The audit's reasoning is anchored on 0G Galileo (chain id 16602) and mirrored to
          Ethereum Sepolia via KeeperHub Direct Execution. Anyone with the SHA-256 above
          can independently verify what was analyzed by querying either chain.
        </td></tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""
