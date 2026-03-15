"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";

export default function Home() {
  const [patente, setPatente] = useState("");
  const [provincia, setProvincia] = useState("caba");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const res = await fetch("http://localhost:8000/api/consulta", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ patente, provincia }),
      });

      if (!res.ok) throw new Error("Error al crear consulta");
      const data = await res.json();
      router.push(`/consulta/${data.id}`);
    } catch (err) {
      setError("No se pudo conectar con el servidor");
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-gray-950 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <h1 className="text-3xl font-bold text-white text-center mb-2">gestorIA</h1>
        <p className="text-gray-400 text-center mb-8">Consulta vehicular inteligente</p>

        <form onSubmit={handleSubmit} className="bg-gray-900 rounded-2xl p-8 border border-gray-800">
          <div className="mb-6">
            <label className="block text-gray-300 text-sm font-medium mb-2">Patente</label>
            <input
              type="text"
              value={patente}
              onChange={(e) => setPatente(e.target.value.toUpperCase())}
              placeholder="Ej: AB123CD"
              className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 text-lg tracking-wider"
              required
              maxLength={10}
            />
          </div>

          <div className="mb-8">
            <label className="block text-gray-300 text-sm font-medium mb-2">Provincia</label>
            <select
              value={provincia}
              onChange={(e) => setProvincia(e.target.value)}
              className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-xl text-white focus:outline-none focus:border-blue-500"
            >
              <option value="caba">CABA</option>
              <option value="buenos_aires">Buenos Aires</option>
            </select>
          </div>

          {error && <p className="text-red-400 text-sm mb-4">{error}</p>}

          <button
            type="submit"
            disabled={loading || !patente}
            className="w-full py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:text-gray-500 text-white font-semibold rounded-xl transition-colors"
          >
            {loading ? "Consultando..." : "Consultar"}
          </button>
        </form>
      </div>
    </main>
  );
}
