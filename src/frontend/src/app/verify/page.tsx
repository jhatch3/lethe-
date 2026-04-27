"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { Suspense, useCallback, useEffect, useRef, useState, type ChangeEvent, type DragEvent } from "react";
import { useSearchParams } from "next/navigation";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type VerifyAnchored = {
  anchored: true;
  sha256: string;
  verdict: string;
  verdict_int: number;
  agree_count: number;
  total_agents: number;
  anchored_at: number;
  anchored_by: string;
  registry_address: string;
  network: string;
  chain_id: number;
};

type VerifyMissing = {
  anchored: false;
  sha256?: string;
  registry_address: string;
  network: string;
  chain_id: number;
};

type VerifyResult = VerifyAnchored | VerifyMissing;

const CHAINSCAN = "https://chainscan-galileo.0g.ai";

async function sha256Hex(file: File): Promise<string> {
  const buf = await file.arrayBuffer();
  const digest = await crypto.subtle.digest("SHA-256", buf);
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

async function fetchVerify(hex: string): Promise<VerifyResult> {
  const r = await fetch(`${API_URL}/api/verify/${hex}`);
  if (!r.ok) {
    const txt = await r.text().catch(() => "");
    throw new Error(`HTTP ${r.status}: ${txt.slice(0, 160)}`);
  }
  return (await r.json()) as VerifyResult;
}

function VerifyInner() {
  const params = useSearchParams();
  const queryHash = params.get("sha");

  const [busy, setBusy] = useState(false);
  const [filename, setFilename] = useState<string | null>(null);
  const [hash, setHash] = useState<string | null>(null);
  const [result, setResult] = useState<VerifyResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const verifyHash = useCallback(async (hex: string) => {
    const clean = hex.toLowerCase().replace(/^0x/, "");
    setBusy(true);
    setError(null);
    setResult(null);
    setHash("0x" + clean);
    try {
      const body = await fetchVerify(clean);
      setResult(body);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }, []);

  const verifyFile = useCallback(
    async (file: File) => {
      setBusy(true);
      setError(null);
      setResult(null);
      setHash(null);
      setFilename(file.name);
      try {
        const hex = await sha256Hex(file);
        await verifyHash(hex);
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
        setBusy(false);
      }
    },
    [verifyHash]
  );

  // If ?sha=0x... was passed, auto-verify on load
  useEffect(() => {
    if (queryHash && /^(0x)?[0-9a-fA-F]{64}$/.test(queryHash)) {
      void verifyHash(queryHash);
    }
  }, [queryHash, verifyHash]);

  const onDrop = useCallback(
    (e: DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      setDragging(false);
      const f = e.dataTransfer?.files?.[0];
      if (f) void verifyFile(f);
    },
    [verifyFile]
  );

  const verdictColor =
    result && result.anchored
      ? result.verdict === "approve"
        ? "var(--accent-green)"
        : result.verdict === "clarify"
        ? "var(--accent-amber)"
        : "var(--accent-rose)"
      : "var(--ink-faint)";

  return (
    <>
      <nav className="nav-top">
        <div className="brand">
          <span className="dot" />
          Lethe
          <span className="brand-sub">/ verify</span>
        </div>
        <div className="links">
          <Link href="/">Home</Link>
          <Link href="/dashboard">Dashboard</Link>
        </div>
        <Link className="cta" href="/">
          ← Back to home
        </Link>
      </nav>

      <div className="dash-page">
        <section className="dash-hero">
          <motion.div
            className="dash-eyebrow"
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <span className="pulse-dot" />
            <span className="pill">verify · zero upload</span>
            <span>file stays in your browser</span>
          </motion.div>

          <motion.h1
            className="dash-headline"
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.05 }}
          >
            Verify a bill.<br />
            <em>Was it audited?</em>
          </motion.h1>

          <motion.p
            className="dash-sub"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.6, delay: 0.15 }}
          >
            Drop the bill PDF, TXT, or image. Your browser computes its
            SHA-256 locally and queries the on-chain registry. The bill
            itself never leaves your machine.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.25 }}
            className={`upload-stage${dragging ? " dragging" : ""}`}
            onClick={() => fileRef.current?.click()}
            onDragOver={(e) => {
              e.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
          >
            <div className="up-glyph">⌕</div>
            <div className="up-h">Drop a file to verify</div>
            <div className="up-p">
              SHA-256 is computed in-browser; the file never uploads. Only the hash hits the backend, which queries the contract on 0G Galileo.
            </div>
            <div className="upload-types">
              <span>pdf</span>
              <span>txt</span>
              <span>png</span>
              <span>jpg</span>
            </div>
            <input
              ref={fileRef}
              type="file"
              accept=".pdf,.txt,.png,.jpg,.jpeg,.webp"
              style={{ display: "none" }}
              onChange={(e: ChangeEvent<HTMLInputElement>) => {
                const f = e.target.files?.[0];
                if (f) void verifyFile(f);
              }}
            />
          </motion.div>

          {(busy || hash || error) && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4 }}
              style={{
                marginTop: 36,
                width: "100%",
                maxWidth: 720,
                border: "1px solid var(--line)",
                borderRadius: 8,
                background: "var(--bg-elev)",
                padding: 24,
              }}
            >
              {filename && (
                <div
                  style={{
                    fontFamily: "var(--font-jetbrains-mono), monospace",
                    fontSize: 11,
                    letterSpacing: "0.18em",
                    textTransform: "uppercase",
                    color: "var(--ink-faint)",
                    marginBottom: 12,
                  }}
                >
                  file <b style={{ color: "var(--ink)" }}>{filename}</b>
                </div>
              )}
              {hash && (
                <div
                  style={{
                    fontFamily: "var(--font-jetbrains-mono), monospace",
                    fontSize: 12,
                    color: "var(--ink-dim)",
                    wordBreak: "break-all",
                    marginBottom: 16,
                  }}
                >
                  sha256: {hash}
                </div>
              )}
              {busy && (
                <div style={{ color: "var(--accent-violet)" }}>checking on-chain registry…</div>
              )}
              {error && (
                <div style={{ color: "var(--accent-rose)" }}>
                  ⚠ {error}
                </div>
              )}
              {result && result.anchored && (
                <div>
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 12,
                      marginBottom: 18,
                    }}
                  >
                    <span style={{ color: verdictColor, fontSize: 24 }}>●</span>
                    <span
                      className="dash-headline"
                      style={{
                        fontSize: "clamp(28px, 4vw, 44px)",
                        margin: 0,
                        textTransform: "capitalize",
                      }}
                    >
                      {result.verdict === "approve" ? "Approved" : result.verdict}
                      {" · "}
                      <em>{result.agree_count}/{result.total_agents}</em>
                    </span>
                  </div>
                  <div
                    style={{
                      display: "grid",
                      gridTemplateColumns: "auto 1fr",
                      gap: "8px 16px",
                      fontFamily: "var(--font-jetbrains-mono), monospace",
                      fontSize: 12,
                      color: "var(--ink-dim)",
                    }}
                  >
                    <span style={{ color: "var(--ink-faint)" }}>anchored at</span>
                    <span>{new Date(result.anchored_at * 1000).toLocaleString()}</span>
                    <span style={{ color: "var(--ink-faint)" }}>anchored by</span>
                    <span style={{ wordBreak: "break-all" }}>{result.anchored_by}</span>
                    <span style={{ color: "var(--ink-faint)" }}>registry</span>
                    <span style={{ wordBreak: "break-all" }}>
                      <a
                        href={`${CHAINSCAN}/address/${result.registry_address}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{ color: "var(--ink)", borderBottom: "1px dotted var(--ink-faint)" }}
                      >
                        {result.registry_address}
                      </a>
                    </span>
                    <span style={{ color: "var(--ink-faint)" }}>network</span>
                    <span>{result.network} (chain {result.chain_id})</span>
                  </div>
                </div>
              )}
              {result && !result.anchored && (
                <div>
                  <div
                    className="dash-headline"
                    style={{
                      fontSize: "clamp(28px, 4vw, 44px)",
                      margin: 0,
                      color: "var(--ink-faint)",
                    }}
                  >
                    Not in registry.
                  </div>
                  <p
                    style={{
                      marginTop: 14,
                      color: "var(--ink-dim)",
                      fontSize: 14,
                      lineHeight: 1.6,
                      maxWidth: 540,
                    }}
                  >
                    This SHA-256 has not been anchored by the Lethe coordinator at{" "}
                    <code style={{ fontFamily: "var(--font-jetbrains-mono), monospace" }}>
                      {result.registry_address.slice(0, 10)}…
                    </code>
                    . Either the bill was never audited, or it was audited by a different deployment.
                  </p>
                </div>
              )}
            </motion.div>
          )}

          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.6, delay: 0.45 }}
            className="privacy-line"
          >
            <span><b>local</b> hash</span>
            <span className="div">·</span>
            <span><b>0</b> upload</span>
            <span className="div">·</span>
            <span>chain <b>read-only</b></span>
            <span className="div">·</span>
            <span>works <b>without</b> lethe servers</span>
          </motion.div>
        </section>
      </div>
    </>
  );
}

export default function VerifyPage() {
  return (
    <Suspense fallback={null}>
      <VerifyInner />
    </Suspense>
  );
}