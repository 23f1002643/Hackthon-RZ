import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { ArrowRight, Check, ShoppingBag, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { addCartItem, createCart, createOrder, fetchCustomerOrders, getCart, getOrCreateCustomer, markPaymentFailed, removeCartItem, searchShop, verifyPayment } from "@/lib/api";
import { toast } from "sonner";
import { ThemeToggle } from "@/components/theme-toggle";

export const Route = createFileRoute("/shop")({ component: Shop });

type Discovery = {
  intent?: { budget?: number; occasion?: string };
  recommendation?: { product: { id: number; name: string; price: number; description: string; image_url?: string }; reason: string };
  upsell?: { product: { id: number; name: string; price: number }; reason: string };
  upsell_options?: { product: { id: number; name: string; price: number; image_url?: string }; reason: string }[];
};

type ChatMessage = { role: "shopper" | "assistant"; text: string };

declare global {
  interface Window {
    Razorpay?: new (options: Record<string, unknown>) => { open: () => void };
  }
}

function money(value = 0) {
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(value);
}

function Shop() {
  const [query, setQuery] = useState("I need something for my sister's wedding under ₹4000");
  const [discovery, setDiscovery] = useState<Discovery | null>(null);
  const [cart, setCart] = useState<any>(null);
  const [order, setOrder] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [customerId, setCustomerId] = useState<number | null>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [assistantMessage, setAssistantMessage] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);

  useEffect(() => {
    const script = document.createElement("script");
    script.src = "https://checkout.razorpay.com/v1/checkout.js";
    script.async = true;
    document.body.appendChild(script);
    return () => script.remove();
  }, []);

  useEffect(() => {
    const stored = window.localStorage.getItem("vastra-demo-customer-id");
    if (!stored) return;
    const id = Number(stored);
    if (!Number.isInteger(id)) return;
    setCustomerId(id);
    fetchCustomerOrders(id).then((result) => setHistory(result.orders || [])).catch(() => setHistory([]));
    const storedCartId = Number(window.localStorage.getItem("vastra-demo-cart-id-v2"));
    if (Number.isInteger(storedCartId)) getCart(storedCartId).then((result) => setCart(result.cart)).catch(() => window.localStorage.removeItem("vastra-demo-cart-id-v2"));
  }, []);

  async function discover() {
    setLoading(true);
    setOrder(null);
    try {
      const result = await searchShop(query, messages.map((message) => `${message.role}: ${message.text}`));
      setDiscovery(result);
      const message = result.message || (result.recommendation ? `I found ${result.recommendation.product.name} because ${result.recommendation.reason}` : "I couldn't find a close match. Try another fashion category, occasion, color, or budget.");
      setAssistantMessage(message);
      setMessages((current) => [...current, { role: "shopper", text: query }, { role: "assistant", text: message }].slice(-8));
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "We could not search the catalog.");
    } finally {
      setLoading(false);
    }
  }

  async function addProductToCart(productId: number, isUpsell = false) {
    try {
      let activeCart = cart;
      if (!activeCart) {
        const customer = await getOrCreateCustomer({ name: "Demo Shopper", email: "demo@vastrastudio.local" });
        const id = customer.customer.id as number;
        window.localStorage.setItem("vastra-demo-customer-id", String(id));
        setCustomerId(id);
        const created = await createCart(discovery?.intent?.budget, true, id);
        window.localStorage.setItem("vastra-demo-cart-id-v2", String(created.cart.id));
        activeCart = created.cart;
      }
      const result = await addCartItem(activeCart.id, productId, isUpsell);
      setCart(result.cart);
      toast.success("Added to your cart");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not add that product.");
    }
  }

  async function addUpsell() {
    if (!cart || !discovery?.upsell?.product) return;
    await addProductToCart(discovery.upsell.product.id, true);
  }

  async function removeItem(itemId: number) {
    if (!cart) return;
    try {
      const result = await removeCartItem(cart.id, itemId);
      setCart(result.cart);
      toast.success("Removed from your cart");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not remove that item.");
    }
  }

  async function addSuggestion(productId: number) {
    await addProductToCart(productId, true);
  }

  async function confirmOrder() {
    if (!cart) return;
    setLoading(true);
    try {
      const result = await createOrder(cart.id, true);
      if (!result.checkout?.key || !window.Razorpay) {
        throw new Error("Secure checkout is not configured on the server.");
      }
      const checkout = new window.Razorpay({
        key: result.checkout.key,
        amount: result.checkout.amount,
        currency: result.checkout.currency,
        name: result.checkout.name,
        description: result.checkout.description,
        order_id: result.checkout.razorpay_order_id,
        handler: async (response: { razorpay_payment_id: string; razorpay_order_id: string; razorpay_signature: string }) => {
          try {
            const verified = await verifyPayment(result.order.id, response);
            setOrder(verified.order);
                  toast.success("Payment verified and order confirmed");
                  if (customerId) {
                    const updated = await fetchCustomerOrders(customerId);
                    setHistory(updated.orders || []);
                  }
          } catch (error) {
            toast.error(error instanceof Error ? error.message : "Payment verification failed.");
          }
        },
        modal: {
          ondismiss: async () => {
            try {
              await markPaymentFailed(result.order.id, "Buyer closed Razorpay Checkout.");
              setOrder({ ...result.order, status: "PAYMENT_FAILED" });
              toast("Payment was not completed. Your cart is safe.");
            } catch {
              toast.error("Payment was not completed. Retry from your cart.");
            }
          },
        },
      });
      checkout.open();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not start secure payment.");
    } finally {
      setLoading(false);
    }
  }

  const recommendation = discovery?.recommendation?.product;
  return (
    <main className="min-h-screen bg-background text-foreground">
      <section className="border-b border-border bg-[radial-gradient(circle_at_top_right,oklch(0.35_0.12_300/.45),transparent_45%),radial-gradient(circle_at_top_left,oklch(0.3_0.12_265/.35),transparent_40%)] px-5 py-16 lg:px-16">
        <div className="relative mx-auto max-w-6xl">
          <div className="absolute right-5 top-5 lg:right-16 lg:top-5"><ThemeToggle /></div>
          <div className="flex items-center gap-2 text-sm font-medium text-primary"><Sparkles className="size-4" /> Vastra Studio AI Commerce</div>
          <h1 className="mt-5 max-w-3xl text-4xl font-semibold tracking-tight lg:text-6xl">Tell us what you are looking for.</h1>
          <p className="mt-4 max-w-2xl text-base text-muted-foreground">A real merchant catalog, bounded recommendations, and a secure checkout when you are ready.</p>
          <div className="mt-8 flex max-w-3xl flex-col gap-3 sm:flex-row">
            <input value={query} onChange={(event) => setQuery(event.target.value)} className="min-h-12 flex-1 rounded-md border border-border bg-card px-4 text-sm outline-none focus:border-primary" onKeyDown={(event) => event.key === "Enter" && discover()} />
            <Button onClick={discover} disabled={loading} className="min-h-12 bg-brand-gradient text-primary-foreground"><Sparkles className="size-4" /> {loading ? "Finding matches..." : "Find products"}</Button>
          </div>
          {messages.length > 0 && <div className="mt-8 max-w-3xl space-y-2">{messages.map((message, index) => <div key={`${message.role}-${index}`} className={`max-w-[90%] border px-4 py-3 text-sm ${message.role === "shopper" ? "ml-auto border-border bg-card" : "border-primary/30 bg-primary/5"}`}><span className="mr-2 text-[10px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">{message.role === "shopper" ? "You" : "Vastra Studio"}</span>{message.text}</div>)}</div>}
        </div>
      </section>

      <section className="mx-auto grid max-w-6xl gap-6 px-5 py-10 lg:grid-cols-[1fr_360px] lg:px-16">
        <div className="space-y-6">
          {assistantMessage && <div className="border border-primary/30 bg-primary/5 p-4 text-sm text-foreground"><Sparkles className="mr-2 inline size-4 text-primary" />{assistantMessage}</div>}
          {recommendation ? (
            <article className="border border-border bg-card p-6 shadow-[var(--shadow-panel)]">
              <p className="text-xs font-medium uppercase tracking-[0.18em] text-primary">Recommended from the catalog</p>
              <div className="mt-5 flex flex-col gap-5 sm:flex-row sm:items-center">
                <div className="flex size-32 shrink-0 items-center justify-center overflow-hidden rounded-md bg-muted text-xs text-muted-foreground"><img src={recommendation.image_url || ""} alt={recommendation.name} className="h-full w-full object-cover" onError={(event) => { event.currentTarget.style.display = "none"; }} /><span>Image unavailable</span></div>
                <div><h2 className="text-2xl font-semibold">{recommendation.name}</h2><p className="mt-2 text-sm text-muted-foreground">{recommendation.description}</p><p className="mt-4 text-2xl font-semibold">{money(recommendation.price)}</p><Button className="mt-4" onClick={() => addProductToCart(recommendation.id)}>Add to cart</Button></div>
              </div>
              <div className="mt-6 border-l-2 border-primary pl-4 text-sm text-muted-foreground"><span className="font-medium text-foreground">Why this match? </span>{discovery?.recommendation?.reason}</div>
            </article>
          ) : <div className="border border-dashed border-border p-10 text-center text-sm text-muted-foreground">Your recommendation will appear here.</div>}
          {(discovery?.upsell_options?.length || 0) > 0 && <section className="border border-border bg-card p-5"><p className="text-xs font-medium uppercase tracking-[0.15em] text-primary">Complete the look</p><h2 className="mt-2 text-lg font-semibold">Curated suggestions</h2><div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{discovery?.upsell_options?.map((suggestion) => { const inCart = cart?.items?.some((item: any) => item.product_id === suggestion.product.id); return <article key={suggestion.product.id} className="border border-border p-4"><div className="flex h-20 items-center justify-center overflow-hidden bg-muted text-xs text-muted-foreground"><img src={suggestion.product.image_url || ""} alt={suggestion.product.name} className="h-full w-full object-cover" onError={(event) => { event.currentTarget.style.display = "none"; }} /><span>Image unavailable</span></div><h3 className="mt-3 truncate text-sm font-semibold">{suggestion.product.name}</h3><p className="mt-1 text-xs text-muted-foreground">{suggestion.reason}</p><div className="mt-3 flex items-center justify-between gap-2"><span className="font-semibold">{money(suggestion.product.price)}</span><Button size="sm" variant="outline" disabled={inCart} onClick={() => addSuggestion(suggestion.product.id)}>{inCart ? "Added" : "Add"}</Button></div></article>; })}</div></section>}
        </div>

        <aside className="h-fit border border-border bg-card p-5 shadow-[var(--shadow-panel)]"><div className="flex items-center justify-between"><h2 className="font-semibold">Your cart</h2><ShoppingBag className="size-4 text-muted-foreground" /></div>{cart?.items?.length ? <><div className="mt-5 space-y-3">{cart.items.map((item: any) => <div key={item.id} className="flex items-center justify-between gap-3 text-sm"><span className="min-w-0"><span className="block truncate">{item.name}</span><span className="text-muted-foreground">× {item.quantity}</span></span><span className="flex shrink-0 items-center gap-2"><span className="font-medium">{money(item.line_total)}</span><Button type="button" variant="ghost" size="icon" className="size-7 text-muted-foreground hover:text-destructive" title={`Remove ${item.name}`} aria-label={`Remove ${item.name}`} onClick={() => removeItem(item.id)}>×</Button></span></div>)}</div><div className="mt-5 border-t border-border pt-4"><div className="flex justify-between font-semibold"><span>Total</span><span>{money(cart.total)}</span></div>{cart.budget != null && <p className={`mt-2 text-xs ${cart.over_budget ? "text-destructive" : "text-success"}`}>{cart.over_budget ? "Over your budget" : `${money(cart.budget_remaining)} remaining in budget`}</p>}<Button className="mt-5 w-full" onClick={confirmOrder} disabled={loading || cart.over_budget || order?.status === "COMPLETED"}>{loading ? "Opening secure checkout..." : "Confirm and continue"}<ArrowRight className="size-4" /></Button>{order?.status === "COMPLETED" ? <div className="mt-4 border border-success/40 bg-success/10 p-3 text-sm"><Check className="mb-1 size-4 text-success" />Payment verified. Order {order.order_number} is confirmed.</div> : order?.status === "PAYMENT_FAILED" ? <div className="mt-4 border border-destructive/40 bg-destructive/10 p-3 text-sm">Payment was not completed. Your cart is still safe; try again when ready.</div> : null}</div></> : <p className="mt-8 text-sm text-muted-foreground">Add a recommendation to begin.</p>}</aside>
      </section>
      <section className="mx-auto max-w-6xl px-5 pb-14 lg:px-16">
        <div className="border border-border bg-card p-5">
          <div className="flex items-center justify-between"><h2 className="font-semibold">My orders</h2><span className="text-xs text-muted-foreground">Demo session history</span></div>
          {history.length === 0 ? <p className="mt-4 text-sm text-muted-foreground">Verified orders will remain here after checkout.</p> : <div className="mt-4 divide-y divide-border">{history.map((item: any) => <div key={item.id} className="flex flex-wrap items-center justify-between gap-3 py-3 text-sm"><span className="font-medium">{item.order_number}</span><span>{item.items?.map((line: any) => `${line.name} × ${line.quantity}`).join(", ")}</span><span>{money(item.total)}</span><span className="text-xs text-muted-foreground">{item.payment_status}</span></div>)}</div>}
        </div>
      </section>
    </main>
  );
}
