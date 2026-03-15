"use client";
import { useEffect, useState, use } from "react";

interface SubConsulta {
  tipo: string;
  estado: string;
  intentos: number;
  datos: Record<string, unknown> | null;
  error: string | null;
  updated_at: string;
}

interface Consulta {
  id: number;
  patente: string;
  provincia: string;
  created_at: string;
  estado_general: string;
  sub_consultas: SubConsulta[];
}

const LABELS: Record<string, string> = {
  costos: "Calculadora de costos",
  patentes_caba: "Deuda de patentes (CABA)",
  patentes_pba: "Deuda de patentes (PBA)",
  vtv_caba: "VTV (CABA)",
  vtv_pba: "VTV (Provincia BA)",
  multas: "Multas de transito",
  dominio: "Informe de dominio",
};

const ESTADO_ICONS: Record<string, string> = {
  pendiente: "\u2B1A",
  ejecutando: "\u23F3",
  completado: "\u2705",
  fallido: "\u274C",
  reintentando: "\uD83D\uDD04",
  pendiente_24hs: "\uD83D\uDD50",
};

export default function ConsultaPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [consulta, setConsulta] = useState<Consulta | null>(null);
  const [error, setError] = useState("");
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set());

  useEffect(() => {
    let interval: NodeJS.Timeout;

    const fetchConsulta = async () => {
      try {
        const res = await fetch(`http://localhost:8000/api/consulta/${id}`);
        if (!res.ok) throw new Error("Consulta no encontrada");
        const data: Consulta = await res.json();
        setConsulta(data);

        if (data.estado_general === "completado" || data.estado_general === "con_errores") {
          clearInterval(interval);
        }
      } catch {
        setError("Error al obtener la consulta");
      }
    };

    fetchConsulta();
    interval = setInterval(fetchConsulta, 10000);

    return () => clearInterval(interval);
  }, [id]);

  const handleRetry = async (tipo: string) => {
    try {
      await fetch(`http://localhost:8000/api/consulta/${id}/reintentar/${tipo}`, {
        method: "POST",
      });
      // Re-fetch immediately
      const res = await fetch(`http://localhost:8000/api/consulta/${id}`);
      const data = await res.json();
      setConsulta(data);
    } catch {
      // ignore
    }
  };

  const toggleExpand = (tipo: string) => {
    setExpandedItems((prev) => {
      const next = new Set(prev);
      if (next.has(tipo)) next.delete(tipo);
      else next.add(tipo);
      return next;
    });
  };

  if (error) {
    return (
      <main className="min-h-screen bg-gray-950 flex items-center justify-center">
        <p className="text-red-400">{error}</p>
      </main>
    );
  }

  if (!consulta) {
    return (
      <main className="min-h-screen bg-gray-950 flex items-center justify-center">
        <p className="text-gray-400">Cargando...</p>
      </main>
    );
  }

  const completados = consulta.sub_consultas.filter((s) => s.estado === "completado").length;
  const total = consulta.sub_consultas.length;
  const fallidos = consulta.sub_consultas.filter((s) => s.estado === "fallido").length;

  return (
    <main className="min-h-screen bg-gray-950 p-4">
      <div className="max-w-2xl mx-auto">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-white">Consulta: {consulta.patente}</h1>
          <p className="text-gray-400">Provincia: {consulta.provincia === "caba" ? "CABA" : "Buenos Aires"}</p>
        </div>

        <div className="bg-gray-900 rounded-2xl border border-gray-800 overflow-hidden">
          {consulta.sub_consultas.map((sub) => (
            <div key={sub.tipo} className="border-b border-gray-800 last:border-b-0">
              <div
                className="flex items-center justify-between px-6 py-4 cursor-pointer hover:bg-gray-800/50"
                onClick={() => sub.datos && toggleExpand(sub.tipo)}
              >
                <div className="flex items-center gap-3">
                  <span className="text-xl">{ESTADO_ICONS[sub.estado] || "\u2B1A"}</span>
                  <div>
                    <p className="text-white font-medium">{LABELS[sub.tipo] || sub.tipo}</p>
                    {sub.estado === "ejecutando" && (
                      <p className="text-gray-500 text-sm">Intento {sub.intentos || 1}/3</p>
                    )}
                    {sub.estado === "fallido" && (
                      <p className="text-red-400 text-sm">{sub.error}</p>
                    )}
                    {sub.estado === "pendiente_24hs" && (
                      <p className="text-yellow-400 text-sm">Resultado estimado en ~24hs</p>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {sub.estado === "fallido" && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleRetry(sub.tipo);
                      }}
                      className="px-3 py-1 text-sm bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-lg"
                    >
                      Reintentar
                    </button>
                  )}
                  {sub.datos && (
                    <span className="text-gray-500 text-sm">
                      {expandedItems.has(sub.tipo) ? "\u25B2" : "\u25BC"}
                    </span>
                  )}
                </div>
              </div>

              {expandedItems.has(sub.tipo) && sub.datos && (
                <div className="px-6 pb-4">
                  <pre className="bg-gray-800 rounded-xl p-4 text-gray-300 text-sm overflow-auto max-h-64">
                    {JSON.stringify(sub.datos, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          ))}
        </div>

        <div className="mt-4 text-center text-gray-500 text-sm">
          {completados}/{total} completados
          {fallidos > 0 && ` \u00B7 ${fallidos} fallido${fallidos > 1 ? "s" : ""}`}
          {consulta.estado_general === "en_proceso" && " \u00B7 Actualizando cada 10s..."}
        </div>

        <div className="mt-6 text-center">
          <a href="/" className="text-blue-400 hover:text-blue-300 text-sm">
            &larr; Nueva consulta
          </a>
        </div>
      </div>
    </main>
  );
}
