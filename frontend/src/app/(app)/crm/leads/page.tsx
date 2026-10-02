"use client";
import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Plus, Search, List, Kanban, X, Tag,
  Upload, UserCheck, Archive, ChevronDown, Download,
  Loader2, FileText, Pencil, Trash2,
} from "lucide-react";
import api from "@/lib/api";
import { getCurrentUserId } from "@/lib/auth";
import { SearchableSelect } from "@/components/shared/searchable-select";
import { ModalShell } from "@/components/shared/modal-shell";

// ── Palette ───────────────────────────────────────────────────────────────────
const INDIGO = "#0049A7";

const STATUS_HEX: Record<string, string> = {
  open: "#0049A7", won: "#0F78FF", lost: "#1D0DB0",
};

const TAG_COLORS = [
  "#0049A7", "#0049A7", "#8174F5", "#0F78FF", "#A096F7", "#A096F7", "#1D0DB0", "#0F78FF",
];

function tagColor(tag: string) {
  let h = 0;
  for (let i = 0; i < tag.length; i++) h = (h * 31 + tag.charCodeAt(i)) & 0xffff;
  return TAG_COLORS[h % TAG_COLORS.length];
}

function StatusBadge({ status }: { status: string }) {
  const color = STATUS_HEX[status?.toLowerCase()] ?? "#94A3B8";
  const label = status.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  return (
    <span
      className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded whitespace-nowrap"
      style={{ background: `${color}18`, color, fontSize: 11, fontWeight: 700 }}
    >
      <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: color }} />
      {label}
    </span>
  );
}

function StageBadge({ name }: { name: string }) {
  return (
    <span
      className="inline-flex items-center px-2 py-0.5 rounded whitespace-nowrap"
      style={{ background: `${INDIGO}14`, color: INDIGO, fontSize: 11, fontWeight: 700 }}
    >
      {name}
    </span>
  );
}

// ── Types ─────────────────────────────────────────────────────────────────────
interface PipelineStage {
  id: string;
  name: string;
  sort_order: number;
  is_won: boolean;
  is_lost: boolean;
  probability: number;
}

interface Pipeline {
  id: string;
  name: string;
  stages: PipelineStage[];
}

interface UserOption {
  id: string;
  name: string;
  email: string;
}

interface Lead {
  id: string;
  title: string;
  person_name: string | null;
  org_name: string | null;
  stage_name: string | null;
  stage_id: string | null;
  pipeline_id: string | null;
  lead_value: number | null;
  assigned_to_name: string | null;
  next_follow_up_at: string | null;
  follow_up_status: string;
  status: string;
  tags: string[];
}

interface KanbanLead {
  id: string;
  title: string;
  lead_value: number | null;
  person_name: string | null;
  org_name: string | null;
  assigned_to_name: string | null;
  tags: string[];
}

interface KanbanStage {
  stage_id: string;
  stage_name: string;
  leads: KanbanLead[];
}

interface ImportForm {
  pipeline_id: string;
  stage_id: string;
  assign_to: string;
}

interface ImportResult {
  total_rows: number;
  imported_rows: number;
  failed_rows: number;
  errors?: { row: number; message: string }[];
}

