from pathlib import Path

path = Path(r"c:\Users\Admin\Desktop\RZ-build\agent-growth-hub-main\src\routes\index.tsx")
text = path.read_text(encoding="utf-8")
start = text.index("function CheckoutSimulation() {")
end = text.index("function PaymentTracker({ step, onStep }", start)
replacement = '''function CheckoutSimulation() {
  const [step, setStep] = useState(1);
  const [agentSuggestion, setAgentSuggestion] = useState({
    item: "Handcrafted dupatta",
    price: 399,
    reason: "Adds a complementary festive finish to the current outfit.",
  });

  useEffect(() => {
    let active = true;

    async function loadSuggestion() {
      const cart = [
        { name: "Hand-block printed kurta", price: 2499, qty: 1 },
        { name: "Chanderi silk dupatta", price: 1299, qty: 1 },
        { name: "Cotton straight pants", price: 1799, qty: 1 },
      ];

      try {
        const checkoutResult = await postCheckout(cart, {
          name: "Sim Buyer",
          email: "sim@zephyr.com",
          contact: "9999999999",
        });

        if (!checkoutResult?.ok) {
          throw new Error("checkout failed");
        }

        const logs = await fetchAuditLogs();
        const suggestion = [...(logs.logs || [])].reverse().find((entry: any) => entry?.action === "analyze_cart")?.outputs?.suggestion;

        if (!active) return;
        if (suggestion && suggestion.item) {
          setAgentSuggestion({
            item: suggestion.item,
            price: Number(suggestion.price || 399),
            reason: suggestion.reason || "Adds a complementary festive finish to the current outfit.",
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
    return () => { active = false; };
  }, []);

  return <div className="grid gap-5 xl:grid-cols-[1fr_0.8fr_0.85fr]"><div className="border border-border bg-card shadow-[var(--shadow-panel)]"><PanelHeader icon={ShoppingBag} title="Customer cart" meta="Simulation · #ZA-10482" /><div className="divide-y divide-border">{[{ name: "Hand-block printed kurta", detail: "Indigo · M", price: "₹2,499", qty: 1 }, { name: "Chanderi silk dupatta", detail: "Fuchsia · One size", price: "₹1,299", qty: 1 }, { name: "Cotton straight pants", detail: "Ivory · M", price: "₹1,799", qty: 1 }].map((product) => <div key={product.name} className="flex items-center gap-3 p-4"><div className="flex size-12 items-center justify-center rounded border border-border bg-muted"><Package className="size-5 text-muted-foreground" /></div><div className="min-w-0 flex-1"><p className="truncate text-sm font-medium">{product.name}</p><p className="mt-1 text-xs text-muted-foreground">{product.detail} · Qty {product.qty}</p></div><span className="text-sm font-medium tabular-nums">{product.price}</span></div>)}</div><div className="space-y-2 border-t border-border p-4 text-sm"><div className="flex justify-between text-muted-foreground"><span>Subtotal</span><span className="tabular-nums">₹5,597</span></div><div className="flex justify-between text-muted-foreground"><span>Agent discount</span><span className="tabular-nums text-success">−₹300</span></div><div className="flex justify-between border-t border-border pt-3 font-semibold"><span>Total</span><span className="tabular-nums">₹5,297</span></div></div></div><div className="border border-primary/30 bg-primary/5 shadow-[var(--shadow-panel)]"><PanelHeader icon={Sparkles} title="Agent suggestion" meta="Confidence 94%" /><div className="p-5"><div className="flex items-center gap-2 text-xs font-medium text-primary"><Target className="size-4" /> Personalised for this cart</div><h2 className="mt-5 text-xl font-semibold tracking-tight">{agentSuggestion.item}</h2><p className="mt-2 text-sm leading-relaxed text-muted-foreground">{agentSuggestion.reason}</p><div className="mt-6 flex items-end justify-between gap-3"><div><p className="text-[11px] uppercase tracking-[0.16em] text-muted-foreground">Suggested add-on</p><p className="mt-2 text-2xl font-semibold tabular-nums">₹{agentSuggestion.price.toLocaleString("en-IN")}</p></div><Button variant="outline" className="h-9 border-primary/30 text-primary hover:bg-primary/5">Add to cart</Button></div></div></div><PaymentTracker step={step} onStep={setStep} /></div>;
}

'''
updated = text[:start] + replacement + text[end:]
path.write_text(updated, encoding="utf-8")
print("patched checkout suggestion")
