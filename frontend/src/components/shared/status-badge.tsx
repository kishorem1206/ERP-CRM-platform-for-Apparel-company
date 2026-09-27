import { cn } from "@/lib/utils";

type Status =
  | "draft" | "pending" | "approved" | "rejected"
  | "active" | "inactive" | "cancelled" | "completed"
  | "open" | "closed" | "delivered" | "partial"
  | string;

const colorMap: Record<string, string> = {
  draft:     "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300",
  pending:   "bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-300",
  approved:  "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300",
  rejected:  "bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-300",
  active:    "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300",
  inactive:  "bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400",
  cancelled: "bg-violet-100 text-violet-600 dark:bg-violet-900/40 dark:text-violet-300",
  completed: "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300",
  open:      "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300",
  closed:    "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400",
  delivered: "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300",
  partial:   "bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-300",
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
        "inline-flex items-center rounded px-2 py-0.5 text-[11px] font-bold capitalize",
        color,
        className
      )}
    >
      {label ?? status}
    </span>
  );
}
