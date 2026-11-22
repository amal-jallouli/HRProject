import Link from "next/link";

import { Button } from "@/components/ui/button";

export default function HomePage() {
  return (
    <main className="container flex min-h-screen flex-col items-center justify-center gap-8 py-24 text-center">
      <div className="space-y-4">
        <span className="inline-block rounded-full bg-secondary px-3 py-1 text-xs font-medium text-secondary-foreground">
          Projet IA générative · IIT / ISB
        </span>
        <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">SmartCampus AI</h1>
        <p className="mx-auto max-w-2xl text-lg text-muted-foreground">
          Plateforme agentique d&apos;orientation universitaire. Dialoguez en français, dialecte
          tunisien ou Arabizi et recevez une orientation personnalisée, justifiée et suivie jusqu&apos;à
          l&apos;inscription.
        </p>
      </div>
      <div className="flex flex-wrap items-center justify-center gap-4">
        <Button asChild>
          <Link href="/chat">Tester la liaison API</Link>
        </Button>
        <Button asChild variant="outline">
          <Link href="/login">Se connecter</Link>
        </Button>
      </div>
    </main>
  );
}
