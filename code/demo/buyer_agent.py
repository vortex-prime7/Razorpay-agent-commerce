"""
Autonomous buyer agent — the 30-second money shot for the panel.

A standalone "AI shopping agent" that talks to the merchant purely over the
agent-readable interface: it reads the JSON-LD feed, picks an item, checks
stock, and completes a purchase — with NO human clicking anything. It also
demonstrates the safe-retry contract by reusing one idempotency key.

Run the server first (uvicorn app.main:app --reload), then:
    python -m demo.buyer_agent
"""
import sys
import uuid
import httpx

BASE = "http://127.0.0.1:8000"


def main():
    with httpx.Client(base_url=BASE, timeout=10) as c:
        # 1) Discover the catalog the way an autonomous agent would.
        feed = c.get("/catalog/agent-feed").json()
        items = feed["itemListElement"]
        print(f"[agent] read agent-feed: {len(items)} products discovered")

        # 2) Pick the first in-stock product.
        pick = next((i for i in items
                     if i["offers"]["availability"].endswith("InStock")), None)
        if not pick:
            print("[agent] nothing in stock, stopping."); return
        pid = pick["productID"]
        print(f"[agent] selected {pick['name']} ({pid}) @ ₹{pick['offers']['price']}")

        # 3) Verify availability before committing.
        avail = c.get(f"/catalog/products/{pid}/availability", params={"quantity": 1}).json()
        print(f"[agent] availability check: in_stock={avail['in_stock']}")

        # 4) Buy — one idempotency key for this logical purchase.
        key = "buy_" + uuid.uuid4().hex[:10]
        r = c.post("/checkout", json={"base_product_id": pid, "quantity": 1, "idempotency_key": key}).json()
        print(f"[agent] checkout -> {r['status']}: {r['message']}")
        if r.get("upsell_offered"):
            print(f"[agent] agent upsold add-on {r['addon_product_id']} "
                  f"at {r['discount_percent']}% (confidence {r['agent_confidence']}, "
                  f"brain={r['agent_provider']})")

        # 5) Prove idempotency: replay the same key -> no second charge.
        r2 = c.post("/checkout", json={"base_product_id": pid, "quantity": 1, "idempotency_key": key}).json()
        print(f"[agent] replay same key -> {r2['status']}: {r2['message']}")

    print("\n[agent] done. Open", BASE + "/dashboard", "to see the audit trail.")


if __name__ == "__main__":
    try:
        main()
    except httpx.ConnectError:
        print("Could not reach the server. Start it first: uvicorn app.main:app --reload")
        sys.exit(1)
