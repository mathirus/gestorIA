"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { listarConsultas } from "@/lib/api";
import StatusBadge from "@/components/ui/StatusBadge";
import { formatDate, getProvinciaLabel } from "@/lib/utils";
import type { Consulta } from "@/lib/types";
import Navbar from "@/components/layout/Navbar";

export default function HistorialPage() {
  const [consultas, setConsultas] = useState<Consulta[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const router = useRouter();

  useEffect(() => {
    const fetchConsultas = async () => {
      try {
        const data = await listarConsultas();
        setConsultas(data);
      } catch {
        setError("No se pudo conectar con el servidor");
      } finally {
        setLoading(false);
      }
    };

    fetchConsultas();
  }, []);

  function getStatusVariant(estado: string): "success" | "warning" | "neutral" {
    if (estado === "completado") return "success";
    if (estado === "con_errores") return "warning";
    return "neutral";
  }

  function getStatusLabel(estado: string): string {
    if (estado === "completado") return "Completado";
    if (estado === "con_errores") return "Con errores";
    return "En proceso";
  }

  const filtered = consultas.filter((c) =>
    c.patente.toLowerCase().includes(search.toLowerCase())
  );

  /* ---------- Loading ---------- */
  if (loading) {
    return (
      <>
        <Navbar />
        <main className="min-h-screen bg-gray-950 flex items-center justify-center">
          <div className="flex flex-col items-center gap-4">
            <svg
              className="animate-spin h-8 w-8 text-blue-400"
              viewBox="0 0 24 24"
              fill="none"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
              />
            </svg>
            <p className="text-gray-400 text-sm">Cargando historial...</p>
          </div>
        </main>
      </>
    );
  }

  /* ---------- Error ---------- */
  if (error) {
    return (
      <>
        <Navbar />
        <main className="min-h-screen bg-gray-950 flex items-center justify-center">
          <div className="text-center space-y-4">
            <div className="mx-auto h-12 w-12 rounded-full bg-red-500/10 flex items-center justify-center">
              <svg className="h-6 w-6 text-red-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                <circle cx="12" cy="12" r="10" />
                <path d="M15 9l-6 6M9 9l6 6" />
              </svg>
            </div>
            <p className="text-red-400">{error}</p>
            <p className="text-gray-500 text-sm">
              Verificá que el backend esté corriendo en el puerto correcto.
            </p>
            <div className="flex items-center justify-center gap-4">
              <button
                type="button"
                onClick={() => window.location.reload()}
                className="rounded-xl bg-gray-800 border border-gray-700 px-5 py-2.5 text-sm font-medium text-gray-300 transition-colors hover:bg-gray-700"
              >
                Reintentar
              </button>
              <Link href="/" className="text-blue-400 hover:text-blue-300 text-sm">
                &larr; Volver al inicio
              </Link>
            </div>
          </div>
        </main>
      </>
    );
  }

  /* ---------- Empty ---------- */
  if (consultas.length === 0) {
    return (
      <>
        <Navbar />
        <main className="min-h-screen bg-gray-950 flex items-center justify-center p-4">
          <div className="text-center space-y-4">
            <div className="mx-auto h-16 w-16 rounded-full bg-gray-800 flex items-center justify-center">
              <svg
                className="h-8 w-8 text-gray-600"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth={1.5}
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
              </svg>
            </div>
            <p className="text-gray-400 text-lg">No hay consultas previas</p>
            <Link
              href="/"
              className="inline-block rounded-xl bg-gradient-to-r from-blue-600 to-blue-500 px-6 py-3 text-sm font-semibold text-white transition-all hover:from-blue-500 hover:to-blue-400"
            >
              Crear primera consulta
            </Link>
          </div>
        </main>
      </>
    );
  }

  /* ---------- Table ---------- */
  return (
    <>
      <Navbar />
      <main className="min-h-screen bg-gray-950 p-4 pt-20">
        <div className="max-w-2xl mx-auto">
          <div className="mb-6">
            <h1 className="text-2xl font-bold text-white">Historial</h1>
            <p className="text-sm text-gray-500 mt-1">
              {consultas.length} consulta{consultas.length !== 1 ? "s" : ""} realizada
              {consultas.length !== 1 ? "s" : ""}
            </p>
          </div>

          {/* Search */}
          <div className="mb-4">
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value.toUpperCase())}
              placeholder="Buscar por patente..."
              className="w-full px-4 py-3 bg-gray-900 border border-gray-800 rounded-xl text-white placeholder-gray-600 text-sm focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/50 font-mono tracking-wide transition-colors"
            />
          </div>

          {filtered.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-gray-500 text-sm">
                No se encontraron consultas para &quot;{search}&quot;
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {filtered.map((c) => (
                <button
                  key={c.id}
                  type="button"
                  onClick={() => router.push(`/consulta/${c.id}`)}
                  className="w-full text-left rounded-xl border border-gray-800 bg-gray-900 px-5 py-4 transition-all hover:bg-gray-800/80 hover:border-gray-700 cursor-pointer group"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <span className="font-mono text-base font-bold text-white tracking-wide group-hover:text-blue-400 transition-colors">
                        {c.patente}
                      </span>
                      <span className="text-xs text-gray-500 hidden sm:inline">
                        {getProvinciaLabel(c.provincia)}
                      </span>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-xs text-gray-600 hidden sm:inline">
                        {formatDate(c.created_at)}
                      </span>
                      <StatusBadge
                        variant={getStatusVariant(c.estado_general)}
                        label={getStatusLabel(c.estado_general)}
                      />
                      <svg
                        className="h-4 w-4 text-gray-600 group-hover:text-gray-400 transition-colors"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth={2}
                      >
                        <path d="M9 18l6-6-6-6" />
                      </svg>
                    </div>
                  </div>
                  <div className="mt-1 sm:hidden">
                    <span className="text-xs text-gray-600">
                      {getProvinciaLabel(c.provincia)} &middot; {formatDate(c.created_at)}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          )}

          <div className="mt-8 text-center">
            <Link
              href="/"
              className="text-sm text-gray-400 hover:text-blue-400 transition-colors"
            >
              &larr; Nueva consulta
            </Link>
          </div>
        </div>
      </main>
    </>
  );
}
