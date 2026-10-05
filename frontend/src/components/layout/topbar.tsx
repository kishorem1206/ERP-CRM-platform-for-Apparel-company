"use client";
import { useEffect, useRef, useState } from "react";
import { Search, Bell, CheckCheck, Package, CreditCard, Factory, Info, Users, Building2, Box, Truck, Receipt } from "lucide-react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import api from "@/lib/api";
import { cn } from "@/lib/utils";

type Notif = {
  id: string;
  notification_type: "low_stock" | "overdue_payment" | "production_delay" | "job_work_overdue" | "job_work_bill_pending" | "system";
  title: string;
  body: string;
  is_read: boolean;
  created_at: string;
};

const TYPE_ICON: Record<string, React.ReactNode> = {
  low_stock:        <Package className="h-4 w-4 text-violet-500" />,
  overdue_payment:  <CreditCard className="h-4 w-4 text-violet-500" />,
  production_delay: <Factory className="h-4 w-4 text-violet-500" />,
  job_work_overdue: <Truck className="h-4 w-4 text-violet-500" />,
  job_work_bill_pending: <Receipt className="h-4 w-4 text-violet-500" />,
  system:           <Info className="h-4 w-4 text-blue-500" />,
};

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

type SearchResult = { label: string; sub: string; href: string; module: string };

async function runSearch(q: string): Promise<SearchResult[]> {
  const s = encodeURIComponent(q);
  const [custRes, vendRes, prodRes] = await Promise.allSettled([
    api.get(`/sales/customers?search=${s}&page_size=5`),
    api.get(`/purchase/vendors?search=${s}&page_size=5`),
    api.get(`/products?search=${s}&page_size=5`),
  ]);

  const results: SearchResult[] = [];

  if (custRes.status === "fulfilled") {
    for (const c of custRes.value.data.data ?? []) {
      results.push({ module: "Customers", label: c.legal_name, sub: c.code, href: "/crm/customers" });
    }
  }
  if (vendRes.status === "fulfilled") {
    for (const v of vendRes.value.data.data ?? []) {
      results.push({ module: "Vendors", label: v.name, sub: v.code, href: "/purchase/vendors" });
    }
  }
  if (prodRes.status === "fulfilled") {
    for (const p of prodRes.value.data.data ?? []) {
      results.push({ module: "Products", label: p.name, sub: p.code ?? p.sku ?? "", href: "/inventory/products" });
    }
  }
  return results;
}

const MODULE_ICON: Record<string, React.ReactNode> = {
  Customers: <Users className="h-3.5 w-3.5" />,
  Vendors:   <Building2 className="h-3.5 w-3.5" />,
  Products:  <Box className="h-3.5 w-3.5" />,
};

