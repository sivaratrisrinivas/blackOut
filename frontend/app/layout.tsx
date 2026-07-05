import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import { Fraunces, Inter } from "next/font/google";
import "./globals.css";

const fraunces = Fraunces({
  subsets: ["latin"],
  variable: "--font-fraunces",
  display: "swap"
});

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap"
});

export const metadata: Metadata = {
  title: "BlackOut — Late-night decisions, morning clarity",
  description:
    "Reconstruct the previous Late-Night Window, recognize repeat patterns, and repair memory with feedback or forgetting."
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f9f8f4" },
    { media: "(prefers-color-scheme: dark)", color: "#1a1714" }
  ]
};

const themeInit = `(function(){try{var s=localStorage.getItem("blackout-theme");document.documentElement.setAttribute("data-theme",s||"light");}catch(e){}})();`;

export default function RootLayout({
  children
}: Readonly<{
  children: ReactNode;
}>) {
  return (
    <html lang="en" data-theme="light" className={`${inter.variable} ${fraunces.variable}`}>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInit }} />
      </head>
      <body>{children}</body>
    </html>
  );
}