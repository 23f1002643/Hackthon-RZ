import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
import {
  Activity,
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
  PanelLeft,
  Play,
  ReceiptIndianRupee,
  Search,
  Settings2,
  ShoppingBag,
  Sparkles,
  Sun,
  Target,
  X,
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

import { fetchAuditLogs, fetchMetrics, postCheckout, toggleAgent } from "@/lib/api";
import { Toaster } from "@/components/ui/sonner";
import { toast } from "sonner";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Revenue Intelligence | Zephyr Apparel" },
      { name: "description", content: "A real-time commerce agent dashboard for Zephyr Apparel." },
      { property: "og:title", content: "Revenue Intelligence | Zephyr Apparel" },
      { property: "og:description", content: "A real-time commerce agent dashboard for Zephyr Apparel." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: Dashboard,
});

type ViewId = "overview" | "agent" | "checkout" | "audit";

const navItems: { id: ViewId; label: string; icon: typeof LayoutDashboard }[] = [
  { id: "overview", label: "Overview", icon: LayoutDashboard },
  { id: "agent", label: "Agent control", icon: Bot },
  { id: "checkout", label: "Checkout simulation", icon: ShoppingBag },
  { id: "audit", label: "Audit trail", icon: FileClock },
];

const chartData = [
  { hour: "00:00", today: 4, yesterday: 6 },
  { hour: "03:00", today: 9, yesterday: 8 },
  { hour: "06:00", today: 14, yesterday: 12 },
  { hour: "09:00", today: 31, yesterday: 22 },
  { hour: "12:00", today: 47, yesterday: 39 },
  { hour: "15:00", today: 58, yesterday: 51 },
  { hour: "18:00", today: 74, yesterday: 65 },
  { hour: "21:00", today: 86, yesterday: 79 },
];

const actions = [
  { time: "09:42:18", action: "Upsell", detail: "Recommended dupatta pairing", outcome: "success", value: "+₹1,299" },
  { time: "09:41:52", action: "Checkout", detail: "Address intent confirmed", outcome: "success", value: "Captured" },
  { time: "09:40:27", action: "Recovery", detail: "Payment retry initiated", outcome: "pending", value: "Retry 1/3" },
  { time: "09:38:04", action: "Upsell", detail: "Suggested festive bundle", outcome: "success", value: "+₹2,498" },
  { time: "09:35:46", action: "Guardrail", detail: "High-value order held for review", outcome: "failed", value: "₹28,400" },
  { time: "09:32:11", action: "Checkout", detail: "Coupon eligibility checked", outcome: "success", value: "Eligible" },
];

const auditEntries = [
  { time: "09:42:18", label: "Upsell accepted", reason: "Customer viewed size guide twice; paired accessory matched cart intent.", tone: "success" },
  { time: "09:40:27", label: "Retry payment", reason: "Gateway returned a transient timeout; within the 3-attempt retry policy.", tone: "warning" },
  { time: "09:35:46", label: "Order held", reason: "Order value crossed ₹25,000 max limit; merchant review required.", tone: "danger" },
  { time: "09:32:11", label: "Coupon approved", reason: "Returning customer and cart total met the ₹2,000 threshold.", tone: "success" },
];

