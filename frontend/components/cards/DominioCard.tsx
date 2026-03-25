import type { DominioData } from "@/lib/types";
import { cleanDnrpaField } from "@/lib/utils";

interface DominioCardProps {
  data: DominioData;
}

const fields: { key: keyof DominioData; label: string }[] = [
  { key: "registro_seccional", label: "Registro seccional" },
  { key: "localidad", label: "Localidad" },
  { key: "provincia", label: "Provincia" },
  { key: "direccion", label: "Dirección" },
  { key: "tipo_vehiculo", label: "Tipo de vehículo" },
];

export default function DominioCard({ data }: DominioCardProps) {
  if (!data.encontrado) {
    return (
      <div className="flex items-center gap-3 rounded-lg bg-yellow-500/10 px-4 py-3">
        <svg className="h-5 w-5 shrink-0 text-yellow-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
          <path d="M12 9v4m0 4h.01M10.29 3.86l-8.6 14.86A2 2 0 0 0 3.43 22h17.14a2 2 0 0 0 1.74-3.28l-8.6-14.86a2 2 0 0 0-3.42 0z" />
        </svg>
        <span className="text-sm font-medium text-yellow-400">
          Dominio no encontrado en la base de datos del DNRPA
        </span>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {fields.map(({ key, label }) => (
        <div
          key={key}
          className="flex items-start justify-between gap-4 border-b border-gray-800/50 py-2 text-sm last:border-0"
        >
          <span className="text-gray-400">{label}</span>
          <span className="text-right font-medium text-white">
            {cleanDnrpaField(data[key] as string)}
          </span>
        </div>
      ))}
    </div>
  );
}
