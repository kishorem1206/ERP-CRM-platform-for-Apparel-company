"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import api from "@/lib/api";

const INDIGO = "#0049A7";

interface VendorDetail {
  code: string;
  name: string;
  gstin: string | null;
  pan: string | null;
  vendor_type: string;
  payment_terms: number;
  is_active: boolean;
  contacts: { name: string; phone: string | null; email: string | null; is_primary: boolean }[];
  bank_details: { bank_name: string | null; account_number: string | null; ifsc: string | null; account_name: string | null; is_primary: boolean }[];
}

export default function VendorDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data, isLoading, isError } = useQuery({
    queryKey: ["vendor-detail", id],
    queryFn: () => api.get(`/purchase/vendors/${id}`).then((r) => r.data.data as VendorDetail),
  });

  const card = "rounded-2xl border border-border bg-card p-5";
  const label = "text-[11px] font-semibold uppercase tracking-wider text-muted-foreground";

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-center gap-3">
        <Link href="/purchase/vendors" className="rounded-lg p-2 hover:bg-muted" aria-label="Back">
          <ArrowLeft className="h-4 w-4" />
        </Link>
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Vendor</p>
          <h1 className="text-2xl font-bold tracking-tight">{data?.name ?? (isLoading ? "Loading…" : "—")}</h1>
        </div>
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
