"""
Demo 8 – Resumable AI Procurement Agent (LangGraph Persistence + Interrupt)

Scenario: An AI agent handles purchase requests. When a purchase exceeds
€10,000 it must pause for manager approval — which may come hours or days later.

The graph:

  START → lookup_vendors → fetch_pricing → compare_quotes
        → request_approval (INTERRUPTS here — process exits!)
        → submit_purchase_order → notify_employee → END

To simulate a real-world "late second invocation" across process restarts,
we use SqliteSaver (file-based checkpoint) and two CLI modes:

  python demo8.1-purchase-agent.py              # First run  — steps 1-3, then suspends
  python demo8.1-purchase-agent.py --resume     # Second run — manager approves, steps 5-6

Between the two runs the Python process exits completely.  The full agent
state (vendor data, pricing, chosen quote) survives on disk in SQLite.
"""

import sys
import os
import re
import sqlite3
import time
from typing import TypedDict, Optional, Any

import requests
from langchain.tools import tool
from langchain_core.messages import HumanMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import interrupt, Command
from langchain_google_genai import ChatGoogleGenerativeAI

# ─── State ────────────────────────────────────────────────────────────────────

class ProcurementState(TypedDict, total=False):
    request: str
    quantity: int
    item_name: str
    vendors: list[dict]
    quotes: list[dict]
    best_quote: dict
    approval_status: str
    rejection_reason: str
    po_number: str
    notification: str


# ─── LLM (used only for the notification step to make it feel "agentic") ─────

llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite")


# ─── Node functions ──────────────────────────────────────────────────────────

DEFAULT_VENDOR_PRICES = {
    "Dell": 248.0,
    "Lenovo": 235.0,
    "HP": 259.0,
}


def parse_quantity_and_item(request_text: str) -> tuple[int, str]:
    """Extract quantity and requested item from a free-form request string."""
    qty_match = re.search(r"\b(\d+)\b", request_text)
    quantity = int(qty_match.group(1)) if qty_match else 1

    lowered = request_text.lower()
    item_name = "laptops"
    item_patterns = [
        r"\d+\s+([a-zA-Z\- ]+?)\s+for\b",
        r"order\s+\d+\s+([a-zA-Z\- ]+?)\b",
        r"purchase\s+\d+\s+([a-zA-Z\- ]+?)\b",
    ]
    for pattern in item_patterns:
        match = re.search(pattern, lowered)
        if match:
            candidate = match.group(1).strip()
            if candidate:
                item_name = candidate
                break

    if item_name.endswith(" team"):
        item_name = item_name[:-5].strip()
    return quantity, item_name


def _days_from_shipping_info(shipping_info: str) -> Optional[int]:
    if not shipping_info:
        return None

    shipping_info = shipping_info.lower()
    if "week" in shipping_info:
        week_match = re.search(r"(\d+)\s*week", shipping_info)
        if week_match:
            return int(week_match.group(1)) * 7
    day_match = re.search(r"(\d+)\s*day", shipping_info)
    if day_match:
        return int(day_match.group(1))
    if "within 2 weeks" in shipping_info:
        return 14
    if "in stock" in shipping_info or "ships immediately" in shipping_info:
        return 3
    return None


