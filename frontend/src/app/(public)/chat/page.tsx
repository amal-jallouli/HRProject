"use client";

import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { getHealth, type HealthResponse } from "@/lib/api";

export default function ChatPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const checkHealth = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setHealth(await getHealth());
    } catch (err) {
      setHealth(null);
      setError(err instanceof Error ? err.message : "Erreur inconnue");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void checkHealth();
  }, [checkHealth]);

  return (
    <main className="container flex min-h-screen flex-col items-center justify-center gap-6 py-24">
      <div className="w-full max-w-lg space-y-4 rounded-lg border bg-card p-8 text-card-foreground shadow-sm">
        <h1 className="text-2xl font-semibold">Liaison avec l&apos;API</h1>
        <p className="text-sm text-muted-foreground">
          Cette page vérifie la communication avec le backend via{" "}
          <code className="rounded bg-muted px-1 py-0.5">GET /api/v1/health</code>.
        </p>

        <div className="rounded-md border bg-muted/40 p-4 text-sm">
          {loading && <p>Vérification en cours…</p>}

          {!loading && error && (
            <p className="text-destructive">
              API injoignable : {error}. Vérifiez que le backend tourne sur{" "}
              <code>NEXT_PUBLIC_API_URL</code>.
            </p>
          )}

          {!loading && health && (
            <dl className="space-y-1">
              <div className="flex justify-between gap-4">
                <dt className="text-muted-foreground">Statut</dt>
                <dd className="font-medium text-green-600">{health.status}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-muted-foreground">Service</dt>
                <dd className="font-medium">{health.service}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-muted-foreground">Version</dt>
                <dd className="font-medium">{health.version}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-muted-foreground">Environnement</dt>
                <dd className="font-medium">{health.environment}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-muted-foreground">Base de données</dt>
                <dd className="font-medium">{health.dependencies?.database ?? "—"}</dd>
              </div>
            </dl>
          )}
        </div>

        <Button onClick={() => void checkHealth()} disabled={loading}>
          Revérifier
        </Button>
      </div>
    </main>
  );
}
