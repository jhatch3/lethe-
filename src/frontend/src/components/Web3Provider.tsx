"use client";

import "@rainbow-me/rainbowkit/styles.css";

import { type ReactNode, useState } from "react";
import { WagmiProvider, http } from "wagmi";
import { sepolia } from "wagmi/chains";
import { type Chain } from "viem";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  RainbowKitProvider,
  getDefaultConfig,
  darkTheme,
} from "@rainbow-me/rainbowkit";

const zeroGGalileo: Chain = {
  id: 16602,
  name: "0G Galileo Testnet",
  nativeCurrency: { name: "0G", symbol: "0G", decimals: 18 },
  rpcUrls: {
    default: { http: ["https://evmrpc-testnet.0g.ai"] },
  },
  blockExplorers: {
    default: { name: "0G Chainscan", url: "https://chainscan-galileo.0g.ai" },
  },
  testnet: true,
};

const projectId = process.env.NEXT_PUBLIC_WC_PROJECT_ID ?? "";

const config = getDefaultConfig({
  appName: "Lethe",
  projectId: projectId || "lethe-local-dev",
  chains: [sepolia, zeroGGalileo],
  transports: {
    [sepolia.id]: http(),
    [zeroGGalileo.id]: http(),
  },
  ssr: true,
});

export function Web3Provider({ children }: { children: ReactNode }) {
  const [queryClient] = useState(() => new QueryClient());
  return (
    <WagmiProvider config={config}>
      <QueryClientProvider client={queryClient}>
        <RainbowKitProvider
          theme={darkTheme({
            accentColor: "#a78bfa",
            accentColorForeground: "#0b0b0c",
            borderRadius: "small",
            fontStack: "system",
          })}
          modalSize="compact"
        >
          {children}
        </RainbowKitProvider>
      </QueryClientProvider>
    </WagmiProvider>
  );
}