import { LucideIcon, TrendingUp, TrendingDown } from "lucide-react";
import { cn } from "@/lib/utils";

interface KpiCardProps {
  label: string;
  value: string;
  sub?: string;
  icon?: LucideIcon;
  trend?: { value: number; label?: string };
  iconColor?: string;
  className?: string;
}

export function KpiCard({ label, value, sub, icon: Icon, trend, iconColor = "text-primary", className }: KpiCardProps) {
  const positive = trend && trend.value >= 0;

  return (
    <div className={cn("bg-card border rounded-lg p-4 space-y-2", className)}>
      <div className="flex items-center justify-between">
        <span className="text-xs text-muted-foreground">{label}</span>
        {Icon && <Icon className={cn("h-4 w-4", iconColor)} />}
      </div>
      <p className="text-2xl font-semibold tracking-tight">{value}</p>
      <div className="flex items-center gap-2">
        {trend && (
          <span
            className={cn(
              "flex items-center gap-0.5 text-xs font-medium",
              positive ? "text-blue-600" : "text-violet-500"
            )}
          >
            {positive ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
            {Math.abs(trend.value)}%
          </span>
        )}
        {sub && <span className="text-xs text-muted-foreground">{sub}</span>}
      </div>
    </div>
  );
}
