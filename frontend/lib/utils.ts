export function formatCurrency(amount: number | string): string {
  const num = typeof amount === "string" ? parseFloat(amount.replace(/\./g, "").replace(",", ".")) : amount;
  if (isNaN(num)) return "$0";
  return new Intl.NumberFormat("es-AR", {
    style: "currency",
    currency: "ARS",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(num);
}

export function formatDate(dateStr: unknown): string {
  if (!dateStr) return "-";
  if (typeof dateStr === "object" && dateStr !== null) {
    const obj = dateStr as Record<string, number>;
    if (obj.day && obj.month && obj.year) return `${obj.day}/${obj.month}/${obj.year}`;
    return JSON.stringify(dateStr);
  }
  if (typeof dateStr !== "string") return String(dateStr);
  // Handle formats: "2026-03-19T14:01:23", "21/01/2023 11:57:28", "10-07-2015"
  const cleaned = dateStr.split(" ")[0]; // Remove time part
  const parts = cleaned.includes("/") ? cleaned.split("/") : cleaned.includes("-") ? cleaned.split("-") : [];
  if (parts.length === 3) {
    // If first part is 4 digits, it's YYYY-MM-DD
    if (parts[0].length === 4) return `${parts[2]}/${parts[1]}/${parts[0]}`;
    // DD-MM-YYYY or DD/MM/YYYY → normalize to DD/MM/YYYY
    return `${parts[0]}/${parts[1]}/${parts[2]}`;
  }
  return dateStr;
}

export function cleanDnrpaField(value: string): string {
  if (!value) return "-";
  return value.replace(/^\.\s*/, "").replace(/\t/g, " ").trim() || "-";
}

export function getProvinciaLabel(provincia: string): string {
  return provincia === "caba" ? "CABA" : provincia === "buenos_aires" ? "Buenos Aires" : provincia;
}
