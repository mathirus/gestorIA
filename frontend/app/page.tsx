"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { crearConsulta } from "@/lib/api";

export default function Home() {
  const [patente, setPatente] = useState("");
  const [dni, setDni] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const data = await crearConsulta(patente, dni || undefined);
      router.push(`/consulta/${data.id}`);
    } catch {
      setError("No se pudo conectar con el servidor");
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-gray-950 flex items-center justify-center p-4">
      <div className="w-full max-w-md relative">
        {/* Glow effect behind form */}
        <div className="absolute -inset-4 rounded-3xl bg-gradient-to-br from-blue-600/20 via-blue-500/5 to-transparent blur-2xl pointer-events-none" />

        <div className="relative">
          <h1 className="text-5xl font-extrabold text-white text-center mb-2 tracking-tight">
            gestorIA
          </h1>
          <p className="text-gray-400 text-center mb-10 text-lg">
            Consulta vehicular inteligente
          </p>

          <form
            onSubmit={handleSubmit}
            className="bg-gray-900 rounded-2xl p-8 border border-gray-800 shadow-2xl shadow-black/50"
          >
            <div className="mb-6">
              <label className="block text-gray-300 text-sm font-medium mb-2">
                Patente
              </label>
              <input
                type="text"
                value={patente}
                onChange={(e) => setPatente(e.target.value.toUpperCase())}
                placeholder="Ej: AB123CD"
                className="w-full px-5 py-4 bg-gray-800 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/50 text-xl font-mono tracking-widest text-center transition-colors"
                required
                maxLength={10}
              />
            </div>

            <div className="mb-8">
              <label className="block text-gray-300 text-sm font-medium mb-2">
                DNI del titular del vehículo
              </label>
              <input
                type="text"
                value={dni}
                onChange={(e) => setDni(e.target.value.replace(/\D/g, ""))}
                placeholder="Ej: 12345678"
                className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/50 transition-colors"
                required
                maxLength={11}
              />
              <p className="mt-2 text-xs text-gray-500">
                Las multas nacionales (ANSV) se consultan por persona, no por vehículo. Ingresá el DNI del actual titular.
              </p>
            </div>

            {error && (
              <div className="mb-4 rounded-lg bg-red-500/10 border border-red-500/20 px-4 py-3">
                <p className="text-red-400 text-sm">{error}</p>
              </div>
            )}

            <button
              type="submit"
              disabled={loading || !patente || !dni}
              className="w-full py-3.5 bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 disabled:from-gray-700 disabled:to-gray-700 disabled:text-gray-500 text-white font-semibold rounded-xl transition-all flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <svg
                    className="animate-spin h-5 w-5 text-white"
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
                  Consultando...
                </>
              ) : (
                "Consultar"
              )}
            </button>
          </form>

          <div className="mt-6 text-center">
            <Link
              href="/historial"
              className="text-sm text-gray-400 hover:text-blue-400 transition-colors"
            >
              Ver historial de consultas &rarr;
            </Link>
          </div>
        </div>
      </div>
    </main>
  );
}
