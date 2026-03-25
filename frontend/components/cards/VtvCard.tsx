"use client";

import { useState } from "react";
import type { VtvPbaData, VtvCabaData } from "@/lib/types";
import { formatDate } from "@/lib/utils";
import StatusBadge from "@/components/ui/StatusBadge";

interface VtvCardProps {
  data: VtvPbaData | VtvCabaData;
}

export default function VtvCard({ data }: VtvCardProps) {
  const [showAll, setShowAll] = useState(false);

  const isPba = data.fuente === "vtv_pba";
  const estado = data.estado;
  const verificaciones = data.verificaciones;
  const visible = showAll ? verificaciones : verificaciones.slice(0, 5);

  // Extract common fields depending on source
  const ultimaVerificacion = isPba
    ? (data as VtvPbaData).ultima_verificacion
    : (data as VtvCabaData).ultima_verificacion?.fecha_inspeccion ?? "-";

  const planta = isPba
    ? (data as VtvPbaData).planta
    : (data as VtvCabaData).ultima_verificacion?.planta ?? "-";

  const oblea = isPba
    ? (data as VtvPbaData).numero_oblea
    : (data as VtvCabaData).ultima_verificacion?.numero_oblea ?? "-";

  return (
    <div className="space-y-5">
      {/* Status badge */}
      <StatusBadge
        variant={estado === "Vigente" ? "success" : "danger"}
        label={estado}
      />

      {/* Key info */}
      <div className="grid grid-cols-3 gap-4 text-sm">
        <div>
          <span className="text-gray-400">Última verificación</span>
          <p className="font-medium text-white">{formatDate(ultimaVerificacion)}</p>
        </div>
        <div>
          <span className="text-gray-400">Planta</span>
          <p className="font-medium text-white">{planta}</p>
        </div>
        <div>
          <span className="text-gray-400">Oblea</span>
          <p className="font-medium text-white">{oblea || "-"}</p>
        </div>
      </div>

      {/* History table */}
      {verificaciones.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wide">
            Historial de verificaciones
          </h4>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-700 text-xs text-gray-500">
                  <th className="py-2 text-left font-medium">Fecha</th>
                  <th className="py-2 text-left font-medium">Planta</th>
                  <th className="py-2 text-left font-medium">Resultado</th>
                  <th className="py-2 text-left font-medium">Tipo</th>
                  <th className="py-2 text-left font-medium">Oblea</th>
                </tr>
              </thead>
              <tbody>
                {visible.map((v, i) => {
                  const fecha = isPba
                    ? (v as VtvPbaData["verificaciones"][0]).fecha_verificacion
                    : (v as VtvCabaData["verificaciones"][0]).fecha_inspeccion;
                  const plantaV = v.planta;
                  const resultado = v.resultado;
                  const tipo = isPba
                    ? (v as VtvPbaData["verificaciones"][0]).tipo_inspeccion
                    : (v as VtvCabaData["verificaciones"][0]).tipo_inspeccion;
                  const obleaV = isPba
                    ? (v as VtvPbaData["verificaciones"][0]).numero_oblea
                    : (v as VtvCabaData["verificaciones"][0]).numero_oblea;

                  const isAprobado =
                    resultado.toLowerCase().includes("aprobad") ||
                    resultado.toLowerCase().includes("apto");

                  return (
                    <tr key={i} className="border-b border-gray-800/50">
                      <td className="py-2 text-gray-300">{formatDate(fecha)}</td>
                      <td className="py-2 text-gray-300">{plantaV}</td>
                      <td className="py-2">
                        <StatusBadge
                          variant={isAprobado ? "success" : "danger"}
                          label={resultado}
                        />
                      </td>
                      <td className="py-2 text-gray-300">{tipo}</td>
                      <td className="py-2 text-gray-300">{obleaV || "-"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {verificaciones.length > 5 && (
            <button
              type="button"
              onClick={() => setShowAll((prev) => !prev)}
              className="text-xs text-blue-400 hover:text-blue-300 transition-colors"
            >
              {showAll
                ? "Mostrar menos"
                : `Ver todas (${verificaciones.length})`}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
