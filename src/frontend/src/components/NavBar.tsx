"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode, MouseEvent } from "react";
import { useWallet, shortenAddress } from "./useWallet";

export type NavBarProps = {
  /** Optional sub-brand label shown after "Lethe", e.g. "dashboard", "verify". */
  subBrand?: string;
  /** Optional CTA override on the right. Defaults to "Open dashboard →". */
  cta?: ReactNode;
};

/**
 * Shared site navigation. Same link set on every page so users always know
 * where they are and how to reach the others.
 *
 * Behavior:
 *  - "Lethe" wordmark links home
 *  - "Problem" / "Features" smooth-scroll on the landing page; on every other
 *    page they link to "/#problem" / "/#features" so the same word always works
 *  - The right-side CTA defaults to "Open dashboard →"; pages that need a
 *    page-specific CTA (e.g. dashboard's "New analysis") pass `cta`
 */
export function NavBar({ subBrand, cta }: NavBarProps) {
  const pathname = usePathname();
  const isHome = pathname === "/";
  const { address, connecting, connect, disconnect } = useWallet();

  const handleAnchor = (id: string) => (e: MouseEvent<HTMLAnchorElement>) => {
    if (isHome) {
      e.preventDefault();
      document.getElementById(id)?.scrollIntoView({ behavior: "smooth" });
    }
    // off-home: let Link handle the navigation to /#id
  };

  return (
    <nav className="nav-top">
      <Link href="/" className="brand">
        <span className="dot" />
        Lethe
        {subBrand ? <span className="brand-sub">/ {subBrand}</span> : null}
      </Link>
      <div className="links">
        <Link href={isHome ? "#problem" : "/#problem"} onClick={handleAnchor("problem")}>
          Problem
        </Link>
        <Link href={isHome ? "#features" : "/#features"} onClick={handleAnchor("features")}>
          Features
        </Link>
        <Link href={isHome ? "#patterns" : "/#patterns"} onClick={handleAnchor("patterns")}>
          Patterns
        </Link>
        <Link href={isHome ? "#rules" : "/#rules"} onClick={handleAnchor("rules")}>
          Rules
        </Link>
        <a
          href="https://github.com/jhatch3/lethe-"
          target="_blank"
          rel="noopener noreferrer"
        >
          GitHub
        </a>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        {address ? (
          <>
            <Link
              href="/my-audits"
              style={{
                fontSize: 12,
                fontFamily: "var(--font-roobert)",
                padding: "8px 14px",
                border: "1px solid var(--line-strong)",
                borderRadius: "var(--radius-buttons)",
                color: "var(--color-frost-white)",
                textDecoration: "none",
                letterSpacing: 0,
              }}
              title="View audits anchored from this wallet"
            >
              {shortenAddress(address)} ↗
            </Link>
            <button
              onClick={disconnect}
              style={{
                background: "transparent",
                border: "none",
                color: "var(--color-whisper-gray)",
                fontSize: 14,
                cursor: "pointer",
                padding: "2px 6px",
              }}
              title="Disconnect wallet"
            >
              ×
            </button>
          </>
        ) : (
          <button
            onClick={() => void connect()}
            disabled={connecting}
            style={{
              fontSize: 13,
              padding: "8px 16px",
              border: "1px solid var(--line-strong)",
              borderRadius: "var(--radius-buttons)",
              background: "transparent",
              color: "var(--color-frost-white)",
              cursor: connecting ? "wait" : "pointer",
              fontFamily: "var(--font-roobert)",
              letterSpacing: 0,
            }}
            title="Connect a wallet to track your audits"
          >
            {connecting ? "Connecting…" : "Connect wallet"}
          </button>
        )}
        {cta ?? (
          <Link className="cta" href="/dashboard">
            Open dashboard →
          </Link>
        )}
      </div>
    </nav>
  );
}
