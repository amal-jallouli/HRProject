import Link from "next/link";

import { Button } from "@/components/ui/button";

export default function LoginPage() {
  return (
    <main className="container flex min-h-screen flex-col items-center justify-center gap-6 py-24">
      <div className="w-full max-w-sm space-y-4 rounded-lg border bg-card p-8 text-center text-card-foreground shadow-sm">
        <h1 className="text-2xl font-semibold">Connexion</h1>
        <p className="text-sm text-muted-foreground">
          Page en cours de construction. L&apos;authentification sera implémentée dans un prochain
          épic.
        </p>
        <Button asChild variant="outline">
          <Link href="/">Retour à l&apos;accueil</Link>
        </Button>
      </div>
    </main>
  );
}