def _fetch_laptop_catalog() -> list[dict]:
    response = requests.get(
        "https://dummyjson.com/products/category/laptops",
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()
    products = data.get("products", [])
    return products if isinstance(products, list) else []


def _select_best_product_for_vendor(vendor: str) -> dict:
    """Pick the cheapest DummyJSON laptop that appears available within 2 weeks.

    DummyJSON does not expose real supplier-vendor matching for Dell/Lenovo/HP in this endpoint,
    so we treat the endpoint as a market feed and select the best available laptop for each vendor
    request. This keeps the demo realistic while still using live product data.
    """
    try:
        products = _fetch_laptop_catalog()
        eligible: list[dict] = []
        for product in products:
            price = product.get("price")
            stock = product.get("stock", 0)
            shipping_info = product.get("shippingInformation", "")
            delivery_days = _days_from_shipping_info(shipping_info)
            if delivery_days is None:
                delivery_days = 10 if stock and stock > 0 else 21

            if price is None:
                continue
            if stock and stock > 0 and delivery_days <= 14:
                eligible.append(
                    {
                        "product_id": product.get("id"),
                        "product_name": product.get("title", "Unknown laptop"),
                        "brand": product.get("brand", "Unknown"),
                        "unit_price": float(price),
                        "delivery_days": int(delivery_days),
                        "availability_status": product.get("availabilityStatus", "Unknown"),
                        "stock": stock,
                        "shipping_information": shipping_info,
                        "source": "dummyjson",
                    }
                )

        if eligible:
            best = min(eligible, key=lambda p: p["unit_price"])
            return best

    except Exception as exc:
        print(f"   WARNING: live product lookup failed for {vendor}: {exc}")

    default_price = DEFAULT_VENDOR_PRICES.get(vendor, 249.0)
    print(f"   WARNING: no live laptop match found for {vendor}; using fallback price €{default_price}")
    return {
        "product_id": None,
        "product_name": f"Fallback Laptop ({vendor})",
        "brand": vendor,
        "unit_price": float(default_price),
        "delivery_days": 10,
        "availability_status": "Fallback",
        "stock": 999,
        "shipping_information": "Estimated within 2 weeks",
        "source": "fallback",
    }


@tool
def get_unit_price(vendor: str) -> float:
    """Return the live unit price for the cheapest laptop available within 2 weeks for a vendor."""
    offer = _select_best_product_for_vendor(vendor)
    return float(offer["unit_price"])


def lookup_vendors(state: ProcurementState) -> dict:
    """Step 1: Look up approved vendors for laptops."""
    print("\n[Step 1] Looking up approved vendors...")
    time.sleep(1)
    quantity, item_name = parse_quantity_and_item(state["request"])

    vendors = [
        {"name": "Dell", "id": "V-001", "category": "laptops", "rating": 4.5},
        {"name": "Lenovo", "id": "V-002", "category": "laptops", "rating": 4.3},
        {"name": "HP", "id": "V-003", "category": "laptops", "rating": 4.1},
    ]
    for v in vendors:
        print(f"   Found vendor: {v['name']} (rating {v['rating']})")
    print(f"   Parsed request quantity: {quantity}")
    print(f"   Parsed item: {item_name}")
    return {"vendors": vendors, "quantity": quantity, "item_name": item_name}


def fetch_pricing(state: ProcurementState) -> dict:
    """Step 2: Ask the LLM to call the pricing tool once per vendor, then build quotes."""
    print("\n[Step 2] Fetching pricing from suppliers via tool calls...")
    quantity = state["quantity"]
    vendors = [v["name"] for v in state["vendors"]]

    pricing_llm = llm.bind_tools([get_unit_price])
    prompt = (
        "You are assisting with procurement. "
        f"The employee requested {quantity} laptops. "
        f"For each vendor in this exact list: {', '.join(vendors)}, "
        "call the get_unit_price tool exactly once. Do not skip any vendor and do not call any vendor twice."
    )

    ai_msg = pricing_llm.invoke([HumanMessage(content=prompt)])
    tool_calls = ai_msg.tool_calls or []
    seen_vendors: set[str] = set()
    quotes: list[dict[str, Any]] = []

    for call in tool_calls:
        if call.get("name") != "get_unit_price":
            continue
        vendor = str(call.get("args", {}).get("vendor", "")).strip()
        if not vendor or vendor in seen_vendors or vendor not in vendors:
            continue

        unit_price = float(get_unit_price.invoke({"vendor": vendor}))
        offer = _select_best_product_for_vendor(vendor)
        total = round(unit_price * quantity, 2)
        quote = {
            "vendor": vendor,
            "unit_price": unit_price,
            "total": total,
            "delivery_days": int(offer["delivery_days"]),
            "product_name": offer["product_name"],
            "product_id": offer["product_id"],
            "brand": offer["brand"],
            "availability_status": offer["availability_status"],
            "shipping_information": offer["shipping_information"],
            "source": offer["source"],
        }
        quotes.append(quote)
        seen_vendors.add(vendor)

    # Safety fallback if the model misses a vendor
    missing_vendors = [vendor for vendor in vendors if vendor not in seen_vendors]
    for vendor in missing_vendors:
        unit_price = float(get_unit_price.invoke({"vendor": vendor}))
        offer = _select_best_product_for_vendor(vendor)
        total = round(unit_price * quantity, 2)
        quotes.append(
            {
                "vendor": vendor,
                "unit_price": unit_price,
                "total": total,
                "delivery_days": int(offer["delivery_days"]),
                "product_name": offer["product_name"],
                "product_id": offer["product_id"],
                "brand": offer["brand"],
                "availability_status": offer["availability_status"],
                "shipping_information": offer["shipping_information"],
                "source": offer["source"],
            }
        )
        print(f"   WARNING: model missed {vendor}; filled using fallback execution path.")

    for q in quotes:
        print(
            f"   {q['vendor']}: {q['product_name']} | €{q['unit_price']}/unit x {quantity} "
            f"= €{q['total']:,} ({q['delivery_days']} day delivery)"
        )
    return {"quotes": quotes}


def compare_quotes(state: ProcurementState) -> dict:
    """Step 3: Compare quotes and pick the best one."""
    print("\n[Step 3] Comparing quotes...")
    time.sleep(0.5)
    best = min(state["quotes"], key=lambda q: q["total"])
    print(f"   Best quote: {best['vendor']} at €{best['total']:,}")
    print(
        f"   Product: {best['product_name']}"
    )
    print(
        f"   (Saves €{max(q['total'] for q in state['quotes']) - best['total']:,} "
        f"vs most expensive option)"
    )
    return {"best_quote": best}


def approval_needed(state: ProcurementState) -> str:
    return "request_approval" if state["best_quote"]["total"] > 10_000 else "submit_purchase_order"


def request_approval(state: ProcurementState) -> dict:
    """Step 4: Human-in-the-loop — request manager approval only when needed."""
    best = state["best_quote"]
    quantity = state["quantity"]
    item_name = state.get("item_name", "laptops")

    print("\n[Step 4] Order exceeds €10,000 — manager approval required!")
    print("   Sending approval request to manager...")
    amount_str = f"€{best['total']:,}"
    delivery_str = f"{best['delivery_days']} business days"
    print("   ┌─────────────────────────────────────────────┐")
    print("   │  APPROVAL NEEDED                            │")
    print(f"   │  Vendor:   {best['vendor']:<33}│")
    print(f"   │  Product:  {best['product_name'][:33]:<33}│")
    print(f"   │  Amount:   {amount_str:<33}│")
    print(f"   │  Items:    {str(quantity) + ' ' + item_name:<33}│")
    print(f"   │  Delivery: {delivery_str:<33}│")
    print("   └─────────────────────────────────────────────┘")

    decision = interrupt(
        {
            "message": (
                f"Approve purchase of {quantity} {item_name} "
                f"({best['product_name']}) from {best['vendor']} for €{best['total']:,}?"
            ),
            "vendor": best["vendor"],
            "product_name": best["product_name"],
            "amount": best["total"],
        }
    )

    print(f"\n[Step 4] Manager responded: {decision}")
    return {"approval_status": str(decision)}


def route_after_approval(state: ProcurementState) -> str:
    decision = state.get("approval_status", "")
    if "reject" in decision.lower():
        return "notify_employee"
    return "submit_purchase_order"


def submit_purchase_order(state: ProcurementState) -> dict:
    """Step 5: Submit the purchase order to the ERP system."""
    print("\n[Step 5] Submitting purchase order to ERP system...")
    time.sleep(1)
    po_number = "PO-2026-00342"
    print(f"   Purchase order created: {po_number}")
    print(f"   Vendor: {state['best_quote']['vendor']}")
    print(f"   Product: {state['best_quote']['product_name']}")
    print(f"   Amount: €{state['best_quote']['total']:,}")
    return {"po_number": po_number}


def notify_employee(state: ProcurementState) -> dict:
    """Step 6: Use LLM to draft and send a notification to the employee."""
    print("\n[Step 6] Notifying employee...")
    quantity = state["quantity"]
    item_name = state.get("item_name", "laptops")
    best = state["best_quote"]

    approval_status = state.get("approval_status", "")
    is_rejected = "reject" in approval_status.lower()

    if is_rejected:
        rejection_reason = state.get("rejection_reason") or approval_status
        prompt = (
            f"Write a brief, professional notification (2-3 sentences) to an employee "
            f"that their purchase request for {quantity} {item_name} was rejected by the manager. "
            f"Include this reason naturally: {rejection_reason}. "
            f"Be empathetic but concise."
        )
    else:
        prompt = (
            f"Write a brief, professional notification (2-3 sentences) to an employee "
            f"that their purchase request has been approved and processed. "
            f"Details: {quantity} {item_name}, chosen product {best['product_name']}, "
            f"vendor {best['vendor']}, €{best['total']:,}, PO number {state['po_number']}, "
            f"delivery in {best['delivery_days']} business days."
        )

    response = llm.invoke(prompt)
    notification = response.content
    print("   Employee notification sent:")
    print(f'   "{notification}"')

    updates: dict[str, Any] = {"notification": notification}
    if is_rejected and not state.get("rejection_reason"):
        updates["rejection_reason"] = approval_status
    return updates


# ─── Build the graph ─────────────────────────────────────────────────────────
#
#   START → lookup_vendors → fetch_pricing → compare_quotes
#         → request_approval (INTERRUPT)
#         → submit_purchase_order → notify_employee → END

builder = StateGraph(ProcurementState)

builder.add_node("lookup_vendors", lookup_vendors)
builder.add_node("fetch_pricing", fetch_pricing)
builder.add_node("compare_quotes", compare_quotes)
builder.add_node("request_approval", request_approval)
builder.add_node("submit_purchase_order", submit_purchase_order)
builder.add_node("notify_employee", notify_employee)

builder.add_edge(START, "lookup_vendors")
builder.add_edge("lookup_vendors", "fetch_pricing")
builder.add_edge("fetch_pricing", "compare_quotes")
builder.add_conditional_edges(
    "compare_quotes",
    approval_needed,
    {
        "request_approval": "request_approval",
        "submit_purchase_order": "submit_purchase_order",
    },
)
builder.add_conditional_edges(
    "request_approval",
    route_after_approval,
    {
        "submit_purchase_order": "submit_purchase_order",
        "notify_employee": "notify_employee",
    },
)
builder.add_edge("submit_purchase_order", "notify_employee")
builder.add_edge("notify_employee", END)


# ─── Checkpointer (SQLite — survives process restarts!) ──────────────────────

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "procurement_checkpoints.db")
THREAD_ID = "procurement-thread-1"
config = {"configurable": {"thread_id": THREAD_ID}}