// ── CSV Template Download ─────────────────────────────────────────────────────
function downloadCsvTemplate() {
  const headers = "title,lead_value,person_name,organization_name,source_name,expected_close_date,description";
  const blob = new Blob([headers + "\n"], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "leads_import_template.csv";
  a.click();
  URL.revokeObjectURL(url);
}

// ── ImportLeadModal ───────────────────────────────────────────────────────────
function ImportLeadModal({
  onClose,
  pipelines,
  users,
}: {
  onClose: () => void;
  pipelines: Pipeline[];
  users: UserOption[];
}) {
  const queryClient = useQueryClient();
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [file, setFile] = useState<File | null>(null);
  const [rowCount, setRowCount] = useState(0);
  const [isDragging, setIsDragging] = useState(false);
  const [form, setForm] = useState<ImportForm>({ pipeline_id: "", stage_id: "", assign_to: "" });
  const [importResult, setImportResult] = useState<ImportResult | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const selectedPipeline = pipelines.find((p) => p.id === form.pipeline_id);
  const stageOptions = selectedPipeline?.stages.map((s) => ({ value: s.id, label: s.name })) ?? [];

  async function handleFile(f: File) {
    setFile(f);
    try {
      const text = await f.text();
      const lines = text.split("\n").filter((l) => l.trim());
      setRowCount(Math.max(0, lines.length - 1));
    } catch {
      setRowCount(0);
    }
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setIsDragging(false);
    const f = e.dataTransfer.files[0];
    if (f && f.name.endsWith(".csv")) handleFile(f);
  }

  const importMutation = useMutation({
    mutationFn: async () => {
      const fd = new FormData();
      fd.append("file", file!);
      fd.append("pipeline_id", form.pipeline_id);
      fd.append("stage_id", form.stage_id);
      if (form.assign_to) fd.append("assigned_to", form.assign_to);
      const res = await api.post("/crm/leads/import", fd);
      return res.data;
    },
    onSuccess: (data) => {
      setImportResult(data?.data ?? null);
      setStep(3);
      queryClient.invalidateQueries({ queryKey: ["crm-leads"] });
    },
  });

  function setf<K extends keyof ImportForm>(k: K, v: ImportForm[K]) {
    if (k === "pipeline_id") {
      setForm((f) => ({ ...f, pipeline_id: v as string, stage_id: "" }));
    } else {
      setForm((f) => ({ ...f, [k]: v }));
    }
  }

  return (
    <ModalShell maxWidth="max-w-lg" onClose={onClose}>
      {/* Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <div>
            <h2 className="text-lg font-semibold">Import Leads</h2>
            <div className="flex items-center gap-1.5 mt-1.5">
              {([1, 2, 3] as const).map((s) => (
                <span
                  key={s}
                  className="text-[11px] font-semibold px-2.5 py-0.5 rounded-full"
                  style={
                    s === step
                      ? { background: INDIGO, color: "#fff" }
                      : s < step
                      ? { background: `${INDIGO}20`, color: INDIGO }
                      : { background: "hsl(var(--muted))", color: "hsl(var(--muted-foreground))" }
                  }
                >
                  {s === 1 ? "Upload" : s === 2 ? "Configure" : "Result"}
                </span>
              ))}
            </div>
          </div>
          <button onClick={onClose} className="p-1 rounded hover:bg-muted transition-colors">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="p-6 space-y-4">
          {/* ── Step 1: Upload ── */}
          {step === 1 && (
            <>
              <div
                className={`rounded-2xl border-2 border-dashed flex flex-col items-center justify-center gap-3 p-10 cursor-pointer transition-all ${
                  isDragging
                    ? "border-primary bg-primary/5"
                    : "border-border hover:border-primary/50 hover:bg-muted/30"
                }`}
                onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
                onDragLeave={() => setIsDragging(false)}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
              >
                <div
                  className="w-12 h-12 rounded-full flex items-center justify-center"
                  style={{ background: `${INDIGO}14` }}
                >
                  <Upload className="h-6 w-6" style={{ color: INDIGO }} />
                </div>
                <div className="text-center">
                  <p className="text-sm font-medium">Drag and drop a CSV file here</p>
                  <p className="text-xs text-muted-foreground mt-0.5">or click to browse</p>
                </div>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".csv"
                  className="hidden"
                  onChange={(e) => {
                    const f = e.target.files?.[0];
                    if (f) handleFile(f);
                  }}
                />
              </div>

              {file && (
                <div
                  className="flex items-center gap-3 rounded-xl border p-3"
                  style={{ background: `${INDIGO}08`, borderColor: `${INDIGO}30` }}
                >
                  <FileText className="h-5 w-5 flex-shrink-0" style={{ color: INDIGO }} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{file.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {rowCount} data row{rowCount !== 1 ? "s" : ""} detected
                    </p>
                  </div>
                  <button
                    onClick={(e) => { e.stopPropagation(); setFile(null); setRowCount(0); }}
                    className="p-1 rounded hover:bg-muted transition-colors"
                  >
                    <X className="h-3.5 w-3.5 text-muted-foreground" />
                  </button>
                </div>
              )}

              <button
                onClick={downloadCsvTemplate}
                className="flex items-center gap-2 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
              >
                <Download className="h-3.5 w-3.5" />
                Download CSV template
              </button>
            </>
          )}

          {/* ── Step 2: Configure ── */}
          {step === 2 && (
            <>
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">
                  Pipeline <span className="text-destructive">*</span>
                </label>
                <SearchableSelect
                  options={pipelines.map((p) => ({ value: p.id, label: p.name }))}
                  value={form.pipeline_id}
                  onChange={(v) => setf("pipeline_id", v)}
                  placeholder="Select pipeline…"
                  accent={INDIGO}
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">
                  Stage <span className="text-destructive">*</span>
                </label>
                <SearchableSelect
                  options={stageOptions}
                  value={form.stage_id}
                  onChange={(v) => setf("stage_id", v)}
                  placeholder="Select stage…"
                  accent={INDIGO}
                  disabled={!form.pipeline_id}
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">
                  Assign To{" "}
                  <span className="text-muted-foreground font-normal">(optional)</span>
                </label>
                <SearchableSelect
                  options={users.map((u) => ({ value: u.id, label: u.name, meta: u.email }))}
                  value={form.assign_to}
                  onChange={(v) => setf("assign_to", v)}
                  placeholder="Select user…"
                  accent={INDIGO}
                />
              </div>
              {importMutation.isError && (
                <div className="rounded-xl p-3 text-sm" style={{ background: "#1D0DB010", border: "1px solid #1D0DB030", color: "#1D0DB0" }}>
                  Import failed. Please check your file and try again.
                </div>
              )}
            </>
          )}

          {/* ── Step 3: Result ── */}
          {step === 3 && importResult && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div
                  className="rounded-xl p-4 text-center"
                  style={{ background: "#0F78FF10", border: "1px solid #0F78FF30" }}
                >
                  <p className="text-2xl font-bold" style={{ color: "#0F78FF" }}>
                    {importResult.imported_rows}
                  </p>
                  <p className="text-xs text-muted-foreground mt-0.5">Imported</p>
                </div>
                <div
                  className="rounded-xl p-4 text-center"
                  style={{
                    background: importResult.failed_rows > 0 ? "#1D0DB010" : "#94A3B810",
                    border: `1px solid ${importResult.failed_rows > 0 ? "#1D0DB030" : "#94A3B830"}`,
                  }}
                >
                  <p
                    className="text-2xl font-bold"
                    style={{ color: importResult.failed_rows > 0 ? "#1D0DB0" : "#94A3B8" }}
                  >
                    {importResult.failed_rows}
                  </p>
                  <p className="text-xs text-muted-foreground mt-0.5">Failed</p>
                </div>
              </div>

              {importResult.errors && importResult.errors.length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-muted-foreground mb-2 uppercase tracking-wider">
                    Errors
                  </p>
                  <div className="rounded-xl border overflow-hidden max-h-48 overflow-y-auto">
                    {importResult.errors.map((err, i) => (
                      <div
                        key={i}
                        className="flex items-start gap-2 px-3 py-2 text-xs border-b last:border-0"
                      >
                        <span className="font-semibold text-muted-foreground shrink-0">
                          Row {err.row}
                        </span>
                        <span className="text-violet-600">{err.message}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-3 p-6 border-t">
          {step === 1 && (
            <>
              <button
                onClick={onClose}
                className="px-4 py-2 text-sm rounded-xl border border-input hover:bg-muted transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => setStep(2)}
                disabled={!file}
                className="px-4 py-2 text-sm rounded-xl text-white font-semibold transition-all hover:opacity-90 disabled:opacity-50"
                style={{ background: INDIGO }}
              >
                Next
              </button>
            </>
          )}
          {step === 2 && (
            <>
              <button
                onClick={() => setStep(1)}
                className="px-4 py-2 text-sm rounded-xl border border-input hover:bg-muted transition-colors"
              >
                Back
              </button>
              <button
                onClick={() => importMutation.mutate()}
                disabled={!form.pipeline_id || !form.stage_id || importMutation.isPending}
                className="flex items-center gap-2 px-4 py-2 text-sm rounded-xl text-white font-semibold transition-all hover:opacity-90 disabled:opacity-50"
                style={{ background: INDIGO }}
              >
                {importMutation.isPending ? (
                  <><Loader2 className="h-4 w-4 animate-spin" /> Importing…</>
                ) : (
                  "Start Import"
                )}
              </button>
            </>
          )}
          {step === 3 && (
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm rounded-xl text-white font-semibold transition-all hover:opacity-90"
              style={{ background: INDIGO }}
            >
              Done
            </button>
          )}
        </div>
    </ModalShell>
  );
}

// ── BulkActionBar ─────────────────────────────────────────────────────────────
function BulkActionBar({
  count,
  users,
  allStages,
  onAction,
  onClear,
  isPending,
}: {
  count: number;
  users: UserOption[];
  allStages: { value: string; label: string; meta: string }[];
  onAction: (action: string, value?: string) => void;
  onClear: () => void;
  isPending: boolean;
}) {
  const [active, setActive] = useState<"assign" | "stage" | "tag" | "archive" | null>(null);
  const [tagInput, setTagInput] = useState("");
  const [assignUser, setAssignUser] = useState("");
  const [moveStage, setMoveStage] = useState("");

  function execute(action: string, value?: string) {
    onAction(action, value);
    setActive(null);
    setTagInput("");
    setAssignUser("");
    setMoveStage("");
  }

  return (
    <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40">
      <div
        className="bg-card border border-border rounded-2xl px-4 py-3 flex items-center gap-2.5 flex-wrap"
        style={{ boxShadow: "var(--shadow-xl)" }}
      >
        {/* Count */}
        <span
          className="px-2.5 py-1 rounded"
          style={{ background: `${INDIGO}14`, color: INDIGO, fontSize: 11, fontWeight: 700 }}
        >
          {count} lead{count !== 1 ? "s" : ""} selected
        </span>
        <div className="w-px h-5 bg-border" />

        {/* Assign To */}
        <div className="relative">
          {active === "assign" && (
            <div className="absolute bottom-full mb-2 left-0 bg-card border border-border rounded-xl shadow-2xl p-3 w-64 z-50">
              <p className="text-xs font-semibold text-muted-foreground mb-2">Assign To</p>
              <SearchableSelect
                options={users.map((u) => ({ value: u.id, label: u.name, meta: u.email }))}
                value={assignUser}
                onChange={setAssignUser}
                placeholder="Select user…"
                accent={INDIGO}
              />
              <button
                className="mt-2 w-full px-3 py-1.5 text-xs font-semibold text-white rounded-lg disabled:opacity-50 transition-all hover:opacity-90"
                style={{ background: INDIGO }}
                disabled={!assignUser || isPending}
                onClick={() => execute("assign", assignUser)}
              >
                Apply
              </button>
            </div>
          )}
          <button
            onClick={() => setActive(active === "assign" ? null : "assign")}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg hover:bg-muted transition-colors"
          >
            <UserCheck className="h-3.5 w-3.5" />
            Assign To
            <ChevronDown className="h-3 w-3 text-muted-foreground" />
          </button>
        </div>

        {/* Move Stage */}
        <div className="relative">
          {active === "stage" && (
            <div className="absolute bottom-full mb-2 left-0 bg-card border border-border rounded-xl shadow-2xl p-3 w-64 z-50">
              <p className="text-xs font-semibold text-muted-foreground mb-2">Move to Stage</p>
              <SearchableSelect
                options={allStages}
                value={moveStage}
                onChange={setMoveStage}
                placeholder="Select stage…"
                accent={INDIGO}
              />
              <button
                className="mt-2 w-full px-3 py-1.5 text-xs font-semibold text-white rounded-lg disabled:opacity-50 transition-all hover:opacity-90"
                style={{ background: INDIGO }}
                disabled={!moveStage || isPending}
                onClick={() => execute("stage", moveStage)}
              >
                Apply
              </button>
            </div>
          )}
          <button
            onClick={() => setActive(active === "stage" ? null : "stage")}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg hover:bg-muted transition-colors"
          >
            Move Stage
            <ChevronDown className="h-3 w-3 text-muted-foreground" />
          </button>
        </div>

        {/* Add Tag */}
        <div className="relative">
          {active === "tag" && (
            <div className="absolute bottom-full mb-2 left-0 bg-card border border-border rounded-xl shadow-2xl p-3 w-52 z-50">
              <p className="text-xs font-semibold text-muted-foreground mb-2">Add Tag</p>
              <input
                className="w-full rounded-lg border border-input bg-background px-2.5 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                placeholder="Tag name…"
                value={tagInput}
                onChange={(e) => setTagInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && tagInput.trim()) execute("tag", tagInput.trim());
                }}
                autoFocus
              />
              <button
                className="mt-2 w-full px-3 py-1.5 text-xs font-semibold text-white rounded-lg disabled:opacity-50 transition-all hover:opacity-90"
                style={{ background: INDIGO }}
                disabled={!tagInput.trim() || isPending}
                onClick={() => execute("tag", tagInput.trim())}
              >
                Apply
              </button>
            </div>
          )}
          <button
            onClick={() => setActive(active === "tag" ? null : "tag")}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg hover:bg-muted transition-colors"
          >
            <Tag className="h-3.5 w-3.5" />
            Add Tag
            <ChevronDown className="h-3 w-3 text-muted-foreground" />
          </button>
        </div>

        {/* Archive */}
        {active === "archive" ? (
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">
              Archive {count} lead{count !== 1 ? "s" : ""}?
            </span>
            <button
              onClick={() => execute("archive")}
              disabled={isPending}
              className="px-2.5 py-1 text-xs font-semibold text-white rounded-lg bg-violet-500 hover:bg-violet-600 transition-colors disabled:opacity-50"
            >
              Confirm
            </button>
            <button
              onClick={() => setActive(null)}
              className="px-2.5 py-1 text-xs rounded-lg border hover:bg-muted transition-colors"
            >
              No
            </button>
          </div>
        ) : (
          <button
            onClick={() => setActive("archive")}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg hover:bg-violet-50 transition-colors"
            style={{ color: "#1D0DB0" }}
          >
            <Archive className="h-3.5 w-3.5" />
            Archive
          </button>
        )}

        <div className="w-px h-5 bg-border" />
        <button
          onClick={onClear}
          className="text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          Clear
        </button>
        {isPending && <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />}
      </div>
    </div>
  );
}

// ── Kanban Card ───────────────────────────────────────────────────────────────
function KanbanCard({
  lead,
  onDragStart,
}: {
  lead: KanbanLead;
  onDragStart: (e: React.DragEvent, leadId: string) => void;
}) {
  const router = useRouter();
  return (
    <div
      draggable
      onDragStart={(e) => onDragStart(e, lead.id)}
      onClick={() => router.push(`/crm/leads/${lead.id}`)}
      className="bg-card border border-border rounded-xl p-3 cursor-pointer hover:shadow-md hover:border-primary/30 transition-all duration-150 select-none"
    >
      <p className="text-sm font-medium leading-snug mb-1.5 line-clamp-2">{lead.title}</p>
      {lead.lead_value && lead.lead_value > 0 && (
        <p className="text-xs font-semibold mb-1" style={{ color: INDIGO }}>
          ₹{lead.lead_value.toLocaleString("en-IN")}
        </p>
      )}
      {lead.person_name && (
        <p className="text-xs text-muted-foreground truncate">{lead.person_name}</p>
      )}
      {lead.org_name && (
        <p className="text-xs text-muted-foreground truncate">{lead.org_name}</p>
      )}
      {lead.tags && lead.tags.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-2">
          {lead.tags.map((tag) => {
            const c = tagColor(tag);
            return (
              <span
                key={tag}
                className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-semibold"
                style={{ background: `${c}18`, color: c }}
              >
                <Tag className="h-2.5 w-2.5" />
                {tag}
              </span>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ── Kanban Column ─────────────────────────────────────────────────────────────
function KanbanColumn({
  stage,
  onDrop,
  onDragStart,
  dragOverStageId,
  setDragOverStageId,
}: {
  stage: KanbanStage;
  onDrop: (stageId: string) => void;
  onDragStart: (e: React.DragEvent, leadId: string) => void;
  dragOverStageId: string | null;
  setDragOverStageId: (id: string | null) => void;
}) {
  const isOver = dragOverStageId === stage.stage_id;

  return (
    <div
      className="flex-shrink-0 w-72 flex flex-col"
      onDragOver={(e) => { e.preventDefault(); setDragOverStageId(stage.stage_id); }}
      onDragLeave={() => setDragOverStageId(null)}
      onDrop={() => { onDrop(stage.stage_id); setDragOverStageId(null); }}
    >
      <div className="flex items-center justify-between mb-3 px-1">
        <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          {stage.stage_name}
        </p>
        <span
          className="px-2 py-0.5 rounded"
          style={{ background: `${INDIGO}14`, color: INDIGO, fontSize: 11, fontWeight: 700 }}
        >
          {stage.leads.length}
        </span>
      </div>
      <div
        className={`flex-1 min-h-[200px] rounded-xl transition-all duration-150 p-2 space-y-2 ${
          isOver
            ? "bg-primary/5 border-2 border-dashed border-primary/40"
            : "bg-muted/20 border-2 border-transparent"
        }`}
      >
        {stage.leads.map((lead) => (
          <KanbanCard key={lead.id} lead={lead} onDragStart={onDragStart} />
        ))}
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────
export default function LeadsPage() {
  const router = useRouter();
  const queryClient = useQueryClient();

  const [view, setView] = useState<"list" | "kanban">("list");
  const [search, setSearch] = useState("");
  const [assignedToFilter, setAssignedToFilter] = useState("");
  const [followUpDue, setFollowUpDue] = useState(false);
  const [page, setPage] = useState(1);
  const currentUserId = getCurrentUserId();
  const [showImport, setShowImport] = useState(false);
  const [dragLeadId, setDragLeadId] = useState<string | null>(null);
  const [dragOverStageId, setDragOverStageId] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const selectAllRef = useRef<HTMLInputElement>(null);

  // ── Data fetches ────────────────────────────────────────────────────────────
  const { data: leadsData, isLoading: leadsLoading } = useQuery({
    queryKey: ["crm-leads", page, search, assignedToFilter, followUpDue],
    queryFn: async () => {
      const params = new URLSearchParams({ page: String(page), page_size: "50" });
      if (search) params.set("search", search);
      if (assignedToFilter) params.set("assigned_to", assignedToFilter);
      if (followUpDue) params.set("follow_up_due", "true");
      const res = await api.get(`/crm/leads?${params}`);
      return res.data;
    },
    enabled: view === "list",
  });

  const { data: kanbanData, isLoading: kanbanLoading } = useQuery({
    queryKey: ["crm-leads-kanban"],
    queryFn: async () => {
      const res = await api.get("/crm/leads/kanban");
      return res.data;
    },
    enabled: view === "kanban",
  });

  const { data: pipelinesData } = useQuery({
    queryKey: ["crm-pipelines"],
    queryFn: async () => {
      const res = await api.get("/crm/pipelines");
      return res.data;
    },
  });

  const { data: usersData } = useQuery({
    queryKey: ["crm-assignable-users"],
    queryFn: async () => {
      const res = await api.get("/crm/assignable-users");
      return res.data;
    },
  });

  // ── Stage move mutation ──────────────────────────────────────────────────────
  const stageMutation = useMutation({
    mutationFn: ({ leadId, stageId, pipelineId }: { leadId: string; stageId: string; pipelineId: string }) =>
      api.patch(`/crm/leads/${leadId}/stage`, { stage_id: stageId, pipeline_id: pipelineId }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["crm-leads-kanban"] });
    },
  });

  // ── Delete mutation ──────────────────────────────────────────────────────────
  const deleteMutation = useMutation({
    mutationFn: (leadId: string) => api.delete(`/crm/leads/${leadId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["crm-leads"] });
      queryClient.invalidateQueries({ queryKey: ["crm-leads-kanban"] });
    },
  });

  // ── Bulk action mutation ─────────────────────────────────────────────────────
  const bulkMutation = useMutation({
    mutationFn: ({ action, value }: { action: string; value?: string }) =>
      api.post("/crm/leads/bulk-action", {
        lead_ids: Array.from(selectedIds),
        action,
        value,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["crm-leads"] });
      setSelectedIds(new Set());
    },
  });

  // ── Drag handlers ────────────────────────────────────────────────────────────
  function handleDragStart(e: React.DragEvent, leadId: string) {
    setDragLeadId(leadId);
    e.dataTransfer.effectAllowed = "move";
  }

  function handleDrop(targetStageId: string) {
    if (!dragLeadId) return;
    const stages: KanbanStage[] = kanbanData?.data?.stages ?? [];
    const sourceStage = stages.find((s) => s.leads.some((l) => l.id === dragLeadId));
    if (!sourceStage || sourceStage.stage_id === targetStageId) return;
    const pipelines: Pipeline[] = pipelinesData?.data ?? [];
    const pipeline = pipelines.find((p) =>
      p.stages.some((s) => s.id === targetStageId)
    );
    stageMutation.mutate({
      leadId: dragLeadId,
      stageId: targetStageId,
      pipelineId: pipeline?.id ?? "",
    });
    setDragLeadId(null);
  }

  // ── Derived data ─────────────────────────────────────────────────────────────
  const leads: Lead[] = leadsData?.data ?? [];
  const total: number = leadsData?.meta?.total ?? 0;
  const kanbanStages: KanbanStage[] = kanbanData?.data?.stages ?? [];
  const pipelines: Pipeline[] = pipelinesData?.data ?? [];
  const users: UserOption[] = usersData?.data ?? [];

  const allStages = pipelines.flatMap((p) =>
    p.stages.map((s) => ({ value: s.id, label: s.name, meta: p.name }))
  );

  const someSelected = selectedIds.size > 0;
  const allSelected = leads.length > 0 && leads.every((l) => selectedIds.has(l.id));

  // Indeterminate checkbox state
  useEffect(() => {
    if (selectAllRef.current) {
      selectAllRef.current.indeterminate = someSelected && !allSelected;
    }
  }, [someSelected, allSelected]);

  function toggleSelect(id: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }

  function toggleSelectAll() {
    if (allSelected) setSelectedIds(new Set());
    else setSelectedIds(new Set(leads.map((l) => l.id)));
  }

  function handleBulkAction(action: string, value?: string) {
    bulkMutation.mutate({ action, value });
  }

  return (
    <div className="p-8 space-y-8">
      {/* Page header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">
            CRM / LEADS
          </p>
          <h1 className="text-2xl font-bold tracking-tight">Leads</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Track and manage your sales pipeline.
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* View toggle */}
          <div className="flex items-center gap-1 p-1 bg-muted/50 rounded-xl">
            <button
              onClick={() => setView("list")}
              className={`p-2 rounded-lg transition-all duration-150 ${
                view === "list" ? "bg-card shadow-sm text-foreground" : "text-muted-foreground hover:text-foreground"
              }`}
              title="List view"
            >
              <List className="h-4 w-4" />
            </button>
            <button
              onClick={() => setView("kanban")}
              className={`p-2 rounded-lg transition-all duration-150 ${
                view === "kanban" ? "bg-card shadow-sm text-foreground" : "text-muted-foreground hover:text-foreground"
              }`}
              title="Kanban view"
            >
              <Kanban className="h-4 w-4" />
            </button>
          </div>
          <button
            onClick={() => setShowImport(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold border border-input hover:bg-muted transition-colors"
          >
            <Upload className="h-4 w-4" /> Import
          </button>
          <button
            onClick={() => router.push("/crm/leads/new")}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-white transition-all hover:opacity-90 active:scale-95"
            style={{ background: INDIGO }}
          >
            <Plus className="h-4 w-4" /> New Lead
          </button>
        </div>
      </div>

      {/* ── LIST VIEW ────────────────────────────────────────────────────────── */}
      {view === "list" && (
        <>
          <div className="flex flex-wrap gap-3 items-center">
            <div className="relative">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <input
                className="rounded-xl border border-input bg-background pl-8 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                placeholder="Search leads…"
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value);
                  setPage(1);
                  setSelectedIds(new Set());
                }}
              />
            </div>

            <div className="w-56">
              <SearchableSelect
                value={assignedToFilter}
                onChange={(v) => {
                  setAssignedToFilter(v);
                  setPage(1);
                  setSelectedIds(new Set());
                }}
                placeholder="Assigned To"
                accent={INDIGO}
                options={[
                  { value: "", label: "All employees" },
                  ...users.map((u) => ({ value: u.id, label: u.name, meta: u.email })),
                ]}
              />
            </div>

            {currentUserId && (
              <button
                onClick={() => {
                  setAssignedToFilter((prev) => (prev === currentUserId ? "" : currentUserId));
                  setPage(1);
                  setSelectedIds(new Set());
                }}
                className="px-3 py-2 rounded-xl text-sm font-semibold border transition-colors"
                style={
                  assignedToFilter === currentUserId
                    ? { background: `${INDIGO}14`, borderColor: `${INDIGO}40`, color: INDIGO }
                    : { borderColor: "hsl(var(--input))" }
                }
              >
                My Leads
              </button>
            )}

            <button
              onClick={() => {
                setFollowUpDue((prev) => !prev);
                setPage(1);
                setSelectedIds(new Set());
              }}
              className="px-3 py-2 rounded-xl text-sm font-semibold border transition-colors"
              style={
                followUpDue
                  ? { background: "#1D0DB014", borderColor: "#1D0DB040", color: "#1D0DB0" }
                  : { borderColor: "hsl(var(--input))" }
              }
            >
              Follow-ups Due
            </button>
          </div>

          <div className="bg-card border border-border rounded-2xl overflow-hidden">
            <div className="flex items-center justify-between px-6 py-4 border-b border-border">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
                  ALL LEADS
                </p>
                <p className="text-sm font-medium mt-0.5">
                  {total} record{total !== 1 ? "s" : ""}
                </p>
              </div>
            </div>
            <div className="p-6">
              <div className="rounded-lg border overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-muted/50 border-b">
                      <tr>
                        <th className="px-4 py-2.5 w-10">
                          <input
                            ref={selectAllRef}
                            type="checkbox"
                            checked={allSelected}
                            onChange={toggleSelectAll}
                            className="rounded border-gray-300 accent-[#0049A7]"
                          />
                        </th>
                        <th className="px-4 py-2.5 text-left font-medium text-muted-foreground whitespace-nowrap">
                          Title
                        </th>
                        <th className="px-4 py-2.5 text-left font-medium text-muted-foreground whitespace-nowrap">
                          Person
                        </th>
                        <th className="px-4 py-2.5 text-left font-medium text-muted-foreground whitespace-nowrap">
                          Organization
                        </th>
                        <th className="px-4 py-2.5 text-left font-medium text-muted-foreground whitespace-nowrap">
                          Stage
                        </th>
                        <th className="px-4 py-2.5 text-left font-medium text-muted-foreground whitespace-nowrap">
                          Value
                        </th>
                        <th className="px-4 py-2.5 text-left font-medium text-muted-foreground whitespace-nowrap">
                          Assigned To
                        </th>
                        <th className="px-4 py-2.5 text-left font-medium text-muted-foreground whitespace-nowrap">
                          Next Follow-up
                        </th>
                        <th className="px-4 py-2.5 text-left font-medium text-muted-foreground whitespace-nowrap">
                          Status
                        </th>
                        <th className="px-4 py-2.5 w-10" />
                      </tr>
                    </thead>
                    <tbody>
                      {leadsLoading ? (
                        <tr>
                          <td
                            colSpan={9}
                            className="text-center py-10 text-muted-foreground"
                          >
                            Loading…
                          </td>
                        </tr>
                      ) : leads.length === 0 ? (
                        <tr>
                          <td
                            colSpan={9}
                            className="text-center py-10 text-muted-foreground"
                          >
                            No leads found — click New Lead to add one
                          </td>
                        </tr>
                      ) : (
                        leads.map((lead) => (
                          <tr
                            key={lead.id}
                            onClick={() => router.push(`/crm/leads/${lead.id}`)}
                            className={`border-b last:border-0 transition-colors cursor-pointer ${
                              selectedIds.has(lead.id)
                                ? "bg-primary/5 hover:bg-primary/8"
                                : "hover:bg-muted/30"
                            }`}
                          >
                            <td
                              className="px-4 py-2.5 w-10"
                              onClick={(e) => { e.stopPropagation(); toggleSelect(lead.id); }}
                            >
                              <input
                                type="checkbox"
                                checked={selectedIds.has(lead.id)}
                                onChange={() => toggleSelect(lead.id)}
                                className="rounded border-gray-300 accent-[#0049A7]"
                              />
                            </td>
                            <td className="px-4 py-2.5 font-medium whitespace-nowrap">
                              {lead.title}
                            </td>
                            <td className="px-4 py-2.5 whitespace-nowrap text-muted-foreground">
                              {lead.person_name || "—"}
                            </td>
                            <td className="px-4 py-2.5 whitespace-nowrap text-muted-foreground">
                              {lead.org_name || "—"}
                            </td>
                            <td className="px-4 py-2.5 whitespace-nowrap">
                              {lead.stage_name ? (
                                <StageBadge name={lead.stage_name} />
                              ) : (
                                <span className="text-muted-foreground">—</span>
                              )}
                            </td>
                            <td className="px-4 py-2.5 whitespace-nowrap">
                              {lead.lead_value
                                ? `₹${lead.lead_value.toLocaleString("en-IN")}`
                                : "—"}
                            </td>
                            <td className="px-4 py-2.5 whitespace-nowrap text-muted-foreground">
                              {lead.assigned_to_name || "—"}
                            </td>
                            <td className="px-4 py-2.5 whitespace-nowrap">
                              {lead.next_follow_up_at ? (
                                <span style={{
                                  color: lead.follow_up_status === "scheduled" && new Date(lead.next_follow_up_at) < new Date()
                                    ? "#1D0DB0" : undefined,
                                }}>
                                  {new Date(lead.next_follow_up_at).toLocaleDateString("en-IN")}
                                </span>
                              ) : (
                                <span className="text-muted-foreground">—</span>
                              )}
                            </td>
                            <td className="px-4 py-2.5 whitespace-nowrap">
                              <StatusBadge status={lead.status} />
                            </td>
                            <td className="px-4 py-2.5 whitespace-nowrap">
                              <div className="flex items-center gap-0.5">
                                <button
                                  onClick={(e) => { e.stopPropagation(); router.push(`/crm/leads/${lead.id}`); }}
                                  className="p-1 rounded transition-colors hover:bg-muted text-muted-foreground"
                                  title="Edit lead"
                                >
                                  <Pencil className="h-3.5 w-3.5" />
                                </button>
                                <button
                                  onClick={(e) => { e.stopPropagation(); setConfirmDeleteId(lead.id); }}
                                  className="p-1 rounded transition-colors hover:bg-violet-50 text-muted-foreground hover:text-violet-500"
                                  title="Delete lead"
                                >
                                  <Trash2 className="h-3.5 w-3.5" />
                                </button>
                              </div>
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>

          {total > 50 && (
            <div className="flex justify-center gap-2">
              <button
                onClick={() => { setPage((p) => Math.max(1, p - 1)); setSelectedIds(new Set()); }}
                disabled={page === 1}
                className="px-3 py-1 rounded border border-input text-sm disabled:opacity-40"
              >
                Prev
              </button>
              <span className="text-sm text-muted-foreground self-center">Page {page}</span>
              <button
                onClick={() => { setPage((p) => p + 1); setSelectedIds(new Set()); }}
                disabled={leads.length < 50}
                className="px-3 py-1 rounded border border-input text-sm disabled:opacity-40"
              >
                Next
              </button>
            </div>
          )}
        </>
      )}

      {/* ── KANBAN VIEW ──────────────────────────────────────────────────────── */}
      {view === "kanban" && (
        <div className="relative">
          {kanbanLoading ? (
            <div className="flex items-center justify-center py-20 text-muted-foreground text-sm">
              Loading pipeline…
            </div>
          ) : kanbanStages.length === 0 ? (
            <div className="flex items-center justify-center py-20 text-muted-foreground text-sm">
              No pipeline stages configured yet.
            </div>
          ) : (
            <div className="flex gap-4 overflow-x-auto pb-6" style={{ minHeight: "70vh" }}>
              {kanbanStages.map((stage) => (
                <KanbanColumn
                  key={stage.stage_id}
                  stage={stage}
                  onDragStart={handleDragStart}
                  onDrop={handleDrop}
                  dragOverStageId={dragOverStageId}
                  setDragOverStageId={setDragOverStageId}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Floating Bulk Action Bar ──────────────────────────────────────────── */}
      {view === "list" && someSelected && (
        <BulkActionBar
          count={selectedIds.size}
          users={users}
          allStages={allStages}
          onAction={handleBulkAction}
          onClear={() => setSelectedIds(new Set())}
          isPending={bulkMutation.isPending}
        />
      )}

      {/* ── Modals ────────────────────────────────────────────────────────────── */}
      {showImport && (
        <ImportLeadModal
          onClose={() => setShowImport(false)}
          pipelines={pipelines}
          users={users}
        />
      )}

      {confirmDeleteId && (
        <ModalShell maxWidth="max-w-xs" onClose={() => setConfirmDeleteId(null)}>
          <div className="p-6">
            <p className="text-sm font-medium mb-1">Delete this lead?</p>
            <p className="text-xs text-muted-foreground mb-5">This action cannot be undone.</p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setConfirmDeleteId(null)}
                className="px-4 py-2 text-sm rounded-xl border border-input hover:bg-muted transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  deleteMutation.mutate(confirmDeleteId);
                  setConfirmDeleteId(null);
                }}
                disabled={deleteMutation.isPending}
                className="px-4 py-2 text-sm rounded-xl text-white font-semibold bg-violet-500 hover:bg-violet-600 transition-colors disabled:opacity-50"
              >
                Delete
              </button>
            </div>
          </div>
        </ModalShell>
      )}
    </div>
  );
}
