import type { EstadoConsulta } from "@/lib/types";

interface StatusIconProps {
  estado: EstadoConsulta;
  className?: string;
}

export default function StatusIcon({ estado, className = "w-5 h-5" }: StatusIconProps) {
  switch (estado) {
    case "pendiente":
      return (
        <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
          <circle cx="12" cy="12" r="10" className="text-gray-500" />
        </svg>
      );

    case "ejecutando":
      return (
        <svg className={`${className} animate-spin text-blue-400`} viewBox="0 0 24 24" fill="none">
          <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth={3} strokeOpacity={0.25} />
          <path
            d="M12 2a10 10 0 0 1 10 10"
            stroke="currentColor"
            strokeWidth={3}
            strokeLinecap="round"
          />
        </svg>
      );

    case "completado":
      return (
        <svg className={`${className} text-green-400`} viewBox="0 0 24 24" fill="none">
          <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth={2} />
          <path
            d="M8 12l3 3 5-5"
            stroke="currentColor"
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      );

    case "fallido":
      return (
        <svg className={`${className} text-red-400`} viewBox="0 0 24 24" fill="none">
          <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth={2} />
          <path
            d="M15 9l-6 6M9 9l6 6"
            stroke="currentColor"
            strokeWidth={2}
            strokeLinecap="round"
          />
        </svg>
      );

    case "reintentando":
      return (
        <svg className={`${className} animate-spin text-blue-400`} viewBox="0 0 24 24" fill="none">
          <path
            d="M4 12a8 8 0 0 1 14.93-4M20 12a8 8 0 0 1-14.93 4"
            stroke="currentColor"
            strokeWidth={2}
            strokeLinecap="round"
          />
          <path
            d="M20 4v4h-4M4 20v-4h4"
            stroke="currentColor"
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      );

    case "pendiente_24hs":
      return (
        <svg className={`${className} text-yellow-400`} viewBox="0 0 24 24" fill="none">
          <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth={2} />
          <path
            d="M12 6v6l4 2"
            stroke="currentColor"
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      );

    default:
      return null;
  }
}
