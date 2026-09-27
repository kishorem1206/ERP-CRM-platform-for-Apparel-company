"use client";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ModalShell, Field, Input, Textarea, ModalActions, SearchableSelect } from "./ModalShell";
import api from "@/lib/api";

interface Props {
  open: boolean;
  onClose: () => void;
}

export function NewLotModal({ open, onClose }: Props) {
  const qc = useQueryClient();
  const [form, setForm] = useState({
    lot_number: "",
    style_id: "",
    planned_qty: "",
    delivery_date: "",
    season: "",
    notes: "",
  });
  const [err, setErr] = useState<string | null>(null);

  const styles = useQuery({
    queryKey: ["styles-list"],
    queryFn: async () => {
      const r = await api.get("/production/styles");
      return (r.data.data ?? []) as { id: string; name: string; code: string | null }[];
    },
    enabled: open,
  });

  const mut = useMutation({
    mutationFn: async () => {
      const payload: Record<string, unknown> = {
        planned_qty: Number(form.planned_qty) || 1,
        notes: form.notes || undefined,
      };
      if (form.lot_number.trim()) payload.lot_number = form.lot_number.trim();
      if (form.style_id) payload.style_id = form.style_id;
      if (form.delivery_date) payload.delivery_date = form.delivery_date;
      if (form.season) payload.season = form.season;
      return api.post("/production/lots", payload);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["production-lots"] });
      onClose();
      setForm({ lot_number: "", style_id: "", planned_qty: "", delivery_date: "", season: "", notes: "" });
    },
    onError: (e: unknown) => {
      const msg = (e as { response?: { data?: { error?: { message?: string } } } })
        ?.response?.data?.error?.message;
      setErr(msg ?? "Failed to create lot");
    },
  });

  function set(k: string, v: string) { setForm((f) => ({ ...f, [k]: v })); setErr(null); }

  return (
    <ModalShell
      open={open}
      onClose={onClose}
      title="New Production Lot"
      subtitle="Start a new lot linked to a style."
      footer={
        <form onSubmit={(e) => { e.preventDefault(); mut.mutate(); }}>
          <ModalActions onClose={onClose} loading={mut.isPending} label="Create Lot" />
        </form>
      }
    >
      <form
        id="new-lot-form"
        onSubmit={(e) => { e.preventDefault(); mut.mutate(); }}
        className="space-y-4"
      >
        <Field label="Lot Number" hint="Leave blank to auto-generate (e.g. LOT/0001)">
          <Input
            placeholder="e.g. LOT-2024-001 (optional)"
            value={form.lot_number}
            onChange={(e) => set("lot_number", e.target.value)}
          />
        </Field>

        <Field label="Style">
          <SearchableSelect
            value={form.style_id}
            onChange={(v) => set("style_id", v)}
            placeholder="— No style —"
            accent="#0049A7"
            options={[
              { value: "", label: "— No style —" },
              ...(styles.data ?? []).map((s) => ({
                value: s.id,
                label: s.name,
                meta: s.code ?? undefined,
              })),
            ]}
          />
        </Field>

        <Field label="Planned Qty" required>
          <Input
            type="number"
            min={1}
            placeholder="e.g. 500"
            value={form.planned_qty}
            onChange={(e) => set("planned_qty", e.target.value)}
          />
        </Field>

        <div className="grid grid-cols-2 gap-3">
          <Field label="Delivery Date">
            <Input
              type="date"
              value={form.delivery_date}
              onChange={(e) => set("delivery_date", e.target.value)}
            />
          </Field>
          <Field label="Season">
            <Input
              placeholder="e.g. SS25"
              value={form.season}
              onChange={(e) => set("season", e.target.value)}
            />
          </Field>
        </div>

        <Field label="Notes">
          <Textarea
            placeholder="Internal notes…"
            value={form.notes}
            onChange={(e) => set("notes", e.target.value)}
          />
        </Field>

        {err && <p className="text-xs text-violet-500">{err}</p>}
      </form>
    </ModalShell>
  );
}
