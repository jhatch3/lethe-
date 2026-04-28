"""Email delivery for Lethe appeal letters.

Three providers, picked from `LETHE_EMAIL_PROVIDER`:
- `resend` — modern API service (recommended; free tier covers hackathons)
- `smtp`   — works with Gmail/Outlook app passwords, stdlib only
- `stub`   — logs the email but doesn't send (default — demo-honest)

The sender + template are split so the same HTML body can be reused by
non-email channels later (Slack, webhook, etc.) without re-building the
formatted content.
"""
