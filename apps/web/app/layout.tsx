import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "BioLoop CI — Démonstrateur local",
  description:
    "Déclaration, appariement, scénarios illustratifs et collecte simple pour le SIREXE Hackathon 2026.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="fr">
      <body>{children}</body>
    </html>
  );
}

