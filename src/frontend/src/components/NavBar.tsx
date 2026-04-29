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
                fontFamily: "var(--font-jetbrains-mono), monospace",
                padding: "5px 10px",
                border: "1px solid var(--line-strong)",
                borderRadius: 3,
                color: "var(--accent-violet)",
                textDecoration: "none",
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
                color: "var(--ink-faint)",
                fontSize: 11,
                cursor: "pointer",
                padding: "2px 4px",
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
              fontSize: 12,
              padding: "5px 12px",
              border: "1px solid var(--line-strong)",
              borderRadius: 3,
              background: "transparent",
              color: "var(--ink)",
              cursor: connecting ? "wait" : "pointer",
              fontFamily: "inherit",
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
