import type { CostosData } from "@/lib/types";
import { formatCurrency } from "@/lib/utils";

interface CostosCardProps {
  data: CostosData;
}

export default function CostosCard({ data }: CostosCardProps) {
  return (
    <div className="space-y-3">
      <table className="w-full text-sm">
        <tbody>
          <tr className="border-b border-gray-800">
            <td className="py-2 text-gray-400">
              Arancel DNRPA ({data.arancel_dnrpa_porcentaje}%)
            </td>
            <td className="py-2 text-right font-medium text-white">
              {formatCurrency(data.arancel_dnrpa)}
            </td>
          </tr>
          <tr className="border-b border-gray-800">
            <td className="py-2 text-gray-400">
              Sellos provinciales ({data.sellos_porcentaje}%)
            </td>
            <td className="py-2 text-right font-medium text-white">
              {formatCurrency(data.sellos)}
            </td>
          </tr>
          <tr className="border-b border-gray-800">
            <td className="py-2 text-gray-400">Verificación policial</td>
            <td className="py-2 text-right font-medium text-white">
              {formatCurrency(data.verificacion_policial)}
            </td>
          </tr>
        </tbody>
      </table>

      {/* Total */}
      <div className="flex items-center justify-between rounded-xl bg-blue-500/10 px-4 py-3">
        <span className="text-sm font-bold text-white">TOTAL</span>
        <span className="text-lg font-bold text-white">
          {formatCurrency(data.total)}
        </span>
      </div>

      {/* Footer */}
      <div className="rounded-lg bg-yellow-500/10 border border-yellow-500/20 px-3 py-2">
        <p className="text-xs text-yellow-400">
          Valuación fiscal estimada: {formatCurrency(data.valuacion_fiscal)} (valor de referencia hardcodeado, no refleja el valor real del vehículo)
        </p>
      </div>
    </div>
  );
}
