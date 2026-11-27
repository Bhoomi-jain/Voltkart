"""Independent pandas answers for the table questions. Use this to CHECK the LLM's answers.
Run from project root:  python tests/ground_truth.py"""
import pandas as pd
T = "sample_bundle/tables/"
st, cu, pr = (pd.read_csv(T+f"{n}.csv") for n in ("stores", "customers", "products"))
od, oi, rt = (pd.read_csv(T+f"{n}.csv") for n in ("orders", "order_items", "returns"))
oi["line"] = oi.quantity * oi.unit_price_inr * (1 - oi.discount_pct / 100)
d = oi.merge(od, on="order_id").merge(pr, on="product_id").merge(cu, on="customer_id").merge(st, on="store_id")
d["order_date"] = pd.to_datetime(d.order_date)
dl = d[d.order_status == "Delivered"]

print("Q1 revenue by store 2025 (top 3)")
r1 = dl[dl.order_date.dt.year == 2025].groupby(["store_id", "store_name", "store_manager"]).line.sum().sort_values(ascending=False)
print(r1.head(3).round(2))
top = r1.index[0][0]

print("\nQ2 top 3 customers at that store 2025")
print(dl[(dl.store_id == top) & (dl.order_date.dt.year == 2025)].groupby(["customer_id", "full_name"]).line.sum().sort_values(ascending=False).head(3).round(2))

print("\nQ3 most returned product")
rr = rt.merge(oi, on="order_item_id").merge(pr, on="product_id")
print(rr.product_name.value_counts().head(3))
p = rr.product_name.value_counts().index[0]
print(rr[rr.product_name == p].return_reason.value_counts())

print("\nQ4 Platinum + Bengaluru + Laptops + Q1 2026 (delivered only)")
f = (d.loyalty_tier == "Platinum") & (d.home_city == "Bengaluru") & (d.category == "Laptops") & (d.order_date >= "2026-01-01") & (d.order_date < "2026-04-01")
print(sorted(d[f & (d.order_status == "Delivered")].full_name.unique()))
print("  (incl. cancelled):", sorted(d[f].full_name.unique()))

print("\nQ5 refund by region (region of the store where order was placed)")
print(rt.merge(oi, on="order_item_id").merge(od, on="order_id").merge(st, on="store_id").groupby("region").refund_amount_inr.sum().round(2))

print("\nQ13 order O00174")
print(d[d.order_id == "O00174"][["order_id", "full_name", "loyalty_tier", "product_name", "category", "line", "order_date", "order_status"]].to_string())

print("\nQ14 S03 (Andheri) orders per month, Oct 2025 - Feb 2026")
s = od[od.store_id == "S03"].copy(); s["m"] = s.order_date.str[:7]
print(s[(s.m >= "2025-10") & (s.m <= "2026-02")].groupby(["m", "channel"]).size().unstack(fill_value=0))

print("\nQ15 revenue by category 2025")
print(dl[dl.order_date.dt.year == 2025].groupby("category").line.sum().sort_values(ascending=False).round(2))

print("\nQ16 smartphone units per month 2025")
print(dl[(dl.category == "Smartphones") & (dl.order_date.dt.year == 2025)].groupby(dl.order_date.dt.strftime("%Y-%m")).quantity.sum())

