import { Consulta } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

export async function crearConsulta(patente: string, dni?: string): Promise<Consulta> {
  // provincia se auto-detecta desde DNRPA en el backend
  const body: Record<string, string> = { patente };
  if (dni) body.dni = dni;
  const res = await fetch(`${API_BASE}/api/consulta`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error("Error al crear consulta");
  return res.json();
}

export async function obtenerConsulta(id: number | string): Promise<Consulta> {
  const res = await fetch(`${API_BASE}/api/consulta/${id}`);
  if (!res.ok) throw new Error("Consulta no encontrada");
  return res.json();
}

export async function reintentarSubConsulta(consultaId: number | string, tipo: string): Promise<void> {
  await fetch(`${API_BASE}/api/consulta/${consultaId}/reintentar/${tipo}`, {
    method: "POST",
  });
}

export async function listarConsultas(): Promise<Consulta[]> {
  const res = await fetch(`${API_BASE}/api/consultas`);
  if (!res.ok) throw new Error("Error al listar consultas");
  return res.json();
}
