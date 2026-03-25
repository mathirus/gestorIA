import type { PlaceholderData } from "@/lib/types";

interface PlaceholderCardProps {
  data: PlaceholderData;
}

export default function PlaceholderCard({ data }: PlaceholderCardProps) {
  return (
    <div className="flex items-start gap-3">
      <svg
        className="mt-0.5 h-5 w-5 shrink-0 text-blue-400"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <circle cx="12" cy="12" r="10" />
        <path d="M12 16v-4M12 8h.01" />
      </svg>
      <p className="text-sm text-gray-400">{data.mensaje}</p>
    </div>
  );
}
