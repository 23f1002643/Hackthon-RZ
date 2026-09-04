import { createFileRoute, Link } from "@tanstack/react-router";
import { useDeferredValue, useEffect, useMemo, useState } from "react";
import {
  Activity,
  ArrowRight,
  ArrowDownRight,
  ArrowUpRight,
  BarChart3,
  Bell,
  Bot,
  Check,
  ChevronRight,
  CircleDollarSign,
  Clock3,
  FileClock,
  Gauge,
  LayoutDashboard,
  Menu,
  Moon,
  Package,
  Play,
  ReceiptIndianRupee,
  Search,
  Settings2,
  ShoppingBag,
  Sparkles,
  Sun,
  Target,
  Zap,
} from "lucide-react";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Toaster } from "@/components/ui/sonner";
import { fetchAuditLogs, fetchChartData, fetchCustomers, fetchMetrics, fetchNotifications, fetchOrders, fetchProducts, importCatalog, searchShop, toggleAgent } from "@/lib/api";
import { toast } from "sonner";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Vastra Studio Merchant" },
      { name: "description", content: "Vastra Studio merchant operations and AI commerce analytics." },
      { property: "og:title", content: "Vastra Studio Merchant" },
      { property: "og:description", content: "Vastra Studio merchant operations and AI commerce analytics." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: Landing,
});

type ViewId = "overview" | "agent" | "orders" | "customers" | "catalog" | "audit";
type DashboardLog = Record<string, any>;

function Landing() {
  return (
    <main className="min-h-screen overflow-hidden bg-background text-foreground">
      <section className="relative border-b border-border px-5 py-16 lg:px-16 lg:py-24">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_85%_10%,oklch(0.34_0.14_300/.42),transparent_35%),radial-gradient(circle_at_15%_0%,oklch(0.3_0.12_265/.32),transparent_32%)]" />
        <div className="relative mx-auto max-w-6xl">
          <div className="flex items-center gap-2 text-sm font-medium text-primary"><Sparkles className="size-4" /> Vastra Studio</div>
          <h1 className="mt-6 max-w-4xl text-5xl font-semibold tracking-tight lg:text-7xl">From intent to payment.</h1>
          <p className="mt-6 max-w-2xl text-lg leading-relaxed text-muted-foreground">An AI commerce agent that understands what shoppers want, finds real products, and keeps every money action bounded by policy and explicit consent.</p>
          <div className="mt-9 flex flex-wrap gap-3">
            <Button asChild className="bg-brand-gradient text-primary-foreground"><Link to="/shop">Start shopping <ArrowRight className="size-4" /></Link></Button>
            <Button asChild variant="outline"><Link to="/dashboard">Open merchant dashboard</Link></Button>
          </div>
          <div className="mt-16 grid max-w-4xl gap-px border border-border bg-border sm:grid-cols-3">
            {["Real catalog data", "Server-side payment verification", "Explainable audit trail"].map((item) => <div key={item} className="bg-card p-5 text-sm font-medium">{item}</div>)}
          </div>
        </div>
      </section>
    </main>
  );
}

const navItems: { id: ViewId; label: string; icon: typeof LayoutDashboard }[] = [
  { id: "overview", label: "Overview", icon: LayoutDashboard },
  { id: "agent", label: "Agent control", icon: Bot },
  { id: "orders", label: "Orders", icon: ReceiptIndianRupee },
  { id: "customers", label: "Customers", icon: ShoppingBag },
  { id: "catalog", label: "Catalog", icon: Package },
  { id: "audit", label: "Audit trail", icon: FileClock },
];

const notificationDismissedKey = "vastra-notification-dismissed-ids";
const auditDismissedKey = "vastra-audit-dismissed-ids";

const actionLabels: Record<string, string> = {
  analyze_cart: "Cart analyzed",
  upsell_decision: "Upsell evaluated",
  upsell_accepted: "Upsell accepted",
  create_customer: "Customer created",
  create_order: "Order created",
  capture_payment: "Payment captured",
  checkout_error: "Checkout error",
};

function cleanDisplayText(value?: string, fallback = "") {
  const source = String(value ?? "").trim();
  if (!source) return fallback;

  const cleaned = source
    .replace(/\(fallback:.*$/i, "")
    .replace(/error code:\s*\d+.*$/i, "")
    .replace(/\{.*$/g, "")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/^["']+|["']+$/g, "")
    .trim();

  return cleaned || fallback;
}

function formatCurrency(value: number) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: Number.isInteger(value) ? 0 : 2,
  }).format(value);
}

function formatIndianTime(input?: Date | string) {
  const date = input ? new Date(input) : new Date();
  if (Number.isNaN(date.getTime())) return "--:--:--";
  return date.toLocaleTimeString("en-IN", { timeZone: "Asia/Kolkata", hour12: false });
}

