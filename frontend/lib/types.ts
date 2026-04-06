// ---- Estado y Tipo enums ----
export type TipoConsulta =
  | "costos"
  | "patentes_caba"
  | "patentes_pba"
  | "vtv_pba"
  | "vtv_caba"
  | "multas_caba"
  | "multas_pba"
  | "multas_nacional"
  | "dominio";

export type EstadoConsulta =
  | "pendiente"
  | "ejecutando"
  | "completado"
  | "fallido"
  | "reintentando"
  | "pendiente_24hs";

// ---- API Response ----
export interface SubConsulta {
  tipo: TipoConsulta;
  estado: EstadoConsulta;
  intentos: number;
  datos: ScraperData | null;
  error: string | null;
  updated_at: string;
}

export interface Consulta {
  id: number;
  patente: string;
  provincia: string | null; // null hasta que DNRPA la detecte
  created_at: string;
  estado_general: "en_proceso" | "completado" | "con_errores";
  sub_consultas: SubConsulta[];
}

// ---- Datos por scraper ----
export interface CostosData {
  valuacion_fiscal: number;
  arancel_dnrpa: number;
  arancel_dnrpa_porcentaje: number;
  sellos: number;
  sellos_porcentaje: number;
  verificacion_policial: number;
  total: number;
  provincia: string;
}

export interface VehiculoInfo {
  dominio: string;
  marca: string;
  modelo: string;
  rubro: string;
  uso: string;
  estado: string;
  categoria: string | number;
  fecha_alta?: string;
}

export interface DeudaItem {
  anio: number;
  cuota: number;
  fecha_vencimiento: string;
  importe_original?: number;
  importe_actualizado: number;
}

export interface PatentesData {
  fuente: string;
  patente: string;
  vehiculo: VehiculoInfo;
  deudas: DeudaItem[];
  total_deuda: number;
  cantidad_cuotas_impagas: number;
}

export interface VtvVerificacionPba {
  fecha_verificacion: string;
  fecha_vencimiento: string;
  resultado: string;
  planta: string;
  numero_oblea: string;
  tipo_inspeccion: string;
}

export interface VtvPbaData {
  fuente: "vtv_pba";
  patente: string;
  estado: "Vigente" | "Vencida" | "Sin datos";
  numero_oblea: string;
  ultima_verificacion: string;
  vencimiento: string;
  planta: string;
  resultado_ultima: string;
  verificaciones: VtvVerificacionPba[];
  cantidad_verificaciones: number;
}

export interface VtvVerificacionCaba {
  dominio: string;
  tipo_vehiculo: string;
  planta: string;
  fecha_inspeccion: string;
  tipo_inspeccion: string;
  fecha_vencimiento: string;
  numero_oblea: string | null;
  resultado: string;
  kilometraje: string | null;
}

export interface VtvCabaData {
  fuente: "vtv_caba";
  patente: string;
  estado: "Vigente" | "Vencida" | "Sin datos";
  ultima_verificacion: VtvVerificacionCaba;
  verificaciones: VtvVerificacionCaba[];
  cantidad_verificaciones: number;
}

export interface DominioData {
  fuente: "dnrpa";
  patente: string;
  encontrado: boolean;
  registro_seccional: string;
  localidad: string;
  provincia: string;
  direccion: string;
  tipo_vehiculo: string;
}

export interface InfraccionCaba {
  nro_acta: string;
  fecha: string;
  descripcion: string;
  monto: string;
}

export interface MultasCabaData {
  fuente: "multas_caba";
  patente: string;
  tiene_infracciones: boolean;
  infracciones: InfraccionCaba[];
  cantidad: number;
  monto_total?: string;
  mensaje?: string;
}

export interface InfraccionPba {
  nro_acta: string;
  dominio: string;
  fecha_generacion: string;
  fecha_vencimiento: string;
  importe: string;
  estado_cupon: string;
  estado_causa: string;
}

export interface MultasPbaData {
  fuente: "multas_pba";
  patente: string;
  tiene_infracciones: boolean;
  infracciones: InfraccionPba[];
  cantidad: number;
  mensaje?: string;
}

export interface MultasNacionalData {
  fuente: "multas_nacional";
  patente: string;
  dni?: string;
  tiene_infracciones: boolean;
  infracciones: unknown[];
  cantidad: number;
  mensaje?: string;
}

export interface PlaceholderData {
  fuente: string;
  patente: string;
  mensaje: string;
}

export type ScraperData =
  | CostosData
  | PatentesData
  | VtvPbaData
  | VtvCabaData
  | DominioData
  | MultasCabaData
  | MultasPbaData
  | MultasNacionalData
  | PlaceholderData;

// ---- Labels amigables ----
export const TIPO_LABELS: Record<string, string> = {
  costos: "Costos de transferencia",
  patentes_caba: "Deuda de patentes (CABA)",
  patentes_pba: "Deuda de patentes (PBA)",
  vtv_caba: "VTV (CABA)",
  vtv_pba: "VTV (Provincia BA)",
  multas_caba: "Multas de tránsito (CABA)",
  multas_pba: "Multas de tránsito (PBA)",
  multas_nacional: "Multas nacionales (ANSV)",
  dominio: "Informe de dominio (DNRPA)",
};