# ─── Main ────────────────────────────────────────────────────────────────────

def run_first_invocation(graph):
    print("=" * 60)
    print("  FIRST INVOCATION — Employee submits purchase request")
    print("=" * 60)
    print('\nEmployee request: "Order 50 laptops for the new engineering team"')

    result = graph.invoke(
        {"request": "Order 50 laptops for the new engineering team"},
        config,
    )

    if result.get("__interrupt__"):
        print("\n" + "=" * 60)
        print("AGENT SUSPENDED — waiting for manager approval")
        print("=" * 60)
        print("\n  The agent process can now exit completely.")
        print("  All state (vendors, pricing, best quote) is frozen in SQLite.")
        print(f"  Checkpoint DB: {DB_PATH}")
        print(f"  Thread ID: {THREAD_ID}")
        print("\n  To resume, run:")
        print(f"    python {os.path.basename(__file__)} --resume\n")
    else:
        print("\n" + "=" * 60)
        print("PROCUREMENT COMPLETE — no approval required")
        print("=" * 60)
        print(f"\n  PO Number:    {result.get('po_number', 'N/A')}")
        print(f"  Vendor:       {result.get('best_quote', {}).get('vendor', 'N/A')}")
        print(f"  Product:      {result.get('best_quote', {}).get('product_name', 'N/A')}")
        print(f"  Total:        €{result.get('best_quote', {}).get('total', 0):,}")
        print()


