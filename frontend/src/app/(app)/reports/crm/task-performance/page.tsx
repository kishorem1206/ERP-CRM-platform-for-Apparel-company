"use client";

import { ReportPage } from "@/components/reports/report-page";
import { Column } from "@/components/shared/data-table";

const RED = "#1D0DB0";

type Row = {
  employee_name: string; pending: number; in_progress: number; overdue: number; completed_this_week: number;
};

const columns: Column<Row>[] = [
  { key: "employee_name", header: "Employee", sortable: true },
  { key: "pending", header: "Pending", sortable: true },
  { key: "in_progress", header: "In Progress" },
  {
    key: "overdue", header: "Overdue",
    render: (r) => <span style={{ color: r.overdue > 0 ? RED : undefined, fontWeight: r.overdue > 0 ? 700 : 400 }}>{r.overdue}</span>,
    sortable: true,
  },
  { key: "completed_this_week", header: "Completed This Week", sortable: true },
];

export default function TaskPerformancePage() {
  return (
    <ReportPage<Row>
      breadcrumb="REPORTS / CRM"
      title="Employee Task Performance"
      description="Pending, in-progress, overdue, and completed-this-week tasks per employee."
      queryKey="report-task-performance"
      endpoint="/reports/employee-task-performance"
      dateRange={false}
      columns={columns}
    />
  );
}