function formatIndianDate(input?: Date | string) {
  const date = input ? new Date(input) : new Date();
  if (Number.isNaN(date.getTime())) return "--";
  return new Intl.DateTimeFormat("en-IN", {
    timeZone: "Asia/Kolkata",
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(date);
}

function formatAuditTime(input?: string) {
  if (!input) return "";
  const date = new Date(input);
  if (Number.isNaN(date.getTime())) return input;
  return date.toLocaleTimeString("en-IN", { timeZone: "Asia/Kolkata", hour12: false });
}

function formatAuditDate(input?: string) {
  if (!input) return "";
  const date = new Date(input);
  if (Number.isNaN(date.getTime())) return input;
  return date.toLocaleDateString("en-IN", {
    timeZone: "Asia/Kolkata",
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function humanizeAction(action?: string) {
  if (!action) return "Agent action";
  if (actionLabels[action]) return actionLabels[action];
  return action
    .split("_")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function getEntryId(entry: DashboardLog) {
  return String(entry.id ?? `${entry.timestamp ?? entry.time ?? ""}:${entry.action ?? entry.label ?? entry.title ?? ""}`);
}

function getEntryAmount(entry: DashboardLog) {
  const candidates: Array<[unknown, number]> = [
    [entry?.outputs?.outputs?.raw?.amount, 100],
    [entry?.outputs?.raw?.amount, 100],
    [entry?.outputs?.outputs?.amount, 1],
    [entry?.outputs?.amount, 1],
    [entry?.inputs?.amount, 1],
  ];

  for (const [rawAmount, divisor] of candidates) {
    if (rawAmount == null) continue;
    const amount = Number(rawAmount);
    if (Number.isFinite(amount) && amount > 0) return amount / divisor;
  }

  return 0;
}

function getEntryLabel(entry: DashboardLog) {
  return cleanDisplayText(entry.title) || cleanDisplayText(entry.label) || humanizeAction(entry.action);
}

function getEntryReason(entry: DashboardLog) {
  return (
    cleanDisplayText(entry.reason) ||
    cleanDisplayText(entry?.outputs?.suggestion?.reason) ||
    cleanDisplayText(entry?.outputs?.outputs?.suggestion?.reason) ||
    cleanDisplayText(entry.detail) ||
    "No additional context."
  );
}

function getEntryTime(entry: DashboardLog) {
  if (entry.timestamp) return formatAuditTime(entry.timestamp);
  return entry.time || "";
}

function getEntryOutcome(entry: DashboardLog) {
  if (entry.error || entry.type === "error") return "Failed";
  if (entry.action === "upsell_decision" && !(entry?.outputs?.decision ?? entry?.outputs?.outputs?.decision)) return "Skipped";
  return "Recorded";
}

function getEntryOutcomeClass(entry: DashboardLog) {
  const outcome = getEntryOutcome(entry);
  if (outcome === "Failed") return "text-destructive";
  if (outcome === "Skipped") return "text-warning";
  return "text-success";
}

function getEntryValue(entry: DashboardLog) {
  const amount = getEntryAmount(entry);
  return amount > 0 ? formatCurrency(amount) : "";
}

function buildSearchText(entry: DashboardLog) {
  const cartItems = Array.isArray(entry?.inputs?.cart) ? entry.inputs.cart.map((item: DashboardLog) => item?.name).join(" ") : "";
  const customerInfo =
    entry?.inputs?.customer_info && typeof entry.inputs.customer_info === "object"
      ? Object.values(entry.inputs.customer_info).join(" ")
      : "";
  const suggestion = entry?.outputs?.suggestion?.item || entry?.outputs?.outputs?.suggestion?.item || "";

  return [getEntryLabel(entry), getEntryReason(entry), entry.action || "", cartItems, customerInfo, suggestion].join(" ").toLowerCase();
}

function readStoredIds(key: string) {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(key);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed.filter((value): value is string => typeof value === "string") : [];
  } catch {
    return [];
  }
}

function writeStoredIds(key: string, ids: string[]) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(key, JSON.stringify(Array.from(new Set(ids))));
}

function mergeIds(current: string[], extra: string[]) {
  return Array.from(new Set([...current, ...extra]));
}

export function Dashboard() {
  const [view, setView] = useState<ViewId>("overview");
  const [agentLive, setAgentLive] = useState(true);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [lightMode, setLightMode] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [clock, setClock] = useState(() => formatIndianTime());
  const [headerDate, setHeaderDate] = useState(() => formatIndianDate());
  const [auditLogs, setAuditLogs] = useState<DashboardLog[]>([]);
  const [hiddenAuditIds, setHiddenAuditIds] = useState<string[]>([]);
  const [notifications, setNotifications] = useState<DashboardLog[]>([]);
  const [dismissedNotificationIds, setDismissedNotificationIds] = useState<string[]>([]);
  const [showNotifs, setShowNotifs] = useState(false);
  const [selectedAuditEntry, setSelectedAuditEntry] = useState<DashboardLog | null>(null);
  const deferredSearchTerm = useDeferredValue(searchTerm.trim().toLowerCase());

  useEffect(() => {
    document.documentElement.classList.toggle("light", lightMode);
    const timer = window.setInterval(() => {
      setClock(formatIndianTime());
      setHeaderDate(formatIndianDate());
    }, 1000);
    return () => window.clearInterval(timer);
  }, [lightMode]);

  useEffect(() => {
    setHiddenAuditIds(readStoredIds(auditDismissedKey));
    setDismissedNotificationIds(readStoredIds(notificationDismissedKey));
  }, []);

  useEffect(() => {
    let mounted = true;

    async function loadAuditLogs() {
      try {
        const data = await fetchAuditLogs();
        if (mounted) setAuditLogs(data.logs || []);
      } catch {
        if (mounted) setAuditLogs([]);
      }
    }

    loadAuditLogs();
    const id = window.setInterval(loadAuditLogs, 5000);
    return () => {
      mounted = false;
      window.clearInterval(id);
    };
  }, []);

  useEffect(() => {
    let mounted = true;
    const dismissedSet = new Set(dismissedNotificationIds);

    async function loadNotifications() {
      try {
        const data = await fetchNotifications();
        if (!mounted) return;
        setNotifications((data.notifications || []).filter((entry: DashboardLog) => !dismissedSet.has(getEntryId(entry))));
      } catch {
        if (mounted) setNotifications([]);
      }
    }

    loadNotifications();
    const id = window.setInterval(loadNotifications, 10000);
    return () => {
      mounted = false;
      window.clearInterval(id);
    };
  }, [dismissedNotificationIds]);

  const viewTitle = useMemo(() => navItems.find((item) => item.id === view)?.label ?? "Overview", [view]);
  const visibleAuditLogs = useMemo(
    () => auditLogs.filter((entry) => !hiddenAuditIds.includes(getEntryId(entry))),
    [auditLogs, hiddenAuditIds],
  );
  const searchResults = useMemo(() => {
    if (!deferredSearchTerm) return [];
    return visibleAuditLogs.filter((entry) => buildSearchText(entry).includes(deferredSearchTerm)).slice(0, 8);
  }, [deferredSearchTerm, visibleAuditLogs]);

  function dismissCurrentNotifications() {
    const nextIds = mergeIds(dismissedNotificationIds, notifications.map((entry) => getEntryId(entry)));
    setDismissedNotificationIds(nextIds);
    writeStoredIds(notificationDismissedKey, nextIds);
    setNotifications([]);
    setShowNotifs(false);
  }

  function clearVisibleAuditLogs() {
    const nextIds = mergeIds(hiddenAuditIds, visibleAuditLogs.map((entry) => getEntryId(entry)));
    setHiddenAuditIds(nextIds);
    writeStoredIds(auditDismissedKey, nextIds);
  }

  return (
    <div className="page-load min-h-screen bg-background text-foreground">
      <Sidebar activeView={view} onNavigate={setView} />
      <div className="min-h-screen pl-[68px] transition-[padding] duration-200">
        <header className="sticky top-0 z-20 flex h-[68px] items-center justify-between border-b border-border bg-background/95 px-5 backdrop-blur lg:px-8">
          <div className="flex min-w-0 items-center gap-3">
            <Button variant="ghost" size="icon" className="text-muted-foreground lg:hidden" title="Open navigation" aria-label="Open navigation">
              <Menu />
            </Button>
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <span className="hidden sm:inline">Workspace</span>
              <ChevronRight className="hidden size-3.5 sm:inline" />
              <span className="truncate text-foreground">{viewTitle}</span>
            </div>
          </div>
          <div className="flex items-center gap-2 sm:gap-5">
            <div className="hidden items-center gap-2 text-xs text-muted-foreground md:flex">
              <Clock3 className="size-3.5" />
              <span className="tabular-nums">{clock}</span>
              <span className="text-border">IST</span>
            </div>
            <div className="hidden h-5 w-px bg-border md:block" />
            <div className="relative hidden md:block">
              <Search className="pointer-events-none absolute left-3 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
              <input
                value={searchTerm}
                onChange={(event) => setSearchTerm(event.target.value)}
                placeholder="Search orders, customers, agent actions..."
                className="h-9 w-[340px] rounded-md border border-border bg-card pl-9 pr-3 text-sm text-foreground outline-none transition-colors focus:border-primary"
              />
            </div>
            <Button variant="ghost" size="icon" className="text-muted-foreground md:hidden" title="Open audit trail" aria-label="Open audit trail" onClick={() => setView("audit")}>
              <Search />
            </Button>
            <div className="relative">
              <Button variant="ghost" size="icon" className="relative text-muted-foreground" onClick={() => setShowNotifs((open) => !open)}>
                <Bell />
                {notifications.length > 0 && <span className="absolute right-2 top-2 size-1.5 rounded-full bg-primary live-dot" />}
              </Button>
              {showNotifs && (
                <div className="absolute right-0 top-10 z-50 w-80 overflow-hidden rounded-md border border-border bg-card shadow-[var(--shadow-panel)]">
                  <div className="flex items-center justify-between border-b border-border px-4 py-3 text-xs font-medium">
                    <span>Notifications</span>
                    <button type="button" className="text-[10px] font-medium text-muted-foreground hover:text-foreground" onClick={dismissCurrentNotifications}>
                      Clear
                    </button>
                  </div>
                  {notifications.length === 0 ? (
                    <div className="px-4 py-6 text-center text-xs text-muted-foreground">No recent activity</div>
                  ) : (
                    notifications.map((entry) => (
                      <button
                        key={getEntryId(entry)}
                        type="button"
                        className="flex w-full items-start gap-3 border-b border-border px-4 py-3 text-left last:border-0 hover:bg-muted/30"
                        onClick={() => {
                          setSelectedAuditEntry(entry);
                          setShowNotifs(false);
                        }}
                      >
                        <span className={`mt-1 size-1.5 shrink-0 rounded-full ${entry.type === "error" ? "bg-destructive" : "bg-success"}`} />
                        <div className="min-w-0">
                          <p className="text-xs font-medium">{getEntryLabel(entry)}</p>
                          <p className="mt-1 text-[11px] leading-relaxed text-muted-foreground">{getEntryReason(entry)}</p>
                          <p className="mt-1 text-[11px] tabular-nums text-muted-foreground">{getEntryTime(entry)}</p>
                        </div>
                      </button>
                    ))
                  )}
                </div>
              )}
            </div>
            <Button
              variant="ghost"
              size="icon"
              className="text-muted-foreground"
              title={lightMode ? "Use dark theme" : "Use light theme"}
              aria-label={lightMode ? "Use dark theme" : "Use light theme"}
              onClick={() => setLightMode((mode) => !mode)}
            >
              {lightMode ? <Moon /> : <Sun />}
            </Button>
            <div className="hidden items-center gap-2 border-l border-border pl-4 sm:flex">
              <div className="flex size-8 items-center justify-center rounded-full bg-brand-gradient text-xs font-semibold text-primary-foreground">ZA</div>
              <div className="hidden text-left lg:block">
                <p className="text-xs font-medium">Vastra Studio</p>
                <p className="text-[11px] text-muted-foreground">Merchant workspace</p>
              </div>
            </div>
          </div>
        </header>

        <main className="mx-auto max-w-[1680px] space-y-6 p-5 lg:p-8">
          <div className="flex flex-col justify-between gap-4 md:flex-row md:items-end">
            <div>
              <p className="mb-2 text-xs font-medium text-primary">{headerDate}</p>
              <h1 className={`text-2xl font-semibold tracking-tight lg:text-[28px] ${view === "overview" ? "gradient-text-primary" : ""}`}>
                {view === "overview" ? "Revenue intelligence" : viewTitle}
              </h1>
              <p className="mt-1 text-sm text-muted-foreground">
                {view === "overview" && "Autonomous commerce performance for Vastra Studio."}
                {view === "agent" && "Set the boundaries your agent must operate within."}
                {view === "audit" && "A complete, reviewable record of every agent decision."}
              </p>
            </div>
            <div className="flex items-center gap-3">
              <AgentStatusButton live={agentLive} onClick={() => setConfirmOpen(true)} />
              <Button
                className="bg-brand-gradient text-primary-foreground shadow-sm hover:opacity-90"
                onClick={async () => {
                  window.location.href = "/shop";
                }}
              >
                <Play className="size-3.5" /> Open buyer flow
              </Button>
            </div>
          </div>

          {deferredSearchTerm && (
            <SearchResults
              term={searchTerm}
              results={searchResults}
              onOpenAudit={() => setView("audit")}
              onSelect={(entry) => {
                setSelectedAuditEntry(entry);
                setView("audit");
              }}
            />
          )}

          {view === "overview" && (
            <Overview
              auditLogs={visibleAuditLogs}
              onOpenAudit={() => setView("audit")}
              onSelectEntry={setSelectedAuditEntry}
              onClearAudit={clearVisibleAuditLogs}
            />
          )}
          {view === "agent" && <AgentControl live={agentLive} onToggle={() => setConfirmOpen(true)} logs={auditLogs} />}
          {view === "orders" && <MerchantOrders />}
          {view === "customers" && <MerchantCustomers />}
          {view === "catalog" && <MerchantCatalog />}
          {view === "audit" && (
            <AuditTrail
              logs={visibleAuditLogs}
              searchTerm={searchTerm}
              onSelectEntry={setSelectedAuditEntry}
              onClear={clearVisibleAuditLogs}
            />
          )}
        </main>
      </div>

      <Dialog open={Boolean(selectedAuditEntry)} onOpenChange={(open) => !open && setSelectedAuditEntry(null)}>
        <DialogContent className="border-border bg-card sm:max-w-[520px]">
          <DialogHeader>
            <DialogTitle>{selectedAuditEntry ? getEntryLabel(selectedAuditEntry) : "Audit detail"}</DialogTitle>
            <DialogDescription>
              {selectedAuditEntry?.timestamp
                ? `${formatAuditDate(selectedAuditEntry.timestamp)} · ${formatAuditTime(selectedAuditEntry.timestamp)}`
                : selectedAuditEntry?.time || "Timestamp unavailable"}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3 rounded border border-border bg-background p-4 text-sm">
            <div>
              <p className="text-[11px] uppercase tracking-[0.12em] text-muted-foreground">Event</p>
              <p className="mt-2 text-foreground">{selectedAuditEntry ? humanizeAction(selectedAuditEntry.action) : "Audit detail"}</p>
            </div>
            <div>
              <p className="text-[11px] uppercase tracking-[0.12em] text-muted-foreground">Reason</p>
              <p className="mt-2 text-foreground">{selectedAuditEntry ? getEntryReason(selectedAuditEntry) : "No additional context."}</p>
            </div>
            <div>
              <p className="text-[11px] uppercase tracking-[0.12em] text-muted-foreground">Outcome</p>
              <p className={`mt-2 ${selectedAuditEntry ? getEntryOutcomeClass(selectedAuditEntry) : "text-foreground"}`}>
                {selectedAuditEntry ? getEntryOutcome(selectedAuditEntry) : "Recorded"}
              </p>
            </div>
            {selectedAuditEntry && getEntryValue(selectedAuditEntry) && (
              <div>
                <p className="text-[11px] uppercase tracking-[0.12em] text-muted-foreground">Amount</p>
                <p className="mt-2 text-foreground">{getEntryValue(selectedAuditEntry)}</p>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button onClick={() => setSelectedAuditEntry(null)}>Close</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <DialogContent className="border-border bg-card sm:max-w-[440px]">
          <DialogHeader>
            <DialogTitle>{agentLive ? "Pause commerce agent?" : "Put commerce agent live?"}</DialogTitle>
            <DialogDescription>
              {agentLive
                ? "New autonomous actions will stop immediately. In-flight payment retries will finish safely."
                : "The agent will resume approved upsells, checkout assistance, and payment recovery within your configured limits."}
            </DialogDescription>
          </DialogHeader>
          <div className="border border-border bg-background p-3 text-sm">
            <div className="flex items-center gap-2 font-medium">
              <Gauge className="size-4 text-primary" /> Current guardrails are active
            </div>
            <p className="mt-1 pl-6 text-xs text-muted-foreground">Max order ₹10,000 · Max upsell ₹1,500 · Confirmation required</p>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmOpen(false)}>
              Cancel
            </Button>
            <Button
              className={agentLive ? "bg-destructive text-destructive-foreground hover:bg-destructive/90" : "bg-brand-gradient text-primary-foreground hover:opacity-90"}
              onClick={async () => {
                const nextActive = !agentLive;
                try {
                  const result = await toggleAgent(nextActive);
                  setAgentLive(result?.merchant?.agent_active ?? nextActive);
                  setConfirmOpen(false);
                  toast.success(nextActive ? "Commerce agent resumed" : "Commerce agent paused");
                } catch (error) {
                  console.error("toggle failed", error);
                  toast.error(`Agent sync failed: ${error instanceof Error ? error.message : String(error)}`);
                }
              }}
            >
              {agentLive ? "Pause agent" : "Go live"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Toaster />
    </div>
  );
}

function Sidebar({ activeView, onNavigate }: { activeView: ViewId; onNavigate: (view: ViewId) => void }) {
  return (
    <aside className="group/sidebar fixed inset-y-0 left-0 z-30 flex w-[68px] flex-col overflow-hidden border-r border-sidebar-border bg-sidebar transition-[width] duration-200 hover:w-[232px]">
      <div className="flex h-[68px] shrink-0 items-center border-b border-sidebar-border px-[18px]">
        <div className="flex size-8 shrink-0 items-center justify-center rounded-md bg-brand-gradient text-sm font-bold text-primary-foreground">Z</div>
        <div className="ml-3 whitespace-nowrap opacity-0 transition-opacity duration-150 group-hover/sidebar:opacity-100">
          <p className="text-sm font-semibold text-sidebar-foreground">Vastra</p>
          <p className="text-[10px] text-muted-foreground">Commerce agent</p>
        </div>
      </div>
      <div className="flex flex-1 flex-col px-2 py-5">
        <p className="mb-2 whitespace-nowrap px-3 text-[10px] font-medium text-muted-foreground opacity-0 group-hover/sidebar:opacity-100">Workspace</p>
        <nav className="space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = activeView === item.id;
            return (
              <Button
                key={item.id}
                variant="ghost"
                onClick={() => onNavigate(item.id)}
                className={`h-10 w-full justify-start gap-3 px-3 text-sm ${active ? "bg-sidebar-accent text-sidebar-foreground" : "text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-foreground"}`}
                title={item.label}
                aria-label={item.label}
              >
                <Icon className={active ? "text-primary" : ""} />
                <span className="whitespace-nowrap opacity-0 transition-opacity duration-150 group-hover/sidebar:opacity-100">{item.label}</span>
              </Button>
            );
          })}
        </nav>
        <div className="my-5 h-px bg-sidebar-border" />
        <Button variant="ghost" className="h-10 w-full justify-start gap-3 px-3 text-sm text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-foreground" title="Settings" aria-label="Settings">
          <Settings2 />
          <span className="whitespace-nowrap opacity-0 transition-opacity duration-150 group-hover/sidebar:opacity-100">Settings</span>
        </Button>
      </div>
      <div className="border-t border-sidebar-border p-3">
        <div className="flex items-center gap-3 rounded-md bg-sidebar-accent p-2">
          <div className="flex size-8 shrink-0 items-center justify-center rounded-full border border-primary/30 bg-primary/10 text-[10px] font-semibold text-primary">AR</div>
          <div className="min-w-0 whitespace-nowrap opacity-0 transition-opacity duration-150 group-hover/sidebar:opacity-100">
            <p className="truncate text-xs font-medium">Ananya Rao</p>
            <p className="text-[10px] text-muted-foreground">Admin</p>
          </div>
        </div>
      </div>
    </aside>
  );
}

function AgentStatusButton({ live, onClick }: { live: boolean; onClick: () => void }) {
  return (
    <Button variant="outline" onClick={onClick} className={`h-9 gap-2 border-border bg-card px-3 text-xs font-medium ${live ? "text-success" : "text-warning"}`}>
      <span className={`size-1.5 rounded-full ${live ? "bg-success" : "bg-warning"}`} />
      {live ? "LIVE" : "PAUSED"}
    </Button>
  );
}

function SearchResults({
  term,
  results,
  onSelect,
  onOpenAudit,
}: {
  term: string;
  results: DashboardLog[];
  onSelect: (entry: DashboardLog) => void;
  onOpenAudit: () => void;
}) {
  return (
    <section className="overflow-hidden border border-border bg-card shadow-[var(--shadow-panel)]">
      <div className="flex items-center justify-between border-b border-border px-4 py-3.5">
        <div>
          <p className="text-sm font-medium">Search results</p>
          <p className="mt-1 text-xs text-muted-foreground">Showing matches for "{term.trim()}"</p>
        </div>
        <Button variant="ghost" size="sm" className="h-7 px-2 text-xs text-muted-foreground" onClick={onOpenAudit}>
          Open audit
          <ChevronRight className="size-3" />
        </Button>
      </div>
      <div className="divide-y divide-border">
        {results.length === 0 ? (
          <div className="px-4 py-6 text-sm text-muted-foreground">No matching orders, customers, or agent actions yet.</div>
        ) : (
          results.map((entry) => (
            <button
              key={getEntryId(entry)}
              type="button"
              className="grid w-full gap-2 bg-transparent px-4 py-3 text-left transition-colors hover:bg-muted/30 md:grid-cols-[160px_220px_1fr_120px] md:items-center md:gap-4"
              onClick={() => onSelect(entry)}
            >
              <span className="text-xs tabular-nums text-muted-foreground">{getEntryTime(entry)}</span>
              <span className="text-sm font-medium text-foreground">{getEntryLabel(entry)}</span>
              <span className="text-xs leading-relaxed text-muted-foreground">{getEntryReason(entry)}</span>
              <span className={`text-xs font-medium ${getEntryOutcomeClass(entry)}`}>{getEntryOutcome(entry)}</span>
            </button>
          ))
        )}
      </div>
    </section>
  );
}

function Overview({
  auditLogs,
  onOpenAudit,
  onSelectEntry,
  onClearAudit,
}: {
  auditLogs: DashboardLog[];
  onOpenAudit: () => void;
  onSelectEntry: (entry: DashboardLog) => void;
  onClearAudit: () => void;
}) {
  const [metrics, setMetrics] = useState<any>({ revenue_today: 0, orders_today: 0, upsell_conversion: 0, agent_actions: 0 });

  useEffect(() => {
    let mounted = true;

    async function loadMetrics() {
      try {
        const result = await fetchMetrics();
        if (mounted) setMetrics(result.metrics || {});
      } catch (error) {
        console.error(error);
      }
    }

    loadMetrics();
    const id = window.setInterval(loadMetrics, 5000);
    return () => {
      mounted = false;
      window.clearInterval(id);
    };
  }, []);

  return (
    <>
      <section className="grid border border-border bg-card shadow-[var(--shadow-panel)] sm:grid-cols-2 xl:grid-cols-4">
        <Kpi label="Revenue today" value={formatCurrency(Number(metrics.revenue_today || 0))} change="Live" detail="verified orders" icon={CircleDollarSign} positive />
        <Kpi label="Orders" value={`${metrics.orders_today ?? 0}`} change="Live" detail="paid today" icon={Package} positive />
        <Kpi label="Upsell conversion" value={`${Math.round(Number(metrics.upsell_conversion || 0))}%`} change="Live" detail="accepted proposals" icon={Target} positive />
        <Kpi label="Agent actions" value={String(metrics.agent_actions ?? 0)} change="Live" detail="recorded events" icon={Activity} positive />
      </section>
      <section className="grid gap-5 xl:grid-cols-[minmax(260px,0.88fr)_minmax(440px,1.5fr)_minmax(300px,1fr)]">
        <ActivityFeed logs={auditLogs} onOpenAudit={onOpenAudit} onSelectEntry={onSelectEntry} onClear={onClearAudit} />
        <RevenueChart totalRevenue={Number(metrics.revenue_today || 0)} orderCount={Number(metrics.orders_today || 0)} agentActions={Number(metrics.agent_actions || 0)} />
        <AuditPreview logs={auditLogs} onOpenAudit={onOpenAudit} onSelectEntry={onSelectEntry} />
      </section>
    </>
  );
}

function Kpi({
  label,
  value,
  change,
  detail,
  icon: Icon,
  positive,
}: {
  label: string;
  value: string;
  change: string;
  detail: string;
  icon: typeof Activity;
  positive?: boolean;
}) {
  return (
    <div className="border-b border-border p-5 last:border-b-0 sm:nth-[odd]:border-r xl:border-b-0 xl:border-r xl:last:border-r-0">
      <div className="flex items-center justify-between">
        <span className="text-xs text-muted-foreground">{label}</span>
        <Icon className="size-4 text-primary/80" />
      </div>
      <p className="mt-3 text-2xl font-semibold tabular-nums tracking-tight">{value}</p>
      <div className="mt-2 flex items-center gap-1.5 text-xs">
        {positive ? <ArrowUpRight className="size-3.5 text-success" /> : <ArrowDownRight className="size-3.5 text-warning" />}
        <span className={positive ? "text-success" : "text-warning"}>{change}</span>
        <span className="text-muted-foreground">{detail}</span>
      </div>
    </div>
  );
}

function PanelHeader({
  icon: Icon,
  title,
  meta,
  action,
  onAction,
  secondaryAction,
  onSecondaryAction,
}: {
  icon: typeof Activity;
  title: string;
  meta?: string;
  action?: string;
  onAction?: () => void;
  secondaryAction?: string;
  onSecondaryAction?: () => void;
}) {
  return (
    <div className="flex items-center justify-between border-b border-border px-4 py-3.5">
      <div className="flex items-center gap-2.5">
        <Icon className="size-4 text-primary" />
        <h2 className="text-sm font-medium">{title}</h2>
        {meta && <span className="text-xs text-muted-foreground">{meta}</span>}
      </div>
      <div className="flex items-center gap-1">
        {secondaryAction && (
          <Button variant="ghost" size="sm" className="h-7 px-2 text-[11px] text-muted-foreground" onClick={onSecondaryAction}>
            {secondaryAction}
          </Button>
        )}
        {action && (
          <Button variant="ghost" size="sm" className="h-7 px-2 text-xs text-muted-foreground" onClick={onAction}>
            {action}
            <ChevronRight className="size-3" />
          </Button>
        )}
      </div>
    </div>
  );
}

function ActivityFeed({
  logs,
  onOpenAudit,
  onSelectEntry,
  onClear,
}: {
  logs: DashboardLog[];
  onOpenAudit?: () => void;
  onSelectEntry: (entry: DashboardLog) => void;
  onClear: () => void;
}) {
  const visibleLogs = logs.slice(0, 6);

  return (
    <div className="overflow-hidden border border-border bg-card shadow-[var(--shadow-panel)]">
      <PanelHeader icon={Zap} title="Agent activity" meta="Live" action="View all" onAction={onOpenAudit} secondaryAction="Clear" onSecondaryAction={onClear} />
      <div className="divide-y divide-border">
        {visibleLogs.length === 0 ? (
          <div className="px-4 py-8 text-center text-xs text-muted-foreground">No agent activity yet</div>
        ) : (
          visibleLogs.map((entry) => <ActivityRow key={getEntryId(entry)} entry={entry} onClick={() => onSelectEntry(entry)} />)
        )}
      </div>
      <div className="flex items-center justify-between border-t border-border bg-muted/30 px-4 py-3 text-[11px] text-muted-foreground">
        <span>Showing the latest {visibleLogs.length} actions</span>
        <button type="button" className="font-medium text-primary hover:text-primary/80" onClick={onOpenAudit}>
          Open trail
        </button>
      </div>
    </div>
  );
}

function ActivityRow({ entry, onClick }: { entry: DashboardLog; onClick?: () => void }) {
  const outcome = getEntryOutcome(entry);
  const outcomeClass = outcome === "Recorded" ? "bg-success/10 text-success" : outcome === "Skipped" ? "bg-warning/10 text-warning" : "bg-destructive/10 text-destructive";

  return (
    <button type="button" className="group flex w-full gap-3 bg-transparent px-4 py-3 text-left transition-colors hover:bg-muted/30" onClick={onClick}>
      <div className="mt-1 flex size-6 shrink-0 items-center justify-center rounded border border-border bg-muted/50">
        <Sparkles className="size-3 text-primary" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-2">
          <p className="truncate text-xs font-semibold text-foreground">{getEntryReason(entry)}</p>
          <span className={`shrink-0 rounded px-1.5 py-0.5 text-[10px] font-medium ${outcomeClass}`}>{outcome}</span>
        </div>
        <div className="mt-1 flex items-center gap-2 text-[11px] text-muted-foreground">
          <span className="font-medium text-foreground/80">{getEntryLabel(entry)}</span>
          <span>·</span>
          <span className="tabular-nums">{getEntryTime(entry)}</span>
          {getEntryValue(entry) ? <span className="ml-auto tabular-nums text-foreground">{getEntryValue(entry)}</span> : null}
        </div>
      </div>
    </button>
  );
}

function RevenueChart({
  totalRevenue = 0,
  orderCount = 0,
  agentActions = 0,
}: {
  totalRevenue?: number;
  orderCount?: number;
  agentActions?: number;
}) {
  const [liveChartData, setLiveChartData] = useState<any[]>([]);

  useEffect(() => {
    let mounted = true;

    async function loadChart() {
      try {
        const data = await fetchChartData();
        if (mounted && data.chart?.length) setLiveChartData(data.chart);
      } catch {
        // An unavailable metrics endpoint must not become invented revenue.
      }
    }

    loadChart();
    const id = window.setInterval(loadChart, 8000);
    return () => {
      mounted = false;
      window.clearInterval(id);
    };
  }, []);

  const peakHour = useMemo(() => {
    if (liveChartData.length === 0) return "--";
    return [...liveChartData].sort((left, right) => Number(right.today) - Number(left.today))[0]?.hour ?? "--";
  }, [liveChartData]);

  return (
    <div className="overflow-hidden border border-border bg-card shadow-[var(--shadow-panel)]">
      <PanelHeader icon={BarChart3} title="Revenue performance" meta="Today · INR" action="Details" />
      <div className="p-4 pb-2">
        <div className="flex items-end justify-between">
          <div>
            <p className="text-3xl font-semibold tabular-nums tracking-tight gradient-text-primary">{formatCurrency(totalRevenue)}</p>
            <p className="mt-1 text-xs text-success">
              +18.4% <span className="text-muted-foreground">vs yesterday</span>
            </p>
          </div>
          <div className="flex gap-4 text-[11px] text-muted-foreground">
            <span className="flex items-center gap-1.5">
              <i className="size-1.5 rounded-full bg-primary" />
              Today
            </span>
            <span className="flex items-center gap-1.5">
              <i className="size-1.5 rounded-full bg-muted-foreground/50" />
              Yesterday
            </span>
          </div>
        </div>
        <div className="mt-5 h-[250px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={liveChartData} margin={{ top: 10, right: 4, bottom: 0, left: -18 }}>
              <XAxis dataKey="hour" axisLine={false} tickLine={false} tick={{ fill: "var(--color-muted-foreground)", fontSize: 10 }} />
              <YAxis axisLine={false} tickLine={false} tick={{ fill: "var(--color-muted-foreground)", fontSize: 10 }} tickFormatter={(value) => formatCurrency(Number(value))} />
              <Tooltip
                contentStyle={{
                  background: "var(--color-card)",
                  border: "1px solid var(--color-border)",
                  borderRadius: "4px",
                  color: "var(--color-foreground)",
                  fontSize: "12px",
                }}
                formatter={(value: number, name: string) => [formatCurrency(Number(value)), name === "today" ? "Today" : "Yesterday"]}
              />
              <Line type="monotone" dataKey="yesterday" stroke="var(--chart-yesterday)" strokeWidth={1.5} strokeDasharray="4 4" dot={false} />
              <Line type="monotone" dataKey="today" stroke="var(--chart-revenue)" strokeWidth={2.5} dot={{ r: 2.5, fill: "var(--chart-revenue)", strokeWidth: 0 }} activeDot={{ r: 4 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
      <div className="grid grid-cols-3 border-t border-border">
        <ChartStat label="Peak hour" value={peakHour} />
        <ChartStat label="Avg. order value" value={orderCount > 0 ? formatCurrency(totalRevenue / orderCount) : "₹0"} />
        <ChartStat label="Agent contribution" value={agentActions > 0 ? formatCurrency(totalRevenue) : "₹0"} />
      </div>
    </div>
  );
}

function ChartStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="border-r border-border p-3 last:border-r-0">
      <p className="text-[10px] text-muted-foreground">{label}</p>
      <p className="mt-1 text-xs font-medium tabular-nums">{value}</p>
    </div>
  );
}

function AuditPreview({
  logs,
  onOpenAudit,
  onSelectEntry,
}: {
  logs: DashboardLog[];
  onOpenAudit?: () => void;
  onSelectEntry: (entry: DashboardLog) => void;
}) {
  const previewEntries = logs.slice(0, 4);

  return (
    <div className="overflow-hidden border border-border bg-card shadow-[var(--shadow-panel)]">
      <PanelHeader icon={FileClock} title="Audit log" meta="Today" action="Open trail" onAction={onOpenAudit} />
      <div className="divide-y divide-border">
        {previewEntries.map((entry) => (
          <AuditRow key={getEntryId(entry)} entry={entry} onClick={() => onSelectEntry(entry)} />
        ))}
      </div>
      <div className="border-t border-border bg-muted/30 px-4 py-3 text-center text-[11px] text-muted-foreground">Every decision includes a reason</div>
    </div>
  );
}

function AuditRow({ entry, onClick }: { entry: DashboardLog; onClick?: () => void }) {
  const toneClass =
    getEntryOutcome(entry) === "Recorded" ? "bg-success shadow-glow-success" : getEntryOutcome(entry) === "Skipped" ? "bg-warning" : "bg-destructive";

  return (
    <button type="button" className="flex w-full gap-3 bg-transparent px-4 py-3.5 text-left hover:bg-muted/30" onClick={onClick}>
      <span className={`mt-1.5 size-1.5 shrink-0 rounded-full ${toneClass}`} />
      <div className="min-w-0">
        <div className="flex items-center justify-between gap-2">
          <p className={`text-xs font-medium ${getEntryOutcomeClass(entry)}`}>{getEntryLabel(entry)}</p>
          <span className="shrink-0 text-[10px] tabular-nums text-muted-foreground">{getEntryTime(entry)}</span>
        </div>
        <p className="mt-1.5 text-[11px] leading-relaxed text-muted-foreground">{getEntryReason(entry)}</p>
      </div>
    </button>
  );
}

function AgentControl({ live, onToggle, logs }: { live: boolean; onToggle: () => void; logs: DashboardLog[] }) {
  return (
    <div className="space-y-5">
      <div className="grid gap-5 lg:grid-cols-[1.25fr_0.75fr]">
        <div className="border border-border bg-card shadow-[var(--shadow-panel)]">
          <PanelHeader icon={Bot} title="Agent status" meta="Autonomous revenue agent" />
          <div className="flex flex-col gap-6 p-5 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-4">
              <div className={`flex size-12 items-center justify-center rounded-full ${live ? "bg-success/10 text-success" : "bg-warning/10 text-warning"}`}>
                <Bot className="size-6" />
              </div>
              <div>
                <p className="font-medium">{live ? "Agent is live" : "Agent is paused"}</p>
                <p className="mt-1 max-w-md text-sm text-muted-foreground">
                  {live ? "Monitoring carts and assisting customers within your configured guardrails." : "No new autonomous actions will be initiated until you resume."}
                </p>
              </div>
            </div>
            <Button variant="outline" onClick={onToggle} className={live ? "text-warning" : "text-success"}>
              {live ? "Pause agent" : "Go live"}
            </Button>
          </div>
        </div>
        <div className="border border-border bg-card shadow-[var(--shadow-panel)]">
          <PanelHeader icon={Gauge} title="Policy health" />
          <div className="space-y-4 p-5">
            <div className="flex items-end justify-between">
              <span className="text-sm text-muted-foreground">Actions within policy</span>
              <span className="text-2xl font-semibold tabular-nums">Configured</span>
            </div>
            <div className="h-1.5 overflow-hidden rounded-full bg-muted">
              <div className="h-full w-full rounded-full bg-success" />
            </div>
            <p className="text-xs text-muted-foreground">Guardrails are enforced by the backend policy engine.</p>
          </div>
        </div>
        <div className="grid gap-5 lg:grid-cols-2">
          <LimitsPanel />
          <RecentActions logs={logs} />
        </div>
      </div>
    </div>
  );
}

function LimitsPanel() {
  const [maxOrderValue, setMaxOrderValue] = useState(10000);
  const [maxRetries, setMaxRetries] = useState(3);
  const [upsellThreshold, setUpsellThreshold] = useState(1500);

  return (
    <div className="border border-border bg-card shadow-[var(--shadow-panel)]">
      <PanelHeader icon={Settings2} title="Operating limits" meta="Applied instantly" />
      <div className="space-y-5 p-5">
        <Limit label="Max order value" value={maxOrderValue} onChange={setMaxOrderValue} hint="Orders above this value require review" min={5000} max={50000} step={500} />
        <Limit label="Max payment retries" value={maxRetries} onChange={setMaxRetries} hint="Displayed control; gateway retries remain server-side" min={1} max={5} step={1} />
        <Limit label="Max upsell value" value={upsellThreshold} onChange={setUpsellThreshold} hint="Must remain within the merchant policy" min={0} max={1500} step={50} />
      </div>
    </div>
  );
}

function Limit({
  label,
  value,
  onChange,
  hint,
  min,
  max,
  step,
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
  hint: string;
  min: number;
  max: number;
  step: number;
}) {
  const clampedValue = Math.min(max, Math.max(min, value));
  const displayValue = label.includes("order") ? formatCurrency(clampedValue) : label.includes("retries") ? `${clampedValue} attempt${clampedValue === 1 ? "" : "s"}` : `${clampedValue}% intent`;

  return (
    <div>
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-sm font-medium">{label}</p>
          <p className="mt-1 text-xs text-muted-foreground">{hint}</p>
        </div>
        <div className="flex items-center gap-2">
          <input
            className="w-20 rounded border border-border bg-background px-2 py-1 text-right text-xs font-medium tabular-nums"
            type="number"
            min={min}
            max={max}
            step={step}
            value={clampedValue}
            onChange={(event) => onChange(Math.min(max, Math.max(min, Number(event.target.value) || min)))}
            aria-label={label}
          />
          <span className="hidden shrink-0 border border-border bg-muted/30 px-2 py-1 text-[11px] font-medium tabular-nums md:inline-flex">{displayValue}</span>
        </div>
      </div>
      <input className="mt-4 h-1.5 w-full cursor-pointer accent-primary" type="range" min={min} max={max} step={step} value={clampedValue} onChange={(event) => onChange(Number(event.target.value))} aria-label={label} />
      <div className="mt-1 flex justify-between text-[10px] text-muted-foreground">
        <span>{label.includes("order") ? formatCurrency(min) : label.includes("retries") ? `${min}` : `${min}%`}</span>
        <span>{label.includes("order") ? formatCurrency(max) : label.includes("retries") ? `${max}` : `${max}%`}</span>
      </div>
    </div>
  );
}

function RecentActions({ logs = [] }: { logs?: DashboardLog[] }) {
  return (
    <div className="border border-border bg-card shadow-[var(--shadow-panel)]">
      <PanelHeader icon={Activity} title="Last 5 actions" action="View audit" />
      <div className="divide-y divide-border">
        {logs.slice(0, 5).map((item) => (
          <div key={getEntryId(item)} className="flex items-center justify-between px-5 py-3">
            <div className="flex items-center gap-2.5">
              <span className="size-1.5 rounded-full bg-success" />
              <span className="text-xs">{getEntryLabel(item)}</span>
            </div>
            <span className="text-[11px] tabular-nums text-muted-foreground">{getEntryTime(item)}</span>
          </div>
        ))}
        {logs.length === 0 && <p className="px-5 py-4 text-xs text-muted-foreground">No recorded agent actions yet.</p>}
      </div>
    </div>
  );
}

function CheckoutSimulation() {
  const [step, setStep] = useState(1);
  const [transactionDialogOpen, setTransactionDialogOpen] = useState(false);
  const [agentSuggestion, setAgentSuggestion] = useState({
    item: "Handcrafted dupatta",
    price: 399,
    reason: "Adds a complementary festive finish to the current outfit.",
  });

  useEffect(() => {
    let active = true;

    async function loadSuggestion() {
      try {
        const discovery = await searchShop("I need a festive outfit under 4000");
        const upsell = discovery.upsell?.product;
        if (active && upsell) {
          setAgentSuggestion({
            item: upsell.name,
            price: upsell.price,
            reason: discovery.upsell.reason || "A related item from the merchant catalog.",
          });
          return;
        }

        const logs = await fetchAuditLogs();
        const suggestion = [...(logs.logs || [])].find((entry: DashboardLog) => entry?.action === "analyze_cart")?.outputs?.suggestion;

        if (!active) return;
        if (suggestion?.item) {
          setAgentSuggestion({
            item: cleanDisplayText(suggestion.item, "Handcrafted dupatta"),
            price: Number(suggestion.price || 399),
            reason: cleanDisplayText(suggestion.reason, "Adds a complementary festive finish to the current outfit."),
          });
          return;
        }
      } catch (error) {
        console.error("suggestion load failed", error);
      }

      if (active) {
        setAgentSuggestion({
          item: "Handcrafted dupatta",
          price: 399,
          reason: "Adds a complementary festive finish to the current outfit.",
        });
      }
    }

    loadSuggestion();
    return () => {
      active = false;
    };
  }, []);

  return (
    <>
      <div className="grid gap-5 xl:grid-cols-[1fr_0.8fr_0.85fr]">
        <div className="border border-border bg-card shadow-[var(--shadow-panel)]">
          <PanelHeader icon={ShoppingBag} title="Customer cart" meta="Simulation · #ZA-10482" />
          <div className="divide-y divide-border">
            {[
              { name: "Hand-block printed kurta", detail: "Indigo · M", price: "₹2,499", qty: 1 },
              { name: "Chanderi silk dupatta", detail: "Fuchsia · One size", price: "₹1,299", qty: 1 },
              { name: "Cotton straight pants", detail: "Ivory · M", price: "₹1,799", qty: 1 },
            ].map((product) => (
              <div key={product.name} className="flex items-center gap-3 p-4">
                <div className="flex size-12 items-center justify-center rounded border border-border bg-muted">
                  <Package className="size-5 text-muted-foreground" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">{product.name}</p>
                  <p className="mt-1 text-xs text-muted-foreground">{product.detail} · Qty {product.qty}</p>
                </div>
                <span className="text-sm font-medium tabular-nums">{product.price}</span>
              </div>
            ))}
          </div>
          <div className="space-y-2 border-t border-border p-4 text-sm">
            <div className="flex justify-between text-muted-foreground">
              <span>Subtotal</span>
              <span className="tabular-nums">₹5,597</span>
            </div>
            <div className="flex justify-between text-muted-foreground">
              <span>Agent discount</span>
              <span className="tabular-nums text-success">-₹300</span>
            </div>
            <div className="flex justify-between border-t border-border pt-3 font-semibold">
              <span>Total</span>
              <span className="tabular-nums">₹5,297</span>
            </div>
          </div>
        </div>

        <div className="border border-primary/30 bg-primary/5 shadow-[var(--shadow-panel)]">
          <PanelHeader icon={Sparkles} title="Agent suggestion" meta="Confidence 94%" />
          <div className="p-5">
            <div className="flex items-center gap-2 text-xs font-medium text-primary">
              <Target className="size-4" /> Personalised for this cart
            </div>
            <h2 className="mt-5 text-xl font-semibold tracking-tight">{cleanDisplayText(agentSuggestion.item, "Handcrafted dupatta")}</h2>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{cleanDisplayText(agentSuggestion.reason, "Adds a complementary festive finish to the current outfit.")}</p>
            <div className="mt-6 flex items-end justify-between gap-3">
              <div>
                <p className="text-[11px] uppercase tracking-[0.16em] text-muted-foreground">Suggested add-on</p>
                <p className="mt-2 text-2xl font-semibold tabular-nums">{formatCurrency(agentSuggestion.price)}</p>
              </div>
              <Button variant="outline" className="h-9 border-primary/30 text-primary hover:bg-primary/5">
                Add to cart
              </Button>
            </div>
          </div>
        </div>

        <PaymentTracker
          step={step}
          onStep={(nextStep) => {
            setStep(nextStep);
            if (nextStep >= 3) {
              setTransactionDialogOpen(true);
              toast.success("Transaction completed successfully");
            }
          }}
        />
      </div>

      <Dialog open={transactionDialogOpen} onOpenChange={setTransactionDialogOpen}>
        <DialogContent className="border-border bg-card sm:max-w-[420px]">
          <DialogHeader>
            <DialogTitle>Payment captured</DialogTitle>
            <DialogDescription>The order has been successfully created and logged in the audit trail.</DialogDescription>
          </DialogHeader>
          <div className="rounded border border-success/30 bg-success/5 p-4 text-sm text-foreground">
            <div className="flex items-center justify-between gap-3">
              <span className="text-muted-foreground">Amount</span>
              <span className="text-lg font-semibold tabular-nums">₹5,297</span>
            </div>
            <div className="mt-3 flex items-center justify-between gap-3">
              <span className="text-muted-foreground">Status</span>
              <span className="inline-flex items-center gap-2 font-medium text-success">
                <Check className="size-4" /> Completed
              </span>
            </div>
          </div>
          <DialogFooter>
            <Button onClick={() => setTransactionDialogOpen(false)}>Close</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

function PaymentTracker({ step, onStep }: { step: number; onStep: (step: number) => void }) {
  const steps = [
    { label: "Pending", icon: Clock3 },
    { label: "Captured", icon: ReceiptIndianRupee },
    { label: "Logged", icon: FileClock },
  ];

  return (
    <div className="border border-border bg-card shadow-[var(--shadow-panel)]">
      <PanelHeader icon={ReceiptIndianRupee} title="Payment status" meta="₹5,297" />
      <div className="p-5">
        <div className="space-y-0">
          {steps.map((item, index) => {
            const Icon = item.icon;
            const complete = index < step;
            const current = index === step;

            return (
              <div key={item.label} className="flex gap-3">
                <div className="flex flex-col items-center">
                  <div className={`flex size-8 items-center justify-center rounded-full border ${complete ? "border-success bg-success text-background" : current ? "border-primary bg-primary/10 text-primary" : "border-border text-muted-foreground"}`}>
                    {complete ? <Check className="size-4" /> : <Icon className="size-4" />}
                  </div>
                  {index < steps.length - 1 && <div className={`my-1 h-8 w-px ${complete ? "bg-success" : "bg-border"}`} />}
                </div>
                <div className="pt-1">
                  <p className={`text-sm font-medium ${current ? "text-foreground" : complete ? "text-success" : "text-muted-foreground"}`}>{item.label}</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {index === 0 ? "Awaiting customer confirmation" : index === 1 ? "Razorpay payment captured" : "Decision added to audit trail"}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
        <Button variant="outline" className="mt-6 w-full" disabled={step >= 3} onClick={() => onStep(Math.min(step + 1, 3))}>
          {step === 1 ? "Capture payment" : step === 2 ? "Log transaction" : "Transaction complete"}
          {step < 3 && <ChevronRight />}
        </Button>
        <p className="mt-3 text-center text-[11px] text-muted-foreground">Test mode · No real payment will be processed</p>
      </div>
    </div>
  );
}

function AuditTrail({
  logs,
  searchTerm = "",
  onSelectEntry,
  onClear,
}: {
  logs: DashboardLog[];
  searchTerm?: string;
  onSelectEntry?: (entry: DashboardLog) => void;
  onClear: () => void;
}) {
  const baseLogs = logs;
  const normalizedTerm = searchTerm.trim().toLowerCase();
  const displayLogs = baseLogs.filter((entry) => !normalizedTerm || buildSearchText(entry).includes(normalizedTerm));

  function handleExport() {
    const rows = displayLogs.map((entry) => ({
      timestamp: entry.time || entry.timestamp || "",
      action: getEntryLabel(entry),
      reason: getEntryReason(entry),
      outcome: getEntryOutcome(entry),
    }));
    const csv = ["Timestamp,Action,Reason,Outcome", ...rows.map((row) => `${row.timestamp},"${row.action.replace(/"/g, '""')}","${row.reason.replace(/"/g, '""')}","${row.outcome}"`)].join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `audit-log-${new Date().toISOString().slice(0, 10)}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="border border-border bg-card shadow-[var(--shadow-panel)]">
      <PanelHeader icon={FileClock} title="All agent decisions" meta={`${displayLogs.length} events today`} action="Export log" onAction={handleExport} secondaryAction="Clear" onSecondaryAction={onClear} />
      <div className="hidden grid-cols-[120px_180px_1fr_120px] gap-4 border-b border-border bg-muted/30 px-5 py-3 text-[11px] font-medium text-muted-foreground md:grid">
        <span>Timestamp</span>
        <span>Decision</span>
        <span>Reason</span>
        <span>Outcome</span>
      </div>
      <div className="divide-y divide-border">
        {displayLogs.length === 0 ? (
          <div className="px-5 py-8 text-center text-sm text-muted-foreground">No matching audit entries found.</div>
        ) : (
          displayLogs.map((entry) => (
            <button
              key={getEntryId(entry)}
              type="button"
              className="grid w-full gap-2 bg-transparent px-5 py-4 text-left transition-colors hover:bg-muted/30 md:grid-cols-[120px_180px_1fr_120px] md:items-center md:gap-4"
              onClick={() => onSelectEntry?.(entry)}
            >
              <span className="text-xs tabular-nums text-muted-foreground">{getEntryTime(entry)}</span>
              <span className="text-sm font-medium text-foreground">{getEntryLabel(entry)}</span>
              <span className="text-xs leading-relaxed text-muted-foreground">{getEntryReason(entry)}</span>
              <span className={`flex items-center gap-1.5 text-xs ${getEntryOutcomeClass(entry)}`}>
                <Check className="size-3.5" />
                {getEntryOutcome(entry)}
              </span>
            </button>
          ))
        )}
      </div>
    </div>
  );
}

function MerchantOrders() {
  const [orders, setOrders] = useState<any[]>([]);
  useEffect(() => { fetchOrders().then((result) => setOrders(result.orders || [])).catch(() => setOrders([])); }, []);
  return <section className="border border-border bg-card shadow-[var(--shadow-panel)]"><PanelHeader icon={ReceiptIndianRupee} title="Orders" meta={`${orders.length} recorded`} /><div className="divide-y divide-border">{orders.length === 0 ? <p className="p-6 text-sm text-muted-foreground">No orders yet. Completed Razorpay payments will appear here.</p> : orders.map((order) => <div key={order.id} className="grid gap-2 px-5 py-4 text-sm md:grid-cols-[150px_1fr_110px_130px]"><span className="font-medium">{order.order_number}</span><span>{order.customer?.name || "Guest"}<span className="ml-2 text-muted-foreground">{order.items?.map((item: any) => `${item.name} × ${item.quantity}`).join(", ")}</span></span><span className="font-medium">{formatCurrency(order.total)}</span><span className="text-xs text-success">{order.payment_status} · {order.status}</span></div>)}</div></section>;
}

function MerchantCustomers() {
  const [customers, setCustomers] = useState<any[]>([]);
  useEffect(() => { fetchCustomers().then((result) => setCustomers(result.customers || [])).catch(() => setCustomers([])); }, []);
  return <section className="border border-border bg-card shadow-[var(--shadow-panel)]"><PanelHeader icon={ShoppingBag} title="Customers" meta={`${customers.length} demo identities`} /><div className="divide-y divide-border">{customers.length === 0 ? <p className="p-6 text-sm text-muted-foreground">Customers appear after a shopper starts a demo session.</p> : customers.map((customer) => <div key={customer.id} className="grid gap-2 px-5 py-4 text-sm md:grid-cols-[1fr_1fr_110px_140px]"><span className="font-medium">{customer.name}</span><span className="text-muted-foreground">{customer.email || customer.contact || "No contact"}</span><span>{customer.order_count} orders</span><span>{formatCurrency(customer.total_spend || 0)} spent</span></div>)}</div></section>;
}

function MerchantCatalog() {
  const [products, setProducts] = useState<any[]>([]);
  const [importing, setImporting] = useState(false);
  const [status, setStatus] = useState("");
  useEffect(() => { fetchProducts().then((result) => setProducts(result.products || [])).catch(() => setProducts([])); }, []);
  async function runImport() {
    setImporting(true);
    try {
      const result = await importCatalog();
      const summary = result.import;
      setStatus(`${summary.created} created, ${summary.updated} updated, ${summary.skipped} skipped`);
      const refreshed = await fetchProducts();
      setProducts(refreshed.products || []);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Catalog import failed");
    } finally { setImporting(false); }
  }
  return <section className="border border-border bg-card shadow-[var(--shadow-panel)]"><div className="flex items-center justify-between border-b border-border px-4 py-3.5"><div><h2 className="text-sm font-medium">Catalog</h2><p className="mt-1 text-xs text-muted-foreground">{products.length} local products · SQLite source of truth</p></div><Button size="sm" onClick={runImport} disabled={importing}>{importing ? "Importing..." : "Import Bright Data"}</Button></div>{status && <p className="border-b border-border bg-muted/30 px-5 py-3 text-xs text-muted-foreground">{status}</p>}<div className="grid gap-3 p-5 sm:grid-cols-2 lg:grid-cols-3">{products.slice(0, 30).map((product) => <div key={product.id} className="border border-border p-4"><div className="flex items-center justify-between gap-2"><p className="truncate text-sm font-medium">{product.name}</p><span className="text-xs text-success">{product.stock} in stock</span></div><p className="mt-2 text-xs text-muted-foreground">{product.category} · {product.brand || "Unbranded"}</p><p className="mt-3 font-semibold">{formatCurrency(product.price)}</p></div>)}</div></section>;
}
