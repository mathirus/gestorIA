"use client";

import { useState, useRef, useEffect } from "react";
import type { EstadoConsulta } from "@/lib/types";
import StatusIcon from "@/components/ui/StatusIcon";
import SkeletonCard from "@/components/ui/SkeletonCard";

interface CardWrapperProps {
  title: string;
  icon: React.ReactNode;
  status: EstadoConsulta;
  summary?: string;
  error?: string | null;
  onRetry?: () => void;
  children: React.ReactNode;
  defaultExpanded?: boolean;
}

export default function CardWrapper({
  title,
  icon,
  status,
  summary,
  error,
  onRetry,
  children,
  defaultExpanded = false,
}: CardWrapperProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const contentRef = useRef<HTMLDivElement>(null);
  const [contentHeight, setContentHeight] = useState(0);

  useEffect(() => {
    if (contentRef.current) {
      setContentHeight(contentRef.current.scrollHeight);
    }
  }, [expanded, status, children]);

  const statusLabel: Record<string, string> = {
    pendiente: "En cola",
    ejecutando: "Consultando...",
    reintentando: "Reintentando...",
    pendiente_24hs: "Pendiente 24hs",
    fallido: "Error",
    completado: "",
  };

  const headerSummary =
    status === "completado" && summary
      ? summary
      : statusLabel[status] || "";

  const borderColor =
    status === "fallido"
      ? "border-red-800/60"
      : status === "completado"
        ? "border-gray-800"
        : "border-gray-800";

  return (
    <div
      className={`overflow-hidden rounded-2xl border ${borderColor} bg-gray-900 transition-colors`}
    >
      {/* Header */}
      <button
        type="button"
        onClick={() => setExpanded((prev) => !prev)}
        className="flex w-full items-center justify-between px-5 py-4 text-left transition-colors hover:bg-gray-800/50"
      >
        <div className="flex items-center gap-3 min-w-0">
          <span className="text-gray-400 shrink-0">{icon}</span>
          <div className="min-w-0">
            <span className="text-sm font-semibold text-white block">
              {title}
            </span>
            {headerSummary && !expanded && (
              <span
                className={`text-xs block mt-0.5 truncate ${
                  status === "fallido"
                    ? "text-red-400"
                    : status === "ejecutando" || status === "reintentando"
                      ? "text-blue-400"
                      : status === "pendiente_24hs"
                        ? "text-yellow-400"
                        : "text-gray-500"
                }`}
              >
                {headerSummary}
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <StatusIcon estado={status} className="h-5 w-5" />
          <svg
            className={`h-4 w-4 text-gray-500 transition-transform duration-200 ${
              expanded ? "rotate-180" : ""
            }`}
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M6 9l6 6 6-6" />
          </svg>
        </div>
      </button>

      {/* Animated Body */}
      <div
        className="overflow-hidden transition-[max-height] duration-300 ease-in-out"
        style={{ maxHeight: expanded ? `${contentHeight + 20}px` : "0px" }}
      >
        <div ref={contentRef} className="border-t border-gray-800">
          {(status === "ejecutando" || status === "reintentando") && (
            <SkeletonCard />
          )}

          {status === "fallido" && (
            <div className="p-5">
              <div className="flex items-start gap-3 rounded-xl bg-red-500/10 border border-red-500/20 p-4">
                <svg
                  className="h-5 w-5 shrink-0 text-red-400 mt-0.5"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth={2}
                >
                  <circle cx="12" cy="12" r="10" />
                  <path d="M15 9l-6 6M9 9l6 6" />
                </svg>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-red-400">
                    No se pudo obtener la información
                  </p>
                  <p className="text-xs text-red-400/70 mt-1">
                    {error || "Error de conexión con el servicio externo."}
                  </p>
                </div>
                {onRetry && (
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      onRetry();
                    }}
                    className="shrink-0 rounded-lg bg-red-500/20 px-4 py-2 text-xs font-semibold text-red-400 transition-colors hover:bg-red-500/30"
                  >
                    Reintentar
                  </button>
                )}
              </div>
            </div>
          )}

          {status === "pendiente" && (
            <div className="p-5">
              <div className="flex items-center gap-2 text-gray-500">
                <div className="h-2 w-2 rounded-full bg-gray-600 animate-pulse" />
                <p className="text-sm">En cola, esperando turno...</p>
              </div>
            </div>
          )}

          {status === "pendiente_24hs" && (
            <div className="p-5">
              <div className="flex items-center gap-3 rounded-xl bg-yellow-500/10 border border-yellow-500/20 p-4">
                <svg
                  className="h-5 w-5 shrink-0 text-yellow-400"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth={2}
                >
                  <circle cx="12" cy="12" r="10" />
                  <path d="M12 6v6l4 2" />
                </svg>
                <p className="text-sm text-yellow-400">
                  Disponible en las próximas 24 horas.
                </p>
              </div>
            </div>
          )}

          {status === "completado" && (
            <div className="p-5">{children}</div>
          )}
        </div>
      </div>
    </div>
  );
}
