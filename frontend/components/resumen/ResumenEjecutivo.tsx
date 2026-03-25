"use client";

import type {
  Consulta,
  PatentesData,
  MultasCabaData,
  MultasPbaData,
  MultasNacionalData,
  VtvPbaData,
  VtvCabaData,
  CostosData,
} from "@/lib/types";
import { formatCurrency } from "@/lib/utils";
import TrafficLight from "@/components/ui/TrafficLight";

interface ResumenEjecutivoProps {
  consulta: Consulta;
}

export default function ResumenEjecutivo({ consulta }: ResumenEjecutivoProps) {
  if (consulta.estado_general === "en_proceso") return null;

  const subs = consulta.sub_consultas;

  // Compute total debt from patentes
  let totalDeuda = 0;
  for (const sc of subs) {
    if (
      (sc.tipo === "patentes_caba" || sc.tipo === "patentes_pba") &&
      sc.estado === "completado" &&
      sc.datos
    ) {
      totalDeuda += (sc.datos as PatentesData).total_deuda ?? 0;
    }
  }

  // Compute total multas
  let cantidadMultas = 0;
  for (const sc of subs) {
    if (
      (sc.tipo === "multas_caba" ||
        sc.tipo === "multas_pba" ||
        sc.tipo === "multas_nacional") &&
      sc.estado === "completado" &&
      sc.datos
    ) {
      const d = sc.datos as MultasCabaData | MultasPbaData | MultasNacionalData;
      cantidadMultas += d.cantidad ?? 0;
    }
  }

  // VTV status
  let vtvStatus: "Vigente" | "Vencida" | "Sin datos" | "No consultada" =
    "No consultada";
  for (const sc of subs) {
    if (
      (sc.tipo === "vtv_caba" || sc.tipo === "vtv_pba") &&
      sc.estado === "completado" &&
      sc.datos
    ) {
      vtvStatus = (sc.datos as VtvPbaData | VtvCabaData).estado;
    }
  }

  // Costo transferencia
  let costoTransferencia = 0;
  for (const sc of subs) {
    if (sc.tipo === "costos" && sc.estado === "completado" && sc.datos) {
      costoTransferencia = (sc.datos as CostosData).total;
    }
  }

  // Problem count
  let problemCount = 0;
  if (totalDeuda > 0) problemCount++;
  if (cantidadMultas > 0) problemCount++;
  if (vtvStatus === "Vencida") problemCount++;

  const lightColor: "green" | "yellow" | "red" =
    problemCount === 0 ? "green" : problemCount <= 2 ? "yellow" : "red";

  const verdictLabel =
    problemCount === 0
      ? "APTO PARA TRANSFERENCIA"
      : problemCount <= 2
        ? "CON OBSERVACIONES"
        : "REQUIERE ATENCIÓN";

  const verdictColor =
    problemCount === 0
      ? "text-green-400"
      : problemCount <= 2
        ? "text-yellow-400"
        : "text-red-400";

  return (
    <div className="rounded-2xl border border-gray-800 bg-gray-900 p-6">
      {/* Header row */}
      <div className="flex items-center gap-5">
        <TrafficLight color={lightColor} />
        <div>
          <p className={`text-sm font-bold tracking-wide ${verdictColor}`}>
            {verdictLabel}
          </p>
          <p className="mt-1 text-sm text-gray-400">
            {problemCount === 0
              ? "Este vehículo está en regla"
              : `${problemCount} problema${problemCount !== 1 ? "s" : ""} detectado${problemCount !== 1 ? "s" : ""}`}
          </p>
        </div>
      </div>

      {/* Quick stat cards */}
      <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatCard
          label="Deuda patentes"
          value={totalDeuda > 0 ? formatCurrency(totalDeuda) : "Sin deuda"}
          variant={totalDeuda > 0 ? "danger" : "success"}
        />
        <StatCard
          label="Multas"
          value={
            cantidadMultas > 0
              ? `${cantidadMultas} infracción${cantidadMultas !== 1 ? "es" : ""}`
              : "Sin multas"
          }
          variant={cantidadMultas > 0 ? "danger" : "success"}
        />
        <StatCard
          label="VTV"
          value={vtvStatus}
          variant={
            vtvStatus === "Vigente"
              ? "success"
              : vtvStatus === "Vencida"
                ? "danger"
                : "neutral"
          }
        />
        <StatCard
          label="Costo transferencia"
          value={costoTransferencia > 0 ? formatCurrency(costoTransferencia) : "-"}
          variant="neutral"
        />
      </div>
    </div>
  );
}

function StatCard({
  label,
  value,
  variant,
}: {
  label: string;
  value: string;
  variant: "success" | "danger" | "neutral";
}) {
  const borderColor =
    variant === "success"
      ? "border-green-500/30"
      : variant === "danger"
        ? "border-red-500/30"
        : "border-gray-700";

  const valueColor =
    variant === "success"
      ? "text-green-400"
      : variant === "danger"
        ? "text-red-400"
        : "text-white";

  return (
    <div
      className={`rounded-xl border ${borderColor} bg-gray-800/50 px-4 py-3`}
    >
      <p className="text-xs text-gray-500">{label}</p>
      <p className={`mt-1 text-sm font-semibold ${valueColor}`}>{value}</p>
    </div>
  );
}
