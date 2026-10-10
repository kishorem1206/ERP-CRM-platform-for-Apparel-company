"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Pencil, X } from "lucide-react";
import api from "@/lib/api";
import { ModalPortal } from "@/components/shared/modal-portal";
import { SearchableSelect } from "@/components/shared/searchable-select";
import { Can } from "@/lib/permissions";
import { parseApiError } from "@/lib/api-error";
import { SuppliesPicker } from "../_supplies-picker";

const INDIGO = "#0049A7";

interface VendorDetail {
  code: string;
  name: string;
  gstin: string | null;
  pan: string | null;
  vendor_type: string;
  payment_terms: number;
  is_active: boolean;
  supplies_product_types: string[] | null;
  contacts: { name: string; phone: string | null; email: string | null; is_primary: boolean }[];
  bank_details: { bank_name: string | null; account_number: string | null; ifsc: string | null; account_name: string | null; is_primary: boolean }[];
}

function EditVendorModal({ id, vendor, onClose }: { id: string; vendor: VendorDetail; onClose: () => void }) {
  const qc = useQueryClient();
  const [form, setForm] = useState({
    name: vendor.name,
    gstin: vendor.gstin ?? "",
    pan: vendor.pan ?? "",
    vendor_type: vendor.vendor_type,
    payment_terms: String(vendor.payment_terms),
    is_active: vendor.is_active,
    supplies: vendor.supplies_product_types ?? ([] as string[]),
  });
  const [error, setError] = useState("");

  const mut = useMutation({
    mutationFn: () =>
      api.patch(`/purchase/vendors/${id}`, {
        name: form.name,
        gstin: form.gstin || null,
        pan: form.pan || null,
        vendor_type: form.vendor_type,
        payment_terms: parseInt(form.payment_terms) || 30,
        is_active: form.is_active,
        supplies_product_types: form.supplies.length ? form.supplies : null,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["vendor-detail", id] });
      qc.invalidateQueries({ queryKey: ["vendors"] });
      onClose();
    },
    onError: (e: unknown) => setError(parseApiError(e, "Failed to update vendor")),
  });

  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  return (
    <ModalPortal>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-6 overflow-y-auto bg-black/40 backdrop-blur-[2px]">
        <div className="bg-card border rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
          <div className="flex items-center justify-between px-5 py-4 border-b">
            <h2 className="font-semibold text-base">Edit Vendor</h2>
            <button onClick={onClose} className="text-muted-foreground hover:text-foreground"><X className="h-4 w-4" /></button>
          </div>
          <form
            className="p-5 space-y-3"
            onSubmit={(e) => { e.preventDefault(); setError(""); mut.mutate(); }}
          >
            <div>
              <label className="text-xs font-medium text-muted-foreground">Vendor Name *</label>
              <input required value={form.name} onChange={set("name")}
                className="mt-1 w-full rounded border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-medium text-muted-foreground">Type *</label>
                <div className="mt-1">
                  <SearchableSelect
                    value={form.vendor_type}
                    onChange={(v) => setForm((f) => ({ ...f, vendor_type: v }))}
                    accent={INDIGO}
                    options={[
                      { value: "supplier", label: "Supplier" },
                      { value: "job_worker", label: "Job Worker" },
                      { value: "transporter", label: "Transporter" },
                      { value: "agent", label: "Agent" },
                    ]}
                  />
                </div>
              </div>
              <div>
                <label className="text-xs font-medium text-muted-foreground">Status</label>
                <div className="mt-1">
                  <SearchableSelect
                    value={form.is_active ? "active" : "inactive"}
                    onChange={(v) => setForm((f) => ({ ...f, is_active: v === "active" }))}
                    accent={INDIGO}
                    options={[
                      { value: "active", label: "Active" },
                      { value: "inactive", label: "Inactive" },
                    ]}
                  />
                </div>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-medium text-muted-foreground">GSTIN</label>
                <input value={form.gstin} onChange={set("gstin")}
                  className="mt-1 w-full rounded border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                  placeholder="22AAAAA0000A1Z5" />
              </div>
              <div>
                <label className="text-xs font-medium text-muted-foreground">PAN</label>
                <input value={form.pan} onChange={set("pan")}
                  className="mt-1 w-full rounded border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                  placeholder="AAAAA0000A" />
              </div>
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground">Payment Terms (days)</label>
              <input type="number" min="0" value={form.payment_terms} onChange={set("payment_terms")}
                className="mt-1 w-full rounded border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
            </div>
            <SuppliesPicker value={form.supplies} onChange={(v) => setForm((f) => ({ ...f, supplies: v }))} />
            {error && <p className="text-xs text-destructive">{error}</p>}
            <div className="flex justify-end gap-2 pt-1">
              <button type="button" onClick={onClose}
                className="px-4 py-1.5 rounded border border-input text-sm hover:bg-muted">Cancel</button>
              <button type="submit" disabled={mut.isPending}
                className="px-4 py-1.5 rounded bg-primary text-primary-foreground text-sm hover:bg-primary/90 disabled:opacity-60">
                {mut.isPending ? "Saving…" : "Save Changes"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </ModalPortal>
  );
}

