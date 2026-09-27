"use client";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ModalShell, Field, Input, Textarea, ModalActions, SearchableSelect } from "./ModalShell";
import api from "@/lib/api";

interface Props {
  open: boolean;
  onClose: () => void;
}

export function NewFabricRunModal({ open, onClose }: Props) {
  const qc = useQueryClient();
  const [form, setForm] = useState({
    run_number: "",
    construction: "",
    input_lot_id: "",
    input_qty: "",
    machine: "",
    started_at: "",
    notes: "",
  });
  const [err, setErr] = useState<string | null>(null);

  const lots = useQuery({
    queryKey: ["material-lots-yarn-fabric"],
    queryFn: async () => {
      const r = await api.get("/materials/lots", { params: { page_size: 100 } });
      return (r.data.data ?? []) as { id: string; lot_number: string; material_type: string }[];
    },
    enabled: open,
  });

  const mut = useMutation({
    mutationFn: () => api.post("/materials/fabric-runs", {
      run_number: form.run_number || undefined,
      construction: form.construction || undefined,
      input_lot_id: form.input_lot_id || undefined,
      input_qty: form.input_qty ? Number(form.input_qty) : undefined,
      machine: form.machine || undefined,
      started_at: form.started_at || undefined,
      notes: form.notes || undefined,
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["fabric-runs"] });
      onClose();
      setForm({ run_number: "", construction: "", input_lot_id: "", input_qty: "", machine: "", started_at: "", notes: "" });
    },
    onError: (e: unknown) => {
      const msg = (e as { response?: { data?: { error?: { message?: string } } } })
        ?.response?.data?.error?.message;
      setErr(msg ?? "Failed to create fabric run");
    },
  });

  function set(k: string, v: string) { setForm((f) => ({ ...f, [k]: v })); setErr(null); }

  const yarnFabricLots = (lots.data ?? []).filter((l) => l.material_type === "yarn" || l.material_type === "fabric");

  return (
    <ModalShell
      open={open}
      onClose={onClose}
      title="New Fabric Run"
      subtitle="Track a knitting or weaving production run."
      footer={
        <form onSubmit={(e) => { e.preventDefault(); mut.mutate(); }}>
          <ModalActions onClose={onClose} loading={mut.isPending} label="Create Run" />
        </form>
      }
    >
      <form
        onSubmit={(e) => { e.preventDefault(); mut.mutate(); }}
        className="space-y-4"
      >
        <div className="grid grid-cols-2 gap-3">
          <Field label="Run Number" hint="Auto-generated if blank">
            <Input
              placeholder="FR-26-0001"
              value={form.run_number}
              onChange={(e) => set("run_number", e.target.value)}
            />
          </Field>
          <Field label="Started">
            <Input
              type="date"
              value={form.started_at}
              onChange={(e) => set("started_at", e.target.value)}
            />
          </Field>
        </div>

        <Field label="Construction">
          <Input
            placeholder="e.g. Single Jersey 30s"
            value={form.construction}
            onChange={(e) => set("construction", e.target.value)}
          />
        </Field>

        <Field label="Input Lot (Yarn/Fabric)">
          <SearchableSelect
            value={form.input_lot_id}
            onChange={(v) => set("input_lot_id", v)}
            placeholder="— None —"
            accent="#8174F5"
            options={[
              { value: "", label: "— None —" },
              ...yarnFabricLots.map((l) => ({
                value: l.id,
                label: l.lot_number,
                meta: l.material_type,
              })),
            ]}
          />
        </Field>

        <div className="grid grid-cols-2 gap-3">
          <Field label="Input Qty (kg)">
            <Input
              type="number"
              step="0.001"
              placeholder="0.000"
              value={form.input_qty}
              onChange={(e) => set("input_qty", e.target.value)}
            />
          </Field>
          <Field label="Machine">
            <Input
              placeholder="e.g. Mayer #3"
              value={form.machine}
              onChange={(e) => set("machine", e.target.value)}
            />
          </Field>
        </div>

        <Field label="Notes">
          <Textarea
            value={form.notes}
            onChange={(e) => set("notes", e.target.value)}
          />
        </Field>

        {err && <p className="text-xs text-violet-500">{err}</p>}
      </form>
    </ModalShell>
  );
}
