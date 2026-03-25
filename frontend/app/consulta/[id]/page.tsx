"use client";

import { useEffect, useState, use } from "react";
import Link from "next/link";
import CardWrapper from "@/components/cards/CardWrapper";
import CostosCard from "@/components/cards/CostosCard";
import PatentesCard from "@/components/cards/PatentesCard";
import VtvCard from "@/components/cards/VtvCard";
import DominioCard from "@/components/cards/DominioCard";
import MultasCard from "@/components/cards/MultasCard";
import PlaceholderCard from "@/components/cards/PlaceholderCard";
import ResumenEjecutivo from "@/components/resumen/ResumenEjecutivo";
import StatusIcon from "@/components/ui/StatusIcon";
import { obtenerConsulta, reintentarSubConsulta } from "@/lib/api";
import { TIPO_LABELS } from "@/lib/types";
import type {
  Consulta,
  SubConsulta,
  CostosData,
  PatentesData,
  VtvPbaData,
  VtvCabaData,
  DominioData,
  MultasCabaData,
  MultasPbaData,
  MultasNacionalData,
  PlaceholderData,
} from "@/lib/types";
import { descargarReporte } from "@/lib/pdf";
import { formatDate, formatCurrency, getProvinciaLabel } from "@/lib/utils";
import Navbar from "@/components/layout/Navbar";

/* ---------- Inline SVG icons for card types ---------- */

const IconCostos = (
  <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
    <line x1="12" y1="1" x2="12" y2="23" />
    <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
  </svg>
);

const IconPatentes = (
  <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
    <polyline points="14 2 14 8 20 8" />
    <line x1="16" y1="13" x2="8" y2="13" />
    <line x1="16" y1="17" x2="8" y2="17" />
    <polyline points="10 9 9 9 8 9" />
  </svg>
);

const IconVtv = (
  <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
    <path d="M9 12l2 2 4-4" />
  </svg>
);

const IconDominio = (
  <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
    <rect x="1" y="8" width="22" height="10" rx="2" />
    <circle cx="7" cy="18" r="2" />
    <circle cx="17" cy="18" r="2" />
    <path d="M5 8V6a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v2" />
  </svg>
);

const IconMultas = (
  <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
    <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
    <line x1="12" y1="9" x2="12" y2="13" />
    <line x1="12" y1="17" x2="12.01" y2="17" />
  </svg>
);

/* ---------- Helper: pick icon by tipo ---------- */

function getCardIcon(tipo: string) {
  if (tipo === "costos") return IconCostos;
  if (tipo.startsWith("patentes")) return IconPatentes;
  if (tipo.startsWith("vtv")) return IconVtv;
  if (tipo === "dominio") return IconDominio;
  if (tipo.startsWith("multas")) return IconMultas;
  return IconCostos;
}

/* ---------- Helper: summary text for collapsed card ---------- */

function getCardSummary(sub: SubConsulta): string {
  if (sub.estado !== "completado" || !sub.datos) return "";

  switch (sub.tipo) {
    case "costos": {
      const d = sub.datos as CostosData;
      return `Total: ${formatCurrency(d.total)}`;
    }
    case "patentes_caba":
    case "patentes_pba": {
      const d = sub.datos as PatentesData;
      return d.total_deuda > 0
        ? `Deuda: ${formatCurrency(d.total_deuda)}`
        : "Sin deuda";
    }
    case "vtv_caba":
    case "vtv_pba": {
      const d = sub.datos as VtvPbaData | VtvCabaData;
      return d.estado === "Vigente" ? "Vigente" : "Vencida";
    }
    case "dominio": {
      const d = sub.datos as DominioData;
      return d.encontrado ? d.registro_seccional : "No encontrado";
    }
    case "multas_caba":
    case "multas_pba":
    case "multas_nacional": {
      const d = sub.datos as MultasCabaData | MultasPbaData | MultasNacionalData;
      return d.tiene_infracciones
        ? `${d.cantidad} infracción${d.cantidad !== 1 ? "es" : ""}`
        : "Sin infracciones";
    }
    default:
      return "";
  }
}

/* ---------- Helper: render inner card by tipo ---------- */

