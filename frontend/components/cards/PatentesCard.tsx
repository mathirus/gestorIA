import type { PatentesData } from "@/lib/types";
import { formatCurrency, formatDate } from "@/lib/utils";
import StatusBadge from "@/components/ui/StatusBadge";

interface PatentesCardProps {
  data: PatentesData;
}

export default function PatentesCard({ data }: PatentesCardProps) {
  const { vehiculo, deudas, total_deuda } = data;

  return (
    <div className="space-y-5">
      {/* Vehicle info grid */}
      <div className="grid grid-cols-2 gap-4 text-sm">
        <div>
          <span className="text-gray-400">Marca / Modelo</span>
          <p className="font-medium text-white">
            {vehiculo.marca} {vehiculo.modelo}
          </p>
        </div>
        <div>
          <span className="text-gray-400">Rubro / Uso</span>
          <p className="font-medium text-white">
            {vehiculo.rubro} / {vehiculo.uso}
          </p>
        </div>
        <div>
          <span className="text-gray-400">Estado</span>
          <p className="font-medium text-white">{vehiculo.estado}</p>
        </div>
        <div>
          <span className="text-gray-400">Categoría</span>
          <p className="font-medium text-white">{vehiculo.categoria}</p>
        </div>
      </div>

      {/* Debt section */}
      {total_deuda === 0 ? (
        <StatusBadge variant="success" label="Sin deuda" />
      ) : (
        <div className="space-y-3">
          <div className="rounded-lg bg-red-500/10 px-4 py-3">
            <span className="text-sm font-semibold text-red-400">
              Deuda total: {formatCurrency(total_deuda)}
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-700 text-xs text-gray-500">
                  <th className="py-2 text-left font-medium">Periodo</th>
                  <th className="py-2 text-left font-medium">Vencimiento</th>
                  <th className="py-2 text-right font-medium">Importe</th>
                </tr>
              </thead>
              <tbody>
                {deudas.map((d, i) => (
                  <tr key={i} className="border-b border-gray-800/50">
                    <td className="py-2 text-gray-300">
                      {d.anio} / Cuota {d.cuota}
                    </td>
                    <td className="py-2 text-gray-300">
                      {formatDate(d.fecha_vencimiento)}
                    </td>
                    <td className="py-2 text-right font-medium text-white">
                      {formatCurrency(d.importe_actualizado)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
