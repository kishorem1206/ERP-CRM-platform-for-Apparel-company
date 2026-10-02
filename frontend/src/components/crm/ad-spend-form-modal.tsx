"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { X } from "lucide-react";
import api from "@/lib/api";
import { SearchableSelect } from "@/components/shared/searchable-select";
import { ModalShell } from "@/components/shared/modal-shell";

const INDIGO = "#0049A7";

const inputCls =
  "w-full rounded-xl border border-input bg-background px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring";

interface LeadSource {
  id: string;
  name: string;
}

export interface AdSpendEntry {
  id: string;
  source_id: string | null;
  campaign: string | null;
  campaign_id: string | null;
  ad_set: string | null;
  period_start: string;
  period_end: string;
  amount: string;
  impressions: number | null;
  clicks: number | null;
  notes: string | null;
}

export function AdSpendFormModal({
  initial,
  onClose,
}: {
  initial?: AdSpendEntry;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const [sourceId, setSourceId] = useState(initial?.source_id ?? "");
  const [campaign, setCampaign] = useState(initial?.campaign ?? "");
  const [campaignId, setCampaignId] = useState(initial?.campaign_id ?? "");
  const [adSet, setAdSet] = useState(initial?.ad_set ?? "");
  const [periodStart, setPeriodStart] = useState(initial?.period_start ?? "");
  const [periodEnd, setPeriodEnd] = useState(initial?.period_end ?? "");
  const [amount, setAmount] = useState(initial?.amount ?? "");
  const [impressions, setImpressions] = useState(initial?.impressions != null ? String(initial.impressions) : "");
  const [clicks, setClicks] = useState(initial?.clicks != null ? String(initial.clicks) : "");
  const [notes, setNotes] = useState(initial?.notes ?? "");
  const [error, setError] = useState("");

  const { data: sourcesData } = useQuery({
    queryKey: ["crm-lead-sources"],
    queryFn: () => api.get("/crm/lead-sources").then((r) => r.data),
  });
  const sources: LeadSource[] = sourcesData?.data ?? [];

  const mutation = useMutation({
    mutationFn: async () => {
      const payload = {
        source_id: sourceId || undefined,
        campaign: campaign || undefined,
        campaign_id: campaignId || undefined,
        ad_set: adSet || undefined,
        period_start: periodStart,
        period_end: periodEnd,
        amount: amount ? Number(amount) : undefined,
        impressions: impressions ? Number(impressions) : undefined,
        clicks: clicks ? Number(clicks) : undefined,
        notes: notes || undefined,
      };
      if (initial) {
        await api.patch(`/crm/ad-spend/${initial.id}`, payload);
      } else {
        await api.post("/crm/ad-spend", payload);
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["crm-ad-spend"] });
      onClose();
    },
    onError: (e: unknown) => {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(typeof msg === "string" ? msg : "Failed to save");
    },
  });

  const canSave = sourceId && periodStart && periodEnd && amount && Number(amount) > 0;

  return (
    <ModalShell maxWidth="max-w-md" onClose={onClose}>
      <div className="flex items-center justify-between p-6 border-b">
        <h2 className="text-lg font-semibold">{initial ? "Edit Spend" : "Log Ad Spend"}</h2>
        <button onClick={onClose} className="p-1 rounded hover:bg-muted transition-colors">
          <X className="h-4 w-4" />
        </button>
      </div>
      <div className="p-6 space-y-4">
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">
            Platform <span className="text-destructive">*</span>
          </label>
          <SearchableSelect
            options={sources.map((s) => ({ value: s.id, label: s.name }))}
            value={sourceId} onChange={setSourceId} placeholder="Select platform…" accent={INDIGO}
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">Campaign</label>
          <input
            className={inputCls} placeholder="e.g. Diwali Push (optional)"
            value={campaign} onChange={(e) => setCampaign(e.target.value)}
          />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">Campaign ID</label>
            <input
              className={inputCls} placeholder="Platform's own ID (optional)"
              value={campaignId} onChange={(e) => setCampaignId(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">Ad Set</label>
            <input
              className={inputCls} placeholder="optional"
              value={adSet} onChange={(e) => setAdSet(e.target.value)}
            />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">
              Period Start <span className="text-destructive">*</span>
            </label>
            <input className={inputCls} type="date" value={periodStart} onChange={(e) => setPeriodStart(e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">
              Period End <span className="text-destructive">*</span>
            </label>
            <input className={inputCls} type="date" value={periodEnd} onChange={(e) => setPeriodEnd(e.target.value)} />
          </div>
        </div>
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">
            Amount (₹) <span className="text-destructive">*</span>
          </label>
          <input
            className={inputCls} type="number" min="0" step="0.01" placeholder="0.00"
            value={amount} onChange={(e) => setAmount(e.target.value)}
          />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">Impressions</label>
            <input
              className={inputCls} type="number" min="0" step="1" placeholder="optional"
              value={impressions} onChange={(e) => setImpressions(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">Clicks</label>
            <input
              className={inputCls} type="number" min="0" step="1" placeholder="optional"
              value={clicks} onChange={(e) => setClicks(e.target.value)}
            />
          </div>
        </div>
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">Notes</label>
          <textarea className={`${inputCls} resize-none`} rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} />
        </div>
        {error && <p className="text-xs text-destructive">{error}</p>}
      </div>
      <div className="flex justify-end gap-3 p-6 border-t">
        <button onClick={onClose} className="px-4 py-2 text-sm rounded-xl border border-input hover:bg-muted transition-colors">
          Cancel
        </button>
        <button
          onClick={() => { setError(""); mutation.mutate(); }}
          disabled={!canSave || mutation.isPending}
          className="px-4 py-2 text-sm rounded-xl text-white font-semibold transition-all hover:opacity-90 disabled:opacity-50"
          style={{ background: INDIGO }}
        >
          {mutation.isPending ? "Saving…" : "Save"}
        </button>
      </div>
    </ModalShell>
  );
}