function renderCardContent(sub: SubConsulta) {
  if (sub.estado !== "completado" || !sub.datos) return null;

  switch (sub.tipo) {
    case "costos":
      return <CostosCard data={sub.datos as CostosData} />;
    case "patentes_caba":
    case "patentes_pba":
      return <PatentesCard data={sub.datos as PatentesData} />;
    case "vtv_caba":
      return <VtvCard data={sub.datos as VtvCabaData} />;
    case "vtv_pba":
      return <VtvCard data={sub.datos as VtvPbaData} />;
    case "dominio":
      return <DominioCard data={sub.datos as DominioData} />;
    case "multas_caba":
      return <MultasCard data={sub.datos as MultasCabaData} variant="caba" />;
    case "multas_pba":
      return <MultasCard data={sub.datos as MultasPbaData} variant="pba" />;
    case "multas_nacional":
      return <MultasCard data={sub.datos as MultasNacionalData} variant="nacional" />;
    default:
      return <PlaceholderCard data={sub.datos as PlaceholderData} />;
  }
}

/* ========== PAGE COMPONENT ========== */

export default function ConsultaPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [consulta, setConsulta] = useState<Consulta | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let interval: NodeJS.Timeout;

    const fetchConsulta = async () => {
      try {
        const data = await obtenerConsulta(id);
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
      await reintentarSubConsulta(id, tipo);
      const data = await obtenerConsulta(id);
      setConsulta(data);
    } catch {
      // ignore
    }
  };

  const handleRetryAll = async () => {
    if (!consulta) return;
    const fallidos = consulta.sub_consultas.filter((s) => s.estado === "fallido");
    for (const sub of fallidos) {
      try {
        await reintentarSubConsulta(id, sub.tipo);
      } catch {
        // ignore
      }
    }
    const data = await obtenerConsulta(id);
    setConsulta(data);
  };

  /* ---------- States ---------- */

  if (error) {
    return (
      <main className="min-h-screen bg-gray-950 flex items-center justify-center">
        <div className="text-center space-y-4">
          <div className="mx-auto h-12 w-12 rounded-full bg-red-500/10 flex items-center justify-center">
            <svg className="h-6 w-6 text-red-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
              <circle cx="12" cy="12" r="10" />
              <path d="M15 9l-6 6M9 9l6 6" />
            </svg>
          </div>
          <p className="text-red-400 text-lg">{error}</p>
          <Link href="/" className="text-blue-400 hover:text-blue-300 text-sm inline-block">
            &larr; Volver al inicio
          </Link>
        </div>
      </main>
    );
  }

  if (!consulta) {
    return (
      <main className="min-h-screen bg-gray-950 flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <svg className="animate-spin h-8 w-8 text-blue-400" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          <p className="text-gray-400 text-sm">Cargando consulta...</p>
        </div>
      </main>
    );
  }

  /* ---------- Computed ---------- */

  const completados = consulta.sub_consultas.filter((s) => s.estado === "completado").length;
  const fallidos = consulta.sub_consultas.filter((s) => s.estado === "fallido").length;
  const terminados = consulta.sub_consultas.filter(
    (s) => s.estado === "completado" || s.estado === "fallido" || s.estado === "pendiente_24hs"
  ).length;
  const total = consulta.sub_consultas.length;
  const progressPct = total > 0 ? Math.round((terminados / total) * 100) : 0;
  const isDone = consulta.estado_general === "completado" || consulta.estado_general === "con_errores";

  return (
    <>
      <Navbar />
      <main className="min-h-screen bg-gray-950 px-4 pb-16 pt-20">
        <div className="max-w-2xl mx-auto">
          {/* ---- Header ---- */}
          <div className="mb-8">
            <div className="flex flex-wrap items-center gap-3 mb-1">
              <h1 className="text-3xl font-bold text-white tracking-wide font-mono">
                {consulta.patente}
              </h1>
              <span className="inline-flex items-center rounded-full border border-gray-700 bg-gray-800 px-3 py-1 text-xs font-medium text-gray-300">
                {getProvinciaLabel(consulta.provincia)}
              </span>
              <StatusIcon
                estado={
                  consulta.estado_general === "en_proceso"
                    ? "ejecutando"
                    : consulta.estado_general === "completado"
                      ? "completado"
                      : "fallido"
                }
                className="h-5 w-5"
              />
            </div>
            <p className="text-sm text-gray-500">
              Creada el {formatDate(consulta.created_at)}
            </p>

            {/* Progress bar */}
            <div className="mt-4">
              <div className="flex items-center justify-between text-xs text-gray-500 mb-1.5">
                <span>
                  {completados}/{total} completados
                  {fallidos > 0 && (
                    <span className="text-red-400 ml-2">
                      ({fallidos} con error)
                    </span>
                  )}
                </span>
                <span>{progressPct}%</span>
              </div>
              <div className="h-2 w-full rounded-full bg-gray-800 overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-700 ease-out ${
                    isDone
                      ? consulta.estado_general === "completado"
                        ? "bg-green-500"
                        : "bg-yellow-500"
                      : "bg-blue-500"
                  }`}
                  style={{ width: `${progressPct}%` }}
                />
              </div>
              {!isDone && (
                <p className="mt-1.5 text-xs text-gray-600 animate-pulse">
                  Actualizando cada 10 segundos...
                </p>
              )}
            </div>

            {/* Scraper status chips */}
            <div className="mt-4 flex flex-wrap gap-2">
              {consulta.sub_consultas.map((sub) => (
                <div
                  key={sub.tipo}
                  className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium border ${
                    sub.estado === "completado"
                      ? "border-green-500/30 bg-green-500/10 text-green-400"
                      : sub.estado === "fallido"
                        ? "border-red-500/30 bg-red-500/10 text-red-400"
                        : sub.estado === "ejecutando" || sub.estado === "reintentando"
                          ? "border-blue-500/30 bg-blue-500/10 text-blue-400"
                          : sub.estado === "pendiente_24hs"
                            ? "border-yellow-500/30 bg-yellow-500/10 text-yellow-400"
                            : "border-gray-700 bg-gray-800 text-gray-500"
                  }`}
                >
                  <StatusIcon estado={sub.estado} className="h-3 w-3" />
                  {(TIPO_LABELS[sub.tipo] || sub.tipo).replace(/ \(.*\)/, "")}
                </div>
              ))}
            </div>
          </div>

          {/* ---- Resumen Ejecutivo ---- */}
          {consulta.estado_general !== "en_proceso" && (
            <div className="mb-6">
              <ResumenEjecutivo consulta={consulta} />
            </div>
          )}

          {/* ---- Reintentar todos (si hay fallidos) ---- */}
          {isDone && fallidos > 0 && (
            <div className="mb-6">
              <button
                type="button"
                onClick={handleRetryAll}
                className="w-full rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm font-semibold text-red-400 transition-colors hover:bg-red-500/20 flex items-center justify-center gap-2"
              >
                <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
                  <path d="M4 12a8 8 0 0 1 14.93-4M20 12a8 8 0 0 1-14.93 4" />
                  <path d="M20 4v4h-4M4 20v-4h4" />
                </svg>
                Reintentar {fallidos} consulta{fallidos !== 1 ? "s" : ""} fallida{fallidos !== 1 ? "s" : ""}
              </button>
            </div>
          )}

          {/* ---- Cards (single column) ---- */}
          <div className="space-y-3 mb-8">
            {consulta.sub_consultas.map((sub) => (
              <CardWrapper
                key={sub.tipo}
                title={TIPO_LABELS[sub.tipo] || sub.tipo}
                icon={getCardIcon(sub.tipo)}
                status={sub.estado}
                summary={getCardSummary(sub)}
                error={sub.error}
                onRetry={() => handleRetry(sub.tipo)}
                defaultExpanded={false}
              >
                {renderCardContent(sub)}
              </CardWrapper>
            ))}
          </div>

          {/* ---- Actions ---- */}
          <div className="flex flex-wrap items-center justify-center gap-3">
            {isDone && (
              <button
                type="button"
                onClick={descargarReporte}
                className="no-print inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-blue-600 to-blue-500 px-6 py-3 text-sm font-semibold text-white transition-all hover:from-blue-500 hover:to-blue-400"
              >
                <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                  <polyline points="7 10 12 15 17 10" />
                  <line x1="12" y1="15" x2="12" y2="3" />
                </svg>
                Descargar reporte
              </button>
            )}
            <Link
              href="/"
              className="no-print inline-flex items-center gap-2 rounded-xl border border-gray-700 bg-gray-800 px-6 py-3 text-sm font-medium text-gray-300 transition-colors hover:bg-gray-700 hover:text-white"
            >
              &larr; Nueva consulta
            </Link>
          </div>
        </div>
      </main>
    </>
  );
}