function Dashboard() {
  const [view, setView] = useState<ViewId>("overview");
  const [agentLive, setAgentLive] = useState(true);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [lightMode, setLightMode] = useState(false);
  const [showSearch, setShowSearch] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [clock, setClock] = useState("09:42:18");

  useEffect(() => {
    document.documentElement.classList.toggle("light", lightMode);
    const timer = window.setInterval(() => {
      setClock(new Date().toLocaleTimeString("en-IN", { hour12: false }));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [lightMode]);

  async function runSimulation() {
    try {
      const sampleCart = [
        { name: 'Hand-block printed kurta', price: 2499, qty: 1 },
        { name: 'Chanderi silk dupatta', price: 1299, qty: 1 },
      ];
      const customer = { name: 'Sim Buyer', email: 'sim@zephyr.com', contact: '9999999999' };
      const res = await postCheckout(sampleCart, customer);
      if (res?.ok) {
        toast.success('Checkout simulation completed');
      } else {
        toast.error('Checkout simulation failed');
      }
    } catch (e) {
      console.error('simulation failed', e);
      toast.error('Simulation error: ' + (e?.message || String(e)));
    }
  }

  const viewTitle = useMemo(() => navItems.find((item) => item.id === view)?.label ?? "Overview", [view]);

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
            {showSearch ? (
              <input
                autoFocus
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                onBlur={() => setShowSearch(false)}
                placeholder="Search audit, products, customers..."
                className="h-8 rounded-md border border-border bg-card px-2 text-sm text-foreground"
              />
            ) : (
              <Button variant="ghost" size="icon" className="text-muted-foreground" title="Search" aria-label="Search" onClick={() => setShowSearch(true)}>
                <Search />
              </Button>
            )}
            <Button variant="ghost" size="icon" className="relative text-muted-foreground" title="Notifications" aria-label="Notifications">
              <Bell />
              <span className="absolute right-2 top-2 size-1.5 rounded-full bg-primary" />
            </Button>
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
                <p className="text-xs font-medium">Zephyr Apparel</p>
                <p className="text-[11px] text-muted-foreground">Merchant workspace</p>
              </div>
            </div>
          </div>
        </header>

        <main className="mx-auto max-w-[1680px] space-y-6 p-5 lg:p-8">
          <div className="flex flex-col justify-between gap-4 md:flex-row md:items-end">
            <div>
              <p className="mb-2 text-xs font-medium text-primary">Thursday, 3 September 2026</p>
              <h1 className="text-2xl font-semibold tracking-tight lg:text-[28px]">{view === "overview" ? "Revenue intelligence" : viewTitle}</h1>
              <p className="mt-1 text-sm text-muted-foreground">
                {view === "overview" && "Autonomous commerce performance for Zephyr Apparel."}
                {view === "agent" && "Set the boundaries your agent must operate within."}
                {view === "checkout" && "Walk through a live agent-assisted customer checkout."}
                {view === "audit" && "A complete, reviewable record of every agent decision."}
              </p>
            </div>
            <div className="flex items-center gap-3">
              <AgentStatusButton live={agentLive} onClick={() => setConfirmOpen(true)} />
              <Button className="bg-brand-gradient text-primary-foreground shadow-sm hover:opacity-90" onClick={async () => { await runSimulation(); setView("checkout"); }}>
                <Play className="size-3.5" /> Run simulation
              </Button>
            </div>
          </div>

          {view === "overview" && <Overview />}
          {view === "agent" && <AgentControl live={agentLive} onToggle={() => setConfirmOpen(true)} />}
          {view === "checkout" && <CheckoutSimulation />}
          {view === "audit" && <AuditTrail />}
        </main>
      </div>

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
            <div className="flex items-center gap-2 font-medium"><Gauge className="size-4 text-primary" /> Current guardrails are active</div>
            <p className="mt-1 pl-6 text-xs text-muted-foreground">Max order ₹25,000 · 3 retries · 12% upsell threshold</p>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmOpen(false)}>Cancel</Button>
            <Button className={agentLive ? "bg-destructive text-destructive-foreground hover:bg-destructive/90" : "bg-brand-gradient text-primary-foreground hover:opacity-90"} onClick={() => { setAgentLive((value) => !value); setConfirmOpen(false); }}>
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
          <p className="text-sm font-semibold text-sidebar-foreground">Zephyr</p>
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
          <Settings2 /><span className="whitespace-nowrap opacity-0 transition-opacity duration-150 group-hover/sidebar:opacity-100">Settings</span>
        </Button>
      </div>
      <div className="border-t border-sidebar-border p-3">
        <div className="flex items-center gap-3 rounded-md bg-sidebar-accent p-2">
          <div className="flex size-8 shrink-0 items-center justify-center rounded-full border border-primary/30 bg-primary/10 text-[10px] font-semibold text-primary">AR</div>
          <div className="min-w-0 whitespace-nowrap opacity-0 transition-opacity duration-150 group-hover/sidebar:opacity-100">
            <p className="truncate text-xs font-medium">Ananya Rao</p><p className="text-[10px] text-muted-foreground">Admin</p>
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

function Overview() {
  const [metrics, setMetrics] = useState<any>({ revenue: 0, order_count: 0, upsell_acceptance_rate: 0 });

  useEffect(() => {
    let mounted = true;
    async function load() {
      try {
        const m = await fetchMetrics();
        if (mounted) setMetrics(m);
      } catch (e) {
        console.error(e);
      }
    }
    load();
    return () => { mounted = false; };
  }, []);

  return (
    <>
      <section className="grid border border-border bg-card shadow-[var(--shadow-panel)] sm:grid-cols-2 xl:grid-cols-4">
        <Kpi label="Revenue today" value={`₹${metrics.revenue}`} change="+18.4%" detail="vs yesterday" icon={CircleDollarSign} positive />
        <Kpi label="Orders" value={`${metrics.order_count}`} change="+12.8%" detail="vs yesterday" icon={Package} positive />
        <Kpi label="Upsell accepted" value={`${Math.round(metrics.upsell_acceptance_rate)}`} change="17.8%" detail="of eligible orders" icon={Target} positive />
        <Kpi label="Agent actions" value="1,284" change="99.2%" detail="within policy" icon={Activity} positive />
      </section>
      <section className="grid gap-5 xl:grid-cols-[minmax(260px,0.88fr)_minmax(440px,1.5fr)_minmax(300px,1fr)]">
        <ActivityFeed />
        <RevenueChart />
        <AuditPreview />
      </section>
    </>
  );
}

function Kpi({ label, value, change, detail, icon: Icon, positive }: { label: string; value: string; change: string; detail: string; icon: typeof Activity; positive?: boolean }) {
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

function PanelHeader({ icon: Icon, title, meta, action }: { icon: typeof Activity; title: string; meta?: string; action?: string }) {
  return (
    <div className="flex items-center justify-between border-b border-border px-4 py-3.5">
      <div className="flex items-center gap-2.5"><Icon className="size-4 text-primary" /><h2 className="text-sm font-medium">{title}</h2>{meta && <span className="text-xs text-muted-foreground">{meta}</span>}</div>
      {action && <Button variant="ghost" size="sm" className="h-7 px-2 text-xs text-muted-foreground">{action}<ChevronRight className="size-3" /></Button>}
    </div>
  );
}

function ActivityFeed() {
  const [logs, setLogs] = useState<any[]>([]);

  useEffect(() => {
    let mounted = true;
    async function poll() {
      try {
        const data = await fetchAuditLogs();
        if (!mounted) return;
        setLogs(data.logs || []);
      } catch (e) {
        console.error(e);
      }
    }
    poll();
    const id = setInterval(poll, 5000);
    return () => { mounted = false; clearInterval(id); };
  }, []);

  return (
    <div className="overflow-hidden border border-border bg-card shadow-[var(--shadow-panel)]">
      <PanelHeader icon={Zap} title="Agent activity" meta="Live" action="View all" />
      <div className="divide-y divide-border">
        {logs.slice(0, 6).map((l, i) => (
          <ActivityRow key={i} time={l.timestamp?.split('T')[1]?.split('.')[0] ?? ''} action={l.action} detail={l.reason || ''} outcome={l.error ? 'failed' : 'success'} value={l.outputs && l.outputs.raw && l.outputs.raw.amount ? `₹${(l.outputs.raw.amount/100).toFixed(2)}` : ''} />
        ))}
      </div>
      <div className="border-t border-border bg-muted/30 px-4 py-3 text-center text-[11px] text-muted-foreground">Showing the latest {logs.length} actions</div>
    </div>
  );
}

function ActivityRow({ time, action, detail, outcome, value }: typeof actions[number]) {
  const outcomeClass = outcome === "success" ? "bg-success/10 text-success" : outcome === "pending" ? "bg-warning/10 text-warning" : "bg-destructive/10 text-destructive";
  return (
    <div className="group flex gap-3 px-4 py-3 transition-colors hover:bg-muted/30">
      <div className="mt-1 flex size-6 shrink-0 items-center justify-center rounded border border-border bg-muted/50"><Sparkles className="size-3 text-primary" /></div>
      <div className="min-w-0 flex-1"><div className="flex items-center justify-between gap-2"><p className="truncate text-xs font-medium">{detail}</p><span className={`shrink-0 rounded px-1.5 py-0.5 text-[10px] font-medium ${outcomeClass}`}>{outcome}</span></div><div className="mt-1 flex items-center gap-2 text-[11px] text-muted-foreground"><span>{action}</span><span>·</span><span className="tabular-nums">{time}</span><span className="ml-auto tabular-nums text-foreground/75">{value}</span></div></div>
    </div>
  );
}

function RevenueChart() {
  return (
    <div className="overflow-hidden border border-border bg-card shadow-[var(--shadow-panel)]">
      <PanelHeader icon={BarChart3} title="Revenue performance" meta="Today · INR" action="Details" />
      <div className="p-4 pb-2">
        <div className="flex items-end justify-between"><div><p className="text-3xl font-semibold tabular-nums tracking-tight">₹1,84,620</p><p className="mt-1 text-xs text-success">+18.4% <span className="text-muted-foreground">vs yesterday</span></p></div><div className="flex gap-4 text-[11px] text-muted-foreground"><span className="flex items-center gap-1.5"><i className="size-1.5 rounded-full bg-primary" />Today</span><span className="flex items-center gap-1.5"><i className="size-1.5 rounded-full bg-muted-foreground/50" />Yesterday</span></div></div>
        <div className="mt-5 h-[250px] w-full">
          <ResponsiveContainer width="100%" height="100%"><LineChart data={chartData} margin={{ top: 10, right: 4, bottom: 0, left: -18 }}>
            <XAxis dataKey="hour" axisLine={false} tickLine={false} tick={{ fill: "var(--color-muted-foreground)", fontSize: 10 }} />
            <YAxis axisLine={false} tickLine={false} tick={{ fill: "var(--color-muted-foreground)", fontSize: 10 }} tickFormatter={(value) => `₹${value}k`} />
            <Tooltip contentStyle={{ background: "var(--color-card)", border: "1px solid var(--color-border)", borderRadius: "4px", color: "var(--color-foreground)", fontSize: "12px" }} formatter={(value: number, name: string) => [`₹${value}k`, name === "today" ? "Today" : "Yesterday"]} />
            <Line type="monotone" dataKey="yesterday" stroke="var(--chart-yesterday)" strokeWidth={1.5} strokeDasharray="4 4" dot={false} />
            <Line type="monotone" dataKey="today" stroke="var(--chart-revenue)" strokeWidth={2.5} dot={{ r: 2.5, fill: "var(--chart-revenue)", strokeWidth: 0 }} activeDot={{ r: 4 }} />
          </LineChart></ResponsiveContainer>
        </div>
      </div>
      <div className="grid grid-cols-3 border-t border-border"><ChartStat label="Peak hour" value="18:00" /><ChartStat label="Avg. order value" value="₹431" /><ChartStat label="Agent contribution" value="₹42.8k" /></div>
    </div>
  );
}

function ChartStat({ label, value }: { label: string; value: string }) { return <div className="border-r border-border p-3 last:border-r-0"><p className="text-[10px] text-muted-foreground">{label}</p><p className="mt-1 text-xs font-medium tabular-nums">{value}</p></div>; }

function AuditPreview() {
  return <div className="overflow-hidden border border-border bg-card shadow-[var(--shadow-panel)]"><PanelHeader icon={FileClock} title="Audit log" meta="Today" action="Open trail" /><div className="divide-y divide-border">{auditEntries.map((entry) => <AuditRow key={entry.time} {...entry} />)}</div><div className="border-t border-border bg-muted/30 px-4 py-3 text-center text-[11px] text-muted-foreground">Every decision includes a reason</div></div>;
}

function AuditRow({ time, label, reason, tone }: typeof auditEntries[number]) {
  const toneClass = tone === "success" ? "bg-success" : tone === "warning" ? "bg-warning" : "bg-destructive";
  return <div className="flex gap-3 px-4 py-3.5"><span className={`mt-1.5 size-1.5 shrink-0 rounded-full ${toneClass}`} /><div className="min-w-0"><div className="flex items-center justify-between gap-2"><p className="text-xs font-medium">{label}</p><span className="shrink-0 text-[10px] tabular-nums text-muted-foreground">{time}</span></div><p className="mt-1.5 text-[11px] leading-relaxed text-muted-foreground">{reason}</p></div></div>;
}

function AgentControl({ live, onToggle }: { live: boolean; onToggle: () => void }) {
  return <div className="space-y-5"><div className="grid gap-5 lg:grid-cols-[1.25fr_0.75fr]"><div className="border border-border bg-card shadow-[var(--shadow-panel)]"><PanelHeader icon={Bot} title="Agent status" meta="Autonomous revenue agent" /><div className="flex flex-col gap-6 p-5 sm:flex-row sm:items-center sm:justify-between"><div className="flex items-center gap-4"><div className={`flex size-12 items-center justify-center rounded-full ${live ? "bg-success/10 text-success" : "bg-warning/10 text-warning"}`}><Bot className="size-6" /></div><div><p className="font-medium">{live ? "Agent is live" : "Agent is paused"}</p><p className="mt-1 max-w-md text-sm text-muted-foreground">{live ? "Monitoring carts and assisting customers within your configured guardrails." : "No new autonomous actions will be initiated until you resume."}</p></div></div><Button variant="outline" onClick={onToggle} className={live ? "text-warning" : "text-success"}>{live ? "Pause agent" : "Go live"}</Button></div></div><div className="border border-border bg-card shadow-[var(--shadow-panel)]"><PanelHeader icon={Gauge} title="Policy health" /><div className="space-y-4 p-5"><div className="flex items-end justify-between"><span className="text-sm text-muted-foreground">Actions within policy</span><span className="text-2xl font-semibold tabular-nums">99.2%</span></div><div className="h-1.5 overflow-hidden rounded-full bg-muted"><div className="h-full w-[99.2%] rounded-full bg-success" /></div><p className="text-xs text-muted-foreground">12 actions held for merchant review today</p></div></div></div><div className="grid gap-5 lg:grid-cols-2"><LimitsPanel /><RecentActions /></div></div>;
}

function LimitsPanel() {
  return <div className="border border-border bg-card shadow-[var(--shadow-panel)]"><PanelHeader icon={Settings2} title="Operating limits" meta="Applied instantly" /><div className="space-y-5 p-5"><Limit label="Max order value" value="₹25,000" hint="Orders above this value require review" min="5000" max="50000" progress="40%" /><Limit label="Max payment retries" value="3 attempts" hint="Stops after the third gateway failure" min="1" max="5" progress="50%" /><Limit label="Upsell threshold" value="12% intent" hint="Minimum confidence before a recommendation" min="5" max="25" progress="35%" /></div></div>;
}

function Limit({ label, value, hint, min, max, progress }: { label: string; value: string; hint: string; min: string; max: string; progress: string }) {
  return <div><div className="flex items-center justify-between gap-3"><div><p className="text-sm font-medium">{label}</p><p className="mt-1 text-xs text-muted-foreground">{hint}</p></div><span className="shrink-0 border border-border bg-muted/30 px-2 py-1 text-xs font-medium tabular-nums">{value}</span></div><input className="mt-4 h-1.5 w-full cursor-pointer accent-primary" type="range" min={min} max={max} defaultValue={Number(min) + Math.round((Number(max) - Number(min)) * parseInt(progress) / 100)} aria-label={label} /><div className="mt-1 flex justify-between text-[10px] text-muted-foreground"><span>{min === "5000" ? "₹5,000" : min === "1" ? "1" : "5%"}</span><span>{max === "50000" ? "₹50,000" : max === "5" ? "5" : "25%"}</span></div></div>;
}

function RecentActions() { return <div className="border border-border bg-card shadow-[var(--shadow-panel)]"><PanelHeader icon={Activity} title="Last 5 actions" action="View audit" /><div className="divide-y divide-border">{actions.slice(0, 5).map((item) => <div key={item.time} className="flex items-center justify-between px-5 py-3"><div className="flex items-center gap-2.5"><span className="size-1.5 rounded-full bg-success" /><span className="text-xs">{item.detail}</span></div><span className="text-[11px] tabular-nums text-muted-foreground">{item.time}</span></div>)}</div></div>; }

function CheckoutSimulation() {
  const [step, setStep] = useState(1);
  return <div className="grid gap-5 xl:grid-cols-[1fr_0.8fr_0.85fr]"><div className="border border-border bg-card shadow-[var(--shadow-panel)]"><PanelHeader icon={ShoppingBag} title="Customer cart" meta="Simulation · #ZA-10482" /><div className="divide-y divide-border">{[{ name: "Hand-block printed kurta", detail: "Indigo · M", price: "₹2,499", qty: 1 }, { name: "Chanderi silk dupatta", detail: "Fuchsia · One size", price: "₹1,299", qty: 1 }, { name: "Cotton straight pants", detail: "Ivory · M", price: "₹1,799", qty: 1 }].map((product) => <div key={product.name} className="flex items-center gap-3 p-4"><div className="flex size-12 items-center justify-center rounded border border-border bg-muted"><Package className="size-5 text-muted-foreground" /></div><div className="min-w-0 flex-1"><p className="truncate text-sm font-medium">{product.name}</p><p className="mt-1 text-xs text-muted-foreground">{product.detail} · Qty {product.qty}</p></div><span className="text-sm font-medium tabular-nums">{product.price}</span></div>)}</div><div className="space-y-2 border-t border-border p-4 text-sm"><div className="flex justify-between text-muted-foreground"><span>Subtotal</span><span className="tabular-nums">₹5,597</span></div><div className="flex justify-between text-muted-foreground"><span>Agent discount</span><span className="tabular-nums text-success">−₹300</span></div><div className="flex justify-between border-t border-border pt-3 font-semibold"><span>Total</span><span className="tabular-nums">₹5,297</span></div></div></div><div className="border border-primary/30 bg-primary/5 shadow-[var(--shadow-panel)]"><PanelHeader icon={Sparkles} title="Agent suggestion" meta="Confidence 94%" /><div className="p-5"><div className="flex items-center gap-2 text-xs font-medium text-primary"><Target className="size-4" /> Personalised for this cart</div><h2 className="mt-5 text-xl font-semibold tracking-tight">Complete the festive look</h2><p className="mt-2 text-sm leading-relaxed text-muted-foreground">Recommend the <span className="font-medium text-foreground">handcrafted jutti</span> in tan. The customer has a kurta-led cart and has previously purchased ethnic footwear.</p><div className="mt-5 border border-border bg-card p-3"><div className="flex items-center gap-3"><div className="flex size-10 items-center justify-center rounded bg-muted"><ShoppingBag className="size-4 text-primary" /></div><div className="flex-1"><p className="text-xs font-medium">Leather jutti · Tan</p><p className="mt-1 text-[11px] text-muted-foreground">₹1,499 · Free delivery</p></div><span className="text-xs font-semibold text-success">+₹1,499</span></div></div><Button className="mt-5 w-full bg-brand-gradient text-primary-foreground hover:opacity-90" onClick={() => setStep(2)}>{step === 1 ? "Accept suggestion" : "Suggestion accepted"}{step === 1 ? <ArrowUpRight /> : <Check />}</Button></div></div><PaymentTracker step={step} onStep={setStep} /></div>;
}

function PaymentTracker({ step, onStep }: { step: number; onStep: (step: number) => void }) {
  const steps = [{ label: "Pending", icon: Clock3 }, { label: "Captured", icon: ReceiptIndianRupee }, { label: "Logged", icon: FileClock }];
  return <div className="border border-border bg-card shadow-[var(--shadow-panel)]"><PanelHeader icon={ReceiptIndianRupee} title="Payment status" meta="₹5,297" /><div className="p-5"><div className="space-y-0">{steps.map((item, index) => { const Icon = item.icon; const complete = index < step; const current = index === step; return <div key={item.label} className="flex gap-3"><div className="flex flex-col items-center"><div className={`flex size-8 items-center justify-center rounded-full border ${complete ? "border-success bg-success text-background" : current ? "border-primary bg-primary/10 text-primary" : "border-border text-muted-foreground"}`}>{complete ? <Check className="size-4" /> : <Icon className="size-4" />}</div>{index < steps.length - 1 && <div className={`my-1 h-8 w-px ${complete ? "bg-success" : "bg-border"}`} />}</div><div className="pt-1"><p className={`text-sm font-medium ${current ? "text-foreground" : complete ? "text-success" : "text-muted-foreground"}`}>{item.label}</p><p className="mt-1 text-xs text-muted-foreground">{index === 0 ? "Awaiting customer confirmation" : index === 1 ? "Razorpay payment captured" : "Decision added to audit trail"}</p></div></div>; })}</div><Button variant="outline" className="mt-6 w-full" disabled={step >= 3} onClick={() => onStep(Math.min(step + 1, 3))}>{step === 1 ? "Capture payment" : step === 2 ? "Log transaction" : "Transaction complete"}{step < 3 && <ChevronRight />}</Button><p className="mt-3 text-center text-[11px] text-muted-foreground">Test mode · No real payment will be processed</p></div></div>;
}

function AuditTrail() { return <div className="border border-border bg-card shadow-[var(--shadow-panel)]"><PanelHeader icon={FileClock} title="All agent decisions" meta="1,284 events today" action="Export log" /><div className="hidden grid-cols-[120px_180px_1fr_120px] gap-4 border-b border-border bg-muted/30 px-5 py-3 text-[11px] font-medium text-muted-foreground md:grid"><span>Timestamp</span><span>Decision</span><span>Reason</span><span>Outcome</span></div><div className="divide-y divide-border">{[...auditEntries, { time: "09:28:44", label: "Bundle surfaced", reason: "Three complementary categories detected with 68% purchase affinity.", tone: "success" as const }, { time: "09:22:09", label: "Shipping waived", reason: "Cart total crossed the free delivery threshold for the active region.", tone: "success" as const }].map((entry) => <div key={entry.time} className="grid gap-2 px-5 py-4 md:grid-cols-[120px_180px_1fr_120px] md:items-center md:gap-4"><span className="text-xs tabular-nums text-muted-foreground">{entry.time}</span><span className="text-sm font-medium">{entry.label}</span><span className="text-xs leading-relaxed text-muted-foreground">{entry.reason}</span><span className="flex items-center gap-1.5 text-xs text-success"><Check className="size-3.5" /> Recorded</span></div>)}</div></div>; }
