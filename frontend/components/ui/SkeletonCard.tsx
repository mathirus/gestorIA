export default function SkeletonCard() {
  return (
    <div className="space-y-3 p-4">
      <div className="h-4 w-3/4 animate-pulse rounded bg-gray-700" />
      <div className="h-4 w-1/2 animate-pulse rounded bg-gray-700" />
      <div className="h-4 w-5/6 animate-pulse rounded bg-gray-700" />
      <div className="h-4 w-2/3 animate-pulse rounded bg-gray-700" />
    </div>
  );
}
