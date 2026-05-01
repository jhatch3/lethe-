"use client";

import { useCallback, useEffect, useState } from "react";
import { useAccount, useDisconnect } from "wagmi";
import { useConnectModal } from "@rainbow-me/rainbowkit";

const STORAGE_KEY = "lethe.wallet.address";

export function useWallet() {
  const { address: rawAddress, isConnecting, isReconnecting } = useAccount();
  const { openConnectModal } = useConnectModal();
  const { disconnect: wagmiDisconnect } = useDisconnect();
  const [error, setError] = useState<string | null>(null);

  const address = rawAddress ? rawAddress.toLowerCase() : null;
  const connecting = isConnecting || isReconnecting;

  // Mirror connected address into localStorage so legacy reads
  // (dashboard/page.tsx reads `lethe.wallet.address` directly) keep working.
  useEffect(() => {
    try {
      if (address) localStorage.setItem(STORAGE_KEY, address);
      else localStorage.removeItem(STORAGE_KEY);
    } catch {}
  }, [address]);

  const connect = useCallback(async () => {
    setError(null);
    if (!openConnectModal) {
      setError("Wallet modal unavailable. Refresh the page and try again.");
      return null;
    }
    openConnectModal();
    return null;
  }, [openConnectModal]);

  const disconnect = useCallback(() => {
    wagmiDisconnect();
  }, [wagmiDisconnect]);

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
    const filtered = existing.filter((a) => a.sha !== audit.sha);
    const next = [audit, ...filtered].slice(0, 100);
    localStorage.setItem(key, JSON.stringify(next));
  } catch {}
}
