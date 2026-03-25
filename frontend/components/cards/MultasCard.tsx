import type {
  MultasCabaData,
  MultasPbaData,
  MultasNacionalData,
} from "@/lib/types";
import { formatCurrency, formatDate } from "@/lib/utils";
import StatusBadge from "@/components/ui/StatusBadge";

interface MultasCardProps {
  data: MultasCabaData | MultasPbaData | MultasNacionalData;
  variant: "caba" | "pba" | "nacional";
}

export default function MultasCard({ data, variant }: MultasCardProps) {
  // No infractions
  if (!data.tiene_infracciones) {
    return (
      <div className="space-y-3">
        <StatusBadge variant="success" label="Sin infracciones" />
        {data.mensaje && (
          <p className="text-sm text-gray-400">{data.mensaje}</p>
        )}
      </div>
    );
  }

  // Has infractions
  return (
    <div className="space-y-4">
      {/* Red banner */}
      <div className="rounded-lg bg-red-500/10 px-4 py-3">
        <span className="text-sm font-semibold text-red-400">
          {data.cantidad} infracción{data.cantidad !== 1 ? "es" : ""} detectada
          {data.cantidad !== 1 ? "s" : ""}
        </span>
      </div>

      {/* CABA table */}
      {variant === "caba" && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-700 text-xs text-gray-500">
                <th className="py-2 text-left font-medium">Acta</th>
                <th className="py-2 text-left font-medium">Fecha</th>
                <th className="py-2 text-right font-medium">Monto</th>
              </tr>
            </thead>
            <tbody>
              {(data as MultasCabaData).infracciones.map((inf, i) => (
                <tr key={i} className="border-b border-gray-800/50">
                  <td className="py-2 text-gray-300">{inf.nro_acta}</td>
                  <td className="py-2 text-gray-300">{formatDate(inf.fecha)}</td>
                  <td className="py-2 text-right font-medium text-white">
                    {formatCurrency(inf.monto)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {(data as MultasCabaData).monto_total && (
            <div className="mt-3 flex items-center justify-between rounded-xl bg-red-500/10 px-4 py-2">
              <span className="text-xs font-semibold text-gray-400">TOTAL</span>
              <span className="text-sm font-bold text-white">
                {formatCurrency((data as MultasCabaData).monto_total!)}
              </span>
            </div>
          )}
        </div>
      )}

      {/* PBA table */}
      {variant === "pba" && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-700 text-xs text-gray-500">
                <th className="py-2 text-left font-medium">Acta</th>
                <th className="py-2 text-left font-medium">Generación</th>
                <th className="py-2 text-left font-medium">Vencimiento</th>
                <th className="py-2 text-right font-medium">Importe</th>
                <th className="py-2 text-left font-medium">Estado</th>
              </tr>
            </thead>
            <tbody>
              {(data as MultasPbaData).infracciones.map((inf, i) => (
                <tr key={i} className="border-b border-gray-800/50">
                  <td className="py-2 text-gray-300">{inf.nro_acta}</td>
                  <td className="py-2 text-gray-300">
                    {formatDate(inf.fecha_generacion)}
                  </td>
                  <td className="py-2 text-gray-300">
                    {formatDate(inf.fecha_vencimiento)}
                  </td>
                  <td className="py-2 text-right font-medium text-white">
                    {formatCurrency(inf.importe)}
                  </td>
                  <td className="py-2">
                    <StatusBadge
                      variant={
                        inf.estado_cupon.toLowerCase().includes("pag")
                          ? "success"
                          : "warning"
                      }
                      label={inf.estado_cupon}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Nacional */}
      {variant === "nacional" && (
        <div className="space-y-2">
          {data.mensaje && (
            <p className="text-sm text-gray-400">{data.mensaje}</p>
          )}
          {(data as MultasNacionalData).infracciones.length > 0 && (
            <div className="rounded-lg border border-gray-800 p-3">
              <pre className="whitespace-pre-wrap text-xs text-gray-300">
                {JSON.stringify(
                  (data as MultasNacionalData).infracciones,
                  null,
                  2
                )}
              </pre>
            </div>
          )}
        </div>
      )}

      {/* Info message fallback */}
      {data.mensaje &&
        !data.tiene_infracciones &&
        data.cantidad === 0 && (
          <p className="text-sm text-gray-400">{data.mensaje}</p>
        )}
    </div>
  );
}
