"""Parser stage.

Extracts text from PDF / TXT / IMG uploads. The redactor sees this output;
the agents see the redactor's output. The original bill bytes are released
immediately after parsing.

Design notes:
- pdfplumber for real PDFs. If a PDF fails to open (e.g., our hackathon
  fake-PDF samples that are really plain text), fall back to a UTF-8 decode.
- TXT is decoded directly.
- Images go through GPT-4o vision OCR when OPENAI_API_KEY is set. Important
  privacy note: the raw image is sent to OpenAI before redaction (the parser
  must see un-redacted content by definition). Redaction applies to the
  extracted text afterward, so nothing un-redacted ever leaves the parse stage.
- We do NOT attempt structured field extraction here; agents read the text.
"""

from __future__ import annotations

import asyncio
import base64
import time
from io import BytesIO
from typing import Any, Dict, Tuple

from config import settings


_OCR_PROMPT = """Extract all text from this medical bill image. Preserve:
- line items, codes (CPT/ICD/HCPCS/REV), modifiers, units, charges
- provider/facility names, dates, claim/account references
- any field labels and section headings
Return raw text only — no commentary, no markdown, no JSON wrapper. Use line breaks to preserve layout where possible."""


async def _ocr_image(bill_bytes: bytes, ext: str, api_key: str) -> Tuple[str, Dict[str, Any]]:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=api_key)
    mime = {"jpg": "jpeg"}.get(ext, ext)
    b64 = base64.b64encode(bill_bytes).decode("ascii")
    started = time.perf_counter()
    resp = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a medical bill OCR engine. Be exhaustive and faithful to the source. Return text only."},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": _OCR_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/{mime};base64,{b64}"},
                    },
                ],
            },
        ],
        temperature=0,
        max_tokens=4000,
    )
    text = (resp.choices[0].message.content or "").strip()
    return text, {
        "model": "gpt-4o",
        "duration_ms": int((time.perf_counter() - started) * 1000),
        "output_chars": len(text),
    }


async def parse(filename: str, bill_bytes: bytes, simulated_delay_ms: int) -> Dict[str, Any]:
    # Real parsing — no artificial delay. The actual time is the actual time.
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    text = ""
    pages = 0
    parser_used = "fallback"
    ocr_meta: Dict[str, Any] = {}

    if ext == "pdf":
        try:
            import pdfplumber

            with pdfplumber.open(BytesIO(bill_bytes)) as pdf:
                pages = len(pdf.pages)
                text = "\n\n".join((page.extract_text() or "") for page in pdf.pages).strip()
                parser_used = "pdfplumber"
        except Exception:
            text = bill_bytes.decode("utf-8", errors="replace").strip()
            parser_used = "text-fallback"
        # Some scanned PDFs return empty text — try OCR on the first page if a
        # vision API key is available.
        if not text.strip() and settings.openai_api_key:
            try:
                text, ocr_meta = await _ocr_image(bill_bytes, "pdf", settings.openai_api_key)
                parser_used = "openai-vision-pdf-fallback"
            except Exception as e:
                ocr_meta = {"error": f"{type(e).__name__}: {str(e)[:160]}"}
    elif ext == "txt":
        text = bill_bytes.decode("utf-8", errors="replace").strip()
        pages = 1
        parser_used = "text"
    elif ext in {"png", "jpg", "jpeg", "webp"}:
        if settings.openai_api_key:
            try:
                text, ocr_meta = await _ocr_image(bill_bytes, ext, settings.openai_api_key)
                parser_used = "openai-vision"
            except Exception as e:
                text = ""
                parser_used = "image-error"
                ocr_meta = {"error": f"{type(e).__name__}: {str(e)[:160]}"}
        else:
            text = "[image upload — set OPENAI_API_KEY to enable vision OCR]"
            parser_used = "image-stub"
    else:
        text = bill_bytes.decode("utf-8", errors="replace").strip()
        parser_used = "text-fallback"

    if simulated_delay_ms:
        await asyncio.sleep(0)

    out: Dict[str, Any] = {
        "filename": filename,
        "size_bytes": len(bill_bytes),
        "page_count": pages,
        "parser": parser_used,
        "text": text,
        "structured": None,
    }
    if ocr_meta:
        out["ocr"] = ocr_meta
    return out