def run_second_invocation(graph):
    print("=" * 60)
    print("  SECOND INVOCATION — Manager responds")
    print("=" * 60)

    saved_state = graph.get_state(config)
    if not saved_state or not saved_state.values:
        print("\nNo saved state found! Run without --resume first.")
        return

    print("\nLoading state from checkpoint...")
    print(f"  ✓ Request: {saved_state.values.get('request', 'N/A')}")
    print(f"  ✓ Quantity: {saved_state.values.get('quantity', 'N/A')}")
    print(f"  ✓ Vendors found: {len(saved_state.values.get('vendors', []))}")
    print(f"  ✓ Quotes received: {len(saved_state.values.get('quotes', []))}")
    best = saved_state.values.get("best_quote", {})
    print(
        f"  ✓ Best quote: {best.get('vendor', 'N/A')} / {best.get('product_name', 'N/A')} "
        f"at €{best.get('total', 0):,}"
    )
    print("\n  Steps 1-3 are NOT re-executed — their output is in the checkpoint!\n")

    resume_value = "Approved — go ahead with the purchase."
    if len(sys.argv) > 2:
        resume_value = " ".join(arg for arg in sys.argv[2:] if arg != "--resume")

    print(f"Manager response: {resume_value}")
    time.sleep(1)

    result = graph.invoke(Command(resume=resume_value), config)

    print("\n" + "=" * 60)
    print("PROCUREMENT COMPLETE")
    print("=" * 60)
    print(f"\n  PO Number:    {result.get('po_number', 'N/A')}")
    print(f"  Vendor:       {result.get('best_quote', {}).get('vendor', 'N/A')}")
    print(f"  Product:      {result.get('best_quote', {}).get('product_name', 'N/A')}")
    print(f"  Total:        €{result.get('best_quote', {}).get('total', 0):,}")
    print(f"  Approval:     {result.get('approval_status', 'N/A')}")
    if result.get("rejection_reason"):
        print(f"  Rejection:    {result.get('rejection_reason')}")
    print()


if __name__ == "__main__":
    resume_mode = "--resume" in sys.argv

    if not resume_mode and os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print("(Cleaned up old checkpoint DB)")

    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    graph = builder.compile(checkpointer=checkpointer)

    try:
        if resume_mode:
            run_second_invocation(graph)
        else:
            run_first_invocation(graph)
    finally:
        conn.close()