export default function VendorDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [showEdit, setShowEdit] = useState(false);
  const { data, isLoading, isError } = useQuery({
    queryKey: ["vendor-detail", id],
    queryFn: () => api.get(`/purchase/vendors/${id}`).then((r) => r.data.data as VendorDetail),
  });

  const card = "rounded-2xl border border-border bg-card p-5";
  const label = "text-[11px] font-semibold uppercase tracking-wider text-muted-foreground";

  return (
    <div className="p-8 space-y-6">
      {showEdit && data && (
        <EditVendorModal id={id} vendor={data} onClose={() => setShowEdit(false)} />
      )}
      <div className="flex items-center gap-3 justify-between">
        <div className="flex items-center gap-3">
          <Link href="/purchase/vendors" className="rounded-lg p-2 hover:bg-muted" aria-label="Back">
            <ArrowLeft className="h-4 w-4" />
          </Link>
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Vendor</p>
            <h1 className="text-2xl font-bold tracking-tight">{data?.name ?? (isLoading ? "Loading…" : "—")}</h1>
          </div>
        </div>
        {data && (
          <Can perm="purchase.edit">
            <button
              onClick={() => setShowEdit(true)}
              className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-white transition-all duration-200 hover:opacity-90 active:scale-95"
              style={{ background: INDIGO }}
            >
              <Pencil className="h-3.5 w-3.5" /> Edit Vendor
            </button>
          </Can>
        )}
      </div>

      {isError ? (
        <div className={card + " text-sm text-muted-foreground"}>This vendor could not be loaded.</div>
      ) : data && (
        <>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            {[
              ["Code", data.code], ["GSTIN", data.gstin], ["PAN", data.pan],
              ["Payment terms", `${data.payment_terms} days`],
            ].map(([k, v]) => (
              <div key={k as string} className={card + " min-w-0"}>
                <p className={label}>{k}</p>
                <p className="mt-1 truncate font-semibold">{(v as string) || "—"}</p>
              </div>
            ))}
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <div className={card}>
              <p className="text-sm font-semibold mb-3" style={{ color: INDIGO }}>Contacts</p>
              {data.contacts.length === 0 && <p className="text-sm text-muted-foreground">No contacts added.</p>}
              {data.contacts.map((c, i) => (
                <div key={i} className="border-t border-border py-2 first:border-t-0">
                  <p className="font-medium">{c.name}{c.is_primary && <span className="ml-2 text-[10px] font-bold uppercase text-indigo-700">Primary</span>}</p>
                  <p className="text-xs text-muted-foreground">{[c.phone, c.email].filter(Boolean).join(" · ") || "—"}</p>
                </div>
              ))}
            </div>
            <div className={card}>
              <p className="text-sm font-semibold mb-3" style={{ color: INDIGO }}>Bank details</p>
              {data.bank_details.length === 0 && <p className="text-sm text-muted-foreground">No bank details added.</p>}
              {data.bank_details.map((b, i) => (
                <div key={i} className="border-t border-border py-2 first:border-t-0 text-sm">
                  <p className="font-medium">{b.bank_name || "—"}</p>
                  <p className="text-xs text-muted-foreground">A/c {b.account_number || "—"} · IFSC {b.ifsc || "—"}</p>
                  <p className="text-xs text-muted-foreground">{b.account_name || ""}</p>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
