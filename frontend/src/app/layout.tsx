import type { Metadata } from "next";
import type { ReactNode } from "react";

import "./globals.css";

export const metadata: Metadata = {
  title: "SmartCampus AI",
  description:
    "Plateforme agentique d'orientation universitaire (IIT / ISB) : conversation, orientation, préinscription et suivi.",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="fr">
      <body className="min-h-screen bg-background text-foreground antialiased">{children}</body>
    </html>
  );
}
