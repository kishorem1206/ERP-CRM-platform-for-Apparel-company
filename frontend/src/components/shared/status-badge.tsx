import { cn } from "@/lib/utils";

type Status =
  | "draft" | "pending" | "approved" | "rejected"
  | "active" | "inactive" | "cancelled" | "completed"
  | "open" | "closed" | "delivered" | "partial"
  | string;

const colorMap: Record<string, string> = {
  draft:     "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300",
  pending:   "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300",
  approved:  "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300",
  rejected:  "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300",
  active:    "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300",
  inactive:  "bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400",
  cancelled: "bg-red-100 text-red-600 dark:bg-red-900/40 dark:text-red-300",
  completed: "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300",
  open:      "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300",
  closed:    "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400",
  delivered: "bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300",
  partial:   "bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-300",
};

interface StatusBadgeProps {
  status: Status;
  label?: string;
  className?: string;
}

export function StatusBadge({ status, label, className }: StatusBadgeProps) {
  const key = status.toLowerCase();
  const color = colorMap[key] ?? "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400";

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium capitalize",
        color,
        className
      )}
    >
      {label ?? status}
    </span>
  );
}