export function Topbar() {
  const qc = useQueryClient();
  const router = useRouter();
  const [searchOpen, setSearchOpen] = useState(false);
  const [bellOpen, setBellOpen] = useState(false);
  const bellRef = useRef<HTMLDivElement>(null);
  const [searchQ, setSearchQ] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const searchRef = useRef<HTMLInputElement>(null);

  // Poll unread count every 30s
  const { data: countData } = useQuery({
    queryKey: ["notif-count"],
    queryFn: async () => {
      const res = await api.get("/notifications/count");
      return (res.data.data?.unread ?? 0) as number;
    },
    refetchInterval: 30_000,
  });

  // Fetch notifications list when bell is open
  const { data: notifs } = useQuery<Notif[]>({
    queryKey: ["notifs"],
    queryFn: async () => {
      const res = await api.get("/notifications?limit=15");
      return res.data.data ?? [];
    },
    enabled: bellOpen,
  });

  // WebSocket for real-time pushes
  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) return;

    const backendHost = process.env.NEXT_PUBLIC_API_URL?.replace(/^https?/, "ws") ?? "ws://localhost:8000";
    const ws = new WebSocket(`${backendHost}/api/v1/ws/notifications?token=${token}`);

    ws.onmessage = () => {
      qc.invalidateQueries({ queryKey: ["notif-count"] });
      qc.invalidateQueries({ queryKey: ["notifs"] });
    };

    return () => ws.close();
  }, [qc]);

  // Close bell dropdown on outside click
  useEffect(() => {
    function handler(e: MouseEvent) {
      if (bellRef.current && !bellRef.current.contains(e.target as Node)) {
        setBellOpen(false);
      }
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  // Keyboard shortcut
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") { e.preventDefault(); setSearchOpen(true); }
      if (e.key === "Escape") { setSearchOpen(false); setBellOpen(false); setSearchQ(""); setSearchResults([]); }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, []);

  // Debounced search
  useEffect(() => {
    if (!searchOpen) { setSearchQ(""); setSearchResults([]); return; }
    if (searchOpen) setTimeout(() => searchRef.current?.focus(), 50);
  }, [searchOpen]);

  useEffect(() => {
    if (searchQ.trim().length < 2) { setSearchResults([]); return; }
    setSearching(true);
    const t = setTimeout(async () => {
      try {
        const results = await runSearch(searchQ.trim());
        setSearchResults(results);
      } finally {
        setSearching(false);
      }
    }, 300);
    return () => clearTimeout(t);
  }, [searchQ]);

  async function markAllRead() {
    await api.post("/notifications/read-all");
    qc.invalidateQueries({ queryKey: ["notif-count"] });
    qc.invalidateQueries({ queryKey: ["notifs"] });
  }

  async function markOneRead(id: string) {
    await api.post(`/notifications/${id}/read`);
    qc.invalidateQueries({ queryKey: ["notif-count"] });
    qc.invalidateQueries({ queryKey: ["notifs"] });
  }

  const unread = countData ?? 0;

  return (
    <>
      <header className="h-14 border-b bg-card flex items-center px-4 gap-4 shrink-0">
        {/* Search trigger */}
        <button
          onClick={() => setSearchOpen(true)}
          className="flex items-center gap-2 text-sm text-muted-foreground border rounded-md px-3 py-1.5 hover:bg-muted transition-colors w-64"
        >
          <Search className="h-4 w-4" />
          <span>Search...</span>
          <kbd className="ml-auto text-xs border rounded px-1">⌘K</kbd>
        </button>

        <div className="flex-1" />

        {/* Notification bell */}
        <div className="relative" ref={bellRef}>
          <button
            onClick={() => setBellOpen((o) => !o)}
            className="relative p-2 rounded-md hover:bg-muted transition-colors"
          >
            <Bell className="h-4 w-4" />
            {unread > 0 && (
              <span className="absolute top-1 right-1 h-4 w-4 flex items-center justify-center rounded-full bg-violet-500 text-[9px] font-bold text-white leading-none">
                {unread > 9 ? "9+" : unread}
              </span>
            )}
          </button>

          {bellOpen && (
            <div className="absolute right-0 top-full mt-2 w-80 bg-card border rounded-xl shadow-xl z-50 overflow-hidden">
              <div className="flex items-center justify-between px-4 py-2.5 border-b">
                <span className="font-semibold text-sm">Notifications</span>
                {unread > 0 && (
                  <button
                    onClick={markAllRead}
                    className="text-xs text-primary hover:underline flex items-center gap-1"
                  >
                    <CheckCheck className="h-3 w-3" /> Mark all read
                  </button>
                )}
              </div>

              <div className="max-h-80 overflow-y-auto divide-y">
                {!notifs || notifs.length === 0 ? (
                  <div className="px-4 py-6 text-sm text-muted-foreground text-center">
                    No notifications
                  </div>
                ) : (
                  notifs.map((n) => (
                    <button
                      key={n.id}
                      onClick={() => markOneRead(n.id)}
                      className={cn(
                        "w-full text-left flex gap-3 px-4 py-3 hover:bg-muted/50 transition-colors",
                        !n.is_read && "bg-primary/5"
                      )}
                    >
                      <div className="mt-0.5 shrink-0">
                        {TYPE_ICON[n.notification_type] ?? <Info className="h-4 w-4 text-muted-foreground" />}
                      </div>
                      <div className="min-w-0">
                        <div className="flex items-center justify-between gap-2">
                          <p className={cn("text-xs font-semibold truncate", !n.is_read && "text-foreground")}>{n.title}</p>
                          <span className="text-[10px] text-muted-foreground shrink-0">{timeAgo(n.created_at)}</span>
                        </div>
                        <p className="text-xs text-muted-foreground line-clamp-2 mt-0.5">{n.body}</p>
                      </div>
                    </button>
                  ))
                )}
              </div>
            </div>
          )}
        </div>
      </header>

      {/* Command palette */}
      {searchOpen && (
        <div className="fixed inset-0 z-50 bg-black/40 flex items-start justify-center pt-24" onClick={() => { setSearchOpen(false); setSearchQ(""); setSearchResults([]); }}>
          <div className="bg-card border rounded-xl shadow-2xl w-full max-w-xl overflow-hidden" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center gap-2 px-4 py-3 border-b">
              <Search className="h-4 w-4 text-muted-foreground shrink-0" />
              <input
                ref={searchRef}
                value={searchQ}
                onChange={(e) => setSearchQ(e.target.value)}
                placeholder="Search customers, vendors, products…"
                className="flex-1 bg-transparent text-sm outline-none"
              />
              {searching && <span className="text-xs text-muted-foreground animate-pulse">Searching…</span>}
              <kbd className="text-xs border rounded px-1 text-muted-foreground shrink-0">ESC</kbd>
            </div>

            {searchQ.trim().length < 2 ? (
              <div className="p-4 text-sm text-muted-foreground text-center">
                Type at least 2 characters to search across all modules
              </div>
            ) : searchResults.length === 0 && !searching ? (
              <div className="p-4 text-sm text-muted-foreground text-center">No results found</div>
            ) : (
              <div className="max-h-80 overflow-y-auto divide-y">
                {Object.entries(
                  searchResults.reduce<Record<string, SearchResult[]>>((acc, r) => {
                    (acc[r.module] ??= []).push(r);
                    return acc;
                  }, {})
                ).map(([module, items]) => (
                  <div key={module}>
                    <div className="flex items-center gap-1.5 px-4 py-1.5 bg-muted/40 text-xs font-semibold text-muted-foreground">
                      {MODULE_ICON[module]} {module}
                    </div>
                    {items.map((item, i) => (
                      <button
                        key={i}
                        onClick={() => {
                          router.push(item.href);
                          setSearchOpen(false);
                          setSearchQ("");
                          setSearchResults([]);
                        }}
                        className="w-full text-left flex items-center gap-3 px-4 py-2.5 hover:bg-muted/50 transition-colors"
                      >
                        <div className="min-w-0">
                          <p className="text-sm font-medium truncate">{item.label}</p>
                          <p className="text-xs text-muted-foreground">{item.sub}</p>
                        </div>
                      </button>
                    ))}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}
