interface TrafficLightProps {
  color: "green" | "yellow" | "red";
}

export default function TrafficLight({ color }: TrafficLightProps) {
  return (
    <div className="flex flex-col items-center gap-1.5 rounded-xl bg-gray-800 px-2 py-3">
      <div
        className={`h-4 w-4 rounded-full transition-all ${
          color === "red"
            ? "bg-red-500 shadow-[0_0_8px_2px_rgba(239,68,68,0.5)]"
            : "bg-red-900/40"
        }`}
      />
      <div
        className={`h-4 w-4 rounded-full transition-all ${
          color === "yellow"
            ? "bg-yellow-500 shadow-[0_0_8px_2px_rgba(234,179,8,0.5)]"
            : "bg-yellow-900/40"
        }`}
      />
      <div
        className={`h-4 w-4 rounded-full transition-all ${
          color === "green"
            ? "bg-green-500 shadow-[0_0_8px_2px_rgba(34,197,94,0.5)]"
            : "bg-green-900/40"
        }`}
      />
    </div>
  );
}
