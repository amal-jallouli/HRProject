/**
 * Client HTTP minimal vers l'API FastAPI.
 * L'URL de base provient de la variable d'environnement NEXT_PUBLIC_API_URL.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type HealthResponse = {
  status: string;
  service: string;
  version: string;
  environment: string;
  dependencies?: Record<string, string>;
};

/** Erreur levée lorsqu'une requête API échoue. */
export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    cache: "no-store",
    ...init,
  });

  if (!response.ok) {
    throw new ApiError(`Requête échouée (${response.status})`, response.status);
  }

  return (await response.json()) as T;
}

/** Récupère l'état de santé du backend. */
export function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/api/v1/health");
}
