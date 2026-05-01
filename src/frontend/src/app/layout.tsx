import type { Metadata } from "next";
import { Raleway, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { Web3Provider } from "@/components/Web3Provider";

// Roobert is the primary brand typeface in the monopo-saigon style guide,
// but it is not available on Google Fonts. The spec explicitly substitutes
// `system-ui, sans-serif`, so we expose a CSS variable that resolves to that
// stack and let any future self-hosted Roobert webfont layer in front of it
// without touching every component.
const raleway = Raleway({
  variable: "--font-raleway",
  weight: ["300", "400", "600"],
  subsets: ["latin"],
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains-mono",
  weight: ["400", "500"],
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Lethe — Medical bills, audited by AI consensus.",
  description:
    "Three independent AI agents audit your medical bill and dispute errors automatically. Forgotten by design.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${raleway.variable} ${jetbrainsMono.variable} h-full antialiased`}
    >
      <body className="min-h-full">
        <Web3Provider>{children}</Web3Provider>
      </body>
    </html>
  );
}