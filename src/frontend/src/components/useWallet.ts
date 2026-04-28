"use client";

import { useCallback, useEffect, useState } from "react";

/** Minimal wallet hook — no wagmi/viem dependency. Just window.ethereum. */

const STORAGE_KEY = "lethe.wallet.address";

type EthRequestArgs = { method: string; params?: unknown[] };
type EthOnHandler = (...args: unknown[]) => void;
type EthereumProvider = {
  request: (args: EthRequestArgs) => Promise<unknown>;
  on?: (event: string, handler: EthOnHandler) => void;
  removeListener?: (event: string, handler: EthOnHandler) => void;
};

declare global {
  interface Window {
    ethereum?: EthereumProvider;
  }
}

export function useWallet() {
  const [address, setAddress] = useState<string | null>(null);
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Hydrate from localStorage on mount so the connection survives reload.
  useEffect(() => {
    try {
      const cached = localStorage.getItem(STORAGE_KEY);
      if (cached && /^0x[0-9a-fA-F]{40}$/.test(cached)) setAddress(cached);
    } catch {}
  }, []);

  // Listen for account changes from the injected wallet.
  useEffect(() => {
    if (typeof window === "undefined" || !window.ethereum?.on) return;
    const handler: EthOnHandler = (...args: unknown[]) => {
      const accounts = args[0] as string[] | undefined;
      const next = accounts?.[0]?.toLowerCase() ?? null;
      setAddress(next);
      try {
        if (next) localStorage.setItem(STORAGE_KEY, next);
        else localStorage.removeItem(STORAGE_KEY);
      } catch {}
    };
    window.ethereum.on("accountsChanged", handler);
    return () => {
      window.ethereum?.removeListener?.("accountsChanged", handler);
    };
  }, []);

  const connect = useCallback(async () => {
    if (typeof window === "undefined" || !window.ethereum) {
      setError("No wallet found. Install MetaMask or another EIP-1193 wallet.");
      return null;
    }
    setConnecting(true);
    setError(null);
    try {
      const accounts = (await window.ethereum.request({
        method: "eth_requestAccounts",
      })) as string[];
      const next = accounts[0]?.toLowerCase() ?? null;
      setAddress(next);
      if (next) {
        try { localStorage.setItem(STORAGE_KEY, next); } catch {}
      }
      return next;
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      return null;
    } finally {
      setConnecting(false);
    }
  }, []);

  const disconnect = useCallback(() => {
    setAddress(null);
    try { localStorage.removeItem(STORAGE_KEY); } catch {}
  }, []);

  return { address, connecting, error, connect, disconnect };
}

export function shortenAddress(addr: string): string {
  return `${addr.slice(0, 6)}…${addr.slice(-4)}`;
}

/** Pure-localStorage audit history keyed by connected wallet. The on-chain
 *  Anchored event is signed by the COORDINATOR's wallet, not the user's,
 *  so we maintain a client-side index of (sha, tx, ts) per user wallet. */
const AUDITS_KEY_PREFIX = "lethe.audits.";

export type LocalAudit = {
  sha: string;
  filename?: string;
  verdict?: string;
  agree_count?: number;
  total_agents?: number;
  anchor_tx?: string | null;
  ts: number;
};

export function loadAudits(wallet: string | null): LocalAudit[] {
  if (!wallet) return [];
  try {
    const raw = localStorage.getItem(AUDITS_KEY_PREFIX + wallet.toLowerCase());
    if (!raw) return [];
    const arr = JSON.parse(raw);
    return Array.isArray(arr) ? arr : [];
  } catch {
    return [];
  }
}

export function appendAudit(wallet: string | null, audit: LocalAudit): void {
  if (!wallet) return;
  try {
    const key = AUDITS_KEY_PREFIX + wallet.toLowerCase();
    const existing = loadAudits(wallet);
    // Dedupe by sha
    const filtered = existing.filter((a) => a.sha !== audit.sha);
    const next = [audit, ...filtered].slice(0, 100); // cap at 100 most recent
    localStorage.setItem(key, JSON.stringify(next));
  } catch {}
}
