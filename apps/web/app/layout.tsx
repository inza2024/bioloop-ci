import type { Metadata } from "next";
import "./globals.css";
import { PwaRuntime } from "./pwa-runtime";

export const metadata: Metadata = {
  title: "BioLoop CI — Démonstrateur local",
  description:
    "Déclaration, preuve P2, mesure P3, lot et scénarios illustratifs traçables pour le SIREXE Hackathon 2026.",
  manifest: "/manifest.webmanifest",
  applicationName: "BioLoop CI",
  appleWebApp: { capable: true, title: "BioLoop CI", statusBarStyle: "default" },
};

export const viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#123d2d",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="fr">
      <body>
        {children}
        <PwaRuntime />
      </body>
    </html>
  );
}
