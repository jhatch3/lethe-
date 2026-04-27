"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode, MouseEvent } from "react";

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
        <Link href="/tech-stack">Tech Stack</Link>
        <Link href="/verify">Verify</Link>
        <Link href="/patterns">Patterns</Link>
        <Link href="/axl">Mesh</Link>
      </div>
      {cta ?? (
        <Link className="cta" href="/dashboard">
          Open dashboard →
        </Link>
      )}
    </nav>
  );
}
