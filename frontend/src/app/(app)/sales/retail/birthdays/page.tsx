"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Gift } from "lucide-react";
import api from "@/lib/api";
import { parseApiError } from "@/lib/api-error";
import { Can } from "@/lib/permissions";
import { SearchableSelect } from "@/components/shared/searchable-select";
import { settingsInputCls as inputCls, useSaveRetailSettings } from "@/components/retail/settings-section";
import { fmtDate } from "@/components/documents/pdf-document-page";
import { RETAIL_ACCENT, type RetailSettings } from "@/lib/retail";

interface Row { customer_id: string; name: string; mobile: string; birthday: string; days_away: number; age: number; coupon_code: string | null; coupon_used: boolean }
interface Dash { today: Row[]; next_7: Row[]; next_30: Row[]; coupons_generated: number; coupons_redeemed: number; redemption_pct: number }

function List({ title, rows }: { title: string; rows: Row[] }) {
  return (
    <div className="rounded-2xl border border-border bg-card p-5">
      <p className="text-sm font-semibold mb-3">{title} <span className="text-muted-foreground font-normal">({rows.length})</span></p>
      {rows.length === 0 ? <p className="text-sm text-muted-foreground">None.</p> : (
        <div className="space-y-2">
          {rows.map((r) => (
            <div key={r.customer_id} className="flex items-center justify-between gap-3 text-sm">
              <Link href={`/sales/retail/customers/${r.customer_id}`} className="hover:underline min-w-0">
                <span className="font-medium">{r.name}</span> <span className="text-xs text-muted-foreground">{r.mobile} · {fmtDate(r.birthday)} · turns {r.age}</span>
              </Link>
              {r.coupon_code ? (
                <span className={`font-mono text-xs ${r.coupon_used ? "line-through text-muted-foreground" : ""}`}>{r.coupon_code}{r.coupon_used ? " (used)" : ""}</span>
              ) : <span className="text-xs text-muted-foreground">No coupon yet</span>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function RetailBirthdaysPage() {
  const qc = useQueryClient();
  const dash = useQuery({ queryKey: ["retail-birthdays"], queryFn: async () => (await api.get("/retail/birthdays")).data.data as Dash });
  const settings = useQuery({ queryKey: ["retail-settings"], queryFn: async () => (await api.get("/retail/settings")).data.data as RetailSettings });
  const { save, status, button } = useSaveRetailSettings();
  const [genMsg, setGenMsg] = useState("");
  const generate = useMutation({
    mutationFn: async () => (await api.post("/retail/birthdays/generate")).data,
    onSuccess: (res) => { setGenMsg(res.message); qc.invalidateQueries({ queryKey: ["retail-birthdays"] }); qc.invalidateQueries({ queryKey: ["retail-coupons"] }); },
    onError: (e: unknown) => setGenMsg(parseApiError(e, "Could not create the coupons.")),
  });
  const [f, setF] = useState({ enabled: false, type: "percent", value: "", min: "", max: "", window: "week", lead: "" });
  useEffect(() => {
    const s = settings.data;
    if (s) setF({
      enabled: s.birthday_enabled, type: s.birthday_discount_type, value: String(Number(s.birthday_discount_value)),
      min: String(Number(s.birthday_min_purchase)), max: s.birthday_max_discount ? String(Number(s.birthday_max_discount)) : "",
      window: s.birthday_window, lead: String(s.birthday_lead_days),
    });
  }, [settings.data]);
  const d = dash.data;
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement>) => setF((x) => ({ ...x, [k]: e.target.value }));

  return (
    <div className="p-8 space-y-6 max-w-5xl">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">SALES / RETAIL</p>
          <h1 className="text-2xl font-bold tracking-tight">Birthday Offers</h1>
          <p className="text-sm text-muted-foreground mt-1">Each customer with a date of birth gets a one-time coupon ahead of their birthday — made every night automatically.</p>
        </div>
        <Can perm="retail.manage">
          <button onClick={() => { setGenMsg(""); generate.mutate(); }} disabled={generate.isPending}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-white disabled:opacity-50" style={{ background: RETAIL_ACCENT }}>
            <Gift className="h-4 w-4" /> {generate.isPending ? "Creating…" : "Create due coupons now"}
          </button>
        </Can>
      </div>
      {genMsg && <p className="text-sm text-muted-foreground">{genMsg}</p>}
      {d && (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
          {[["Birthdays today", d.today.length], ["Next 7 days", d.next_7.length], ["Coupons this year", d.coupons_generated],
            ["Redeemed", d.coupons_redeemed], ["Redemption rate", `${d.redemption_pct}%`]].map(([k, v]) => (
            <div key={k as string} className="rounded-2xl border border-border bg-card p-4"><p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">{k}</p><p className="mt-1 text-lg font-semibold tabular-nums">{v}</p></div>
          ))}
        </div>
      )}
      {d && (
        <div className="grid gap-4 lg:grid-cols-3">
          <List title="Today" rows={d.today} />
          <List title="Next 7 days" rows={d.next_7} />
          <List title="Next 30 days" rows={d.next_30} />
        </div>
      )}
      <Can perm="retail.manage">
        <div className="rounded-2xl border border-border bg-card p-5 space-y-4">
          <label className="flex items-center gap-2 text-sm font-semibold">
            <input type="checkbox" checked={f.enabled} onChange={(e) => setF((x) => ({ ...x, enabled: e.target.checked }))} /> Birthday offers switched on
          </label>
          <div className="grid gap-3 md:grid-cols-3">
            <div>
              <label className="text-xs text-muted-foreground">Discount type</label>
              <SearchableSelect value={f.type} onChange={(v) => setF((x) => ({ ...x, type: v || "percent" }))} accent={RETAIL_ACCENT}
                options={[{ value: "percent", label: "Percentage" }, { value: "fixed", label: "Fixed amount (₹)" }]} />
            </div>
            <div><label className="text-xs text-muted-foreground">{f.type === "percent" ? "Discount %" : "Discount ₹"}</label><input type="number" min="0" className={inputCls} value={f.value} onChange={set("value")} /></div>
            <div><label className="text-xs text-muted-foreground">Max discount ₹</label><input type="number" min="0" className={inputCls} value={f.max} onChange={set("max")} placeholder="No cap" /></div>
            <div><label className="text-xs text-muted-foreground">Minimum purchase ₹</label><input type="number" min="0" className={inputCls} value={f.min} onChange={set("min")} /></div>
            <div>
              <label className="text-xs text-muted-foreground">Valid during</label>
              <SearchableSelect value={f.window} onChange={(v) => setF((x) => ({ ...x, window: v || "week" }))} accent={RETAIL_ACCENT}
                options={[{ value: "week", label: "Birthday week (3 days either side)" }, { value: "month", label: "Birthday month" }]} />
            </div>
            <div><label className="text-xs text-muted-foreground">Create the coupon (days before)</label><input type="number" min="0" max="60" className={inputCls} value={f.lead} onChange={set("lead")} /></div>
          </div>
          <p className="text-[11px] text-muted-foreground">One coupon per customer per birthday, usable once, only by that customer. Sending it by WhatsApp/SMS can be added later.</p>
          {status}
          <div className="flex justify-end">
            {button(() => save.mutate({
              birthday_enabled: f.enabled, birthday_discount_type: f.type, birthday_discount_value: Number(f.value) || 0,
              birthday_min_purchase: Number(f.min) || 0, birthday_max_discount: f.max ? Number(f.max) : null,
              birthday_window: f.window, birthday_lead_days: Number(f.lead) || 0,
            }))}
          </div>
        </div>
      </Can>
    </div>
  );
}
