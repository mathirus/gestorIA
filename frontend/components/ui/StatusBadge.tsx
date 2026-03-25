interface StatusBadgeProps {
  variant: "success" | "danger" | "warning" | "neutral";
  label: string;
}

const variantClasses: Record<StatusBadgeProps["variant"], string> = {
  success: "bg-green-500/15 text-green-400 border-green-500/30",
  danger: "bg-red-500/15 text-red-400 border-red-500/30",
  warning: "bg-yellow-500/15 text-yellow-400 border-yellow-500/30",
  neutral: "bg-gray-500/15 text-gray-400 border-gray-500/30",
};

export default function StatusBadge({ variant, label }: StatusBadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-medium ${variantClasses[variant]}`}
    >
      {label}
    </span>
  );
}
