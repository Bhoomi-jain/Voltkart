# VoltKart evaluation ground truth

Correct answers for all 20 required evaluation questions, computed from `sample_bundle/` and the supplied document versions. Use this file to check exported chat answers; the app itself must still compute answers and cite live sources at runtime.

Conventions:

- Revenue, spend and units use `Delivered` orders unless the question says otherwise.
- Line amount = `quantity × unit_price_inr × (1 - discount_pct / 100)`.
- Money is in INR, rounded to 2 decimals. Dates are ISO `YYYY-MM-DD`.
- When document versions conflict, the newest version wins. If a fact appears only in an older version, that date is named explicitly.
- Q17–Q18 include expected web-search answers even though the web-search bonus was not implemented.

## A. Tables (Chat 1)

### Q1. Which store had the highest revenue in 2025, and who manages it?

**Answer:** VoltKart Connaught Place (`S04`), managed by **Vikram Sethi**, with **INR 5,839,148.75** in 2025 revenue.

**Basis:** `orders.csv` joined to `order_items.csv` and `stores.csv`; filter `order_status == "Delivered"` and `order_date` in 2025; sum line amounts by store and manager.

### Q2. Who were the top 3 customers by spend at that store in 2025? (follow-up; must use memory)

**Answer:** At VoltKart Connaught Place (`S04`) in 2025:

1. **Aarav Kulkarni** (`C0118`) — INR 815,723.40
2. **Ishaan Sharma** (`C0112`) — INR 609,659.80
3. **Varun Mishra** (`C0052`) — INR 437,761.95

**Basis:** Resolve “that store” to Q1’s `S04`; join `customers.csv`, `orders.csv` and `order_items.csv`; Delivered orders only, 2025 only, sum line amounts by customer.

### Q3. Which product was returned most often, and what is its most common return reason?

**Answer:** **Nexora X12 Pro** was returned most often, **9 times**. Its most common return reason was **“Not as described”**, **4 times**.

**Basis:** `returns.csv` joined through `order_item_id` to `order_items.csv`, then `products.csv`; count returns by product and by reason for that product.

### Q4. How many Platinum customers whose home city is Bengaluru bought a laptop in Q1 2026? Name them.

**Answer:** **1 customer: Kabir Kapoor** (`C0037`).

**Basis:** `customers.csv` joined through `orders.csv` and `order_items.csv` to `products.csv`; filter `loyalty_tier == "Platinum"`, `home_city == "Bengaluru"`, `category == "Laptops"`, `order_date` from 2026-01-01 to 2026-03-31, and `order_status == "Delivered"`. Cancelled orders are not counted as purchases.

### Q5. What is the total refund amount by region?

**Answer:**

| Region | Total refund amount |
|---|---:|
| South | INR 916,002.70 |
| West | INR 569,024.40 |
| East | INR 329,242.20 |
| North | INR 141,624.95 |

All regions total **INR 1,955,894.25**.

**Basis:** `returns.csv` joined to `order_items.csv`, `orders.csv` and `stores.csv`; sum `refund_amount_inr` by the store’s region.

## B. Documents (Chat 2)

### Q6. What is the return window for Gold members?

**Answer:** Gold members have a **30-day** return window from delivery under `VoltKart_Return_Policy_2025-09-01.txt`. Smartphones are an exception: they must be returned within **7 days** for all tiers.

**Basis:** 2025-09-01 policy, section 1. Supersedes the 20-day window in 2025-01-15 and the 15-day window in 2024-04-01.

### Q7. How many business days does a refund take?

**Answer:** Approved refunds take **5 business days**.

**Basis:** 2025-09-01 policy, section 3. Supersedes 7 business days (2025-01-15) and 10 business days (2024-04-01).

### Q8. How soon must a customer report a product damaged on delivery?

**Answer:** Within **48 hours of delivery**, with photographs of the product and packaging. Reports after 48 hours are handled as standard returns.

**Basis:** `VoltKart_Return_Policy_2024-04-01.pdf`, section 4. This fact appears only in the older 2024-04-01 version; the later policies omit the damaged-on-delivery reporting rule.

### Q9. Are opened earbuds returnable?

**Answer:** **No.** Opened earbuds are not eligible for return.

**Basis:** `VoltKart_Return_Policy_2025-01-15.docx`, section 5. The newer 2025-09-01 policy omits the non-returnable-items list, so the answer must identify the 2025-01-15 version rather than attribute the rule to the newest policy.

### Q10. What is the location, work mode and salary range for the Machine Learning Engineer role?

**Answer:** The current role is in **Bengaluru or Hyderabad**, is **hybrid with 3 days per week in the office**, and pays **INR 16 to 24 LPA**.

**Basis:** `JD_ML_Engineer_2025-10-20.pdf`, Key Details. The older 2025-03-10 version says Bengaluru on-site 5 days/week and INR 12–18 LPA, but it is superseded.

### Q11. Who does the Machine Learning Engineer report to?

**Answer:** **Ananya Rao, Head of Data Science.**

**Basis:** `JD_ML_Engineer_2025-03-10.docx`, Key Details. The newer 2025-10-20 version does not state a reporting line, so the older version and its date must be named.

### Q12. How much does VoltCare cost, and is there a limit on the number of claims?

**Answer:** Under the current `VoltKart_Warranty_Terms_2026-02-01.docx`, VoltCare costs **10% of invoice value for 1 year** or **18% for 2 years**. The current version states **no limit on the number of claims**; it only says claims can be raised in the app or at a store. The superseded 2024-07-01 version allowed a maximum of **2 claims per product per year** at 8% of invoice value.

**Basis:** 2026-02-01 Price and Claims sections; older 2024-07-01 Price and Claims sections for the historical limit.

## C. Tables and documents together (Chat 2)

### Q13. Kavya Kapoor wants to return the phone from order O00174, 12 days after delivery. Is that allowed, and would a restocking fee apply if it were within the window?

**Answer:** **Not allowed.** The phone in `O00174` is the **Nexora X12 Pro** (`Smartphones`), with an invoice line amount of **INR 49,636.55**. The current 2025-09-01 policy allows only **7 days** for smartphone returns for every tier, so 12 days after delivery is outside the window. If it were within the window and opened for a non-defect reason, the 10% restocking fee would normally be **INR 4,963.66**, but Kavya Kapoor is **Platinum**, so the fee is **waived** and no restocking fee applies.

**Basis:** `orders.csv`, `order_items.csv`, `products.csv` and `customers.csv` for the order, phone line and loyalty tier; `VoltKart_Return_Policy_2025-09-01.txt` sections 1–2 for the 7-day smartphone rule, 10% fee and Platinum waiver.

### Q14. The store operations notice says one store was closed in December 2025. Does the order data agree with that?

**Answer:** **No, not for physical store activity.** The notice says VoltKart Andheri (`S03`) was closed for renovation from 2025-12-01 to 2025-12-31, but the order data contains **3 in-store orders** at `S03` in December 2025, totaling **INR 94,094.55** in line amounts:

| Order | Date | Item | Line amount |
|---|---|---|---:|
| O00351 | 2025-12-07 | Zephyr FitBand 5 | INR 3,324.00 |
| O00663 | 2025-12-17 | Orbitron Swift 15 | INR 44,221.55 |
| O00485 | 2025-12-24 | Orbitron Swift 15 | INR 46,549.00 |

There are also 6 online orders with `store_id = S03` that month; those are consistent with the notice’s instruction to use the online channel and do not prove the physical store was open.

**Basis:** `VoltKart_Store_Operations_Notice_2025-11-05.pdf`, Store-Specific Changes; `orders.csv` and `order_items.csv` filtered to `S03`, December 2025 and `channel == "In-store"`.

## D. Charts (Chat 1, bonus)

### Q15. Show a bar chart of total revenue by product category for 2025.

**Answer:** Bar values, descending:

| Category | Revenue |
|---|---:|
| Laptops | INR 11,152,212.55 |
| Smartphones | INR 10,477,358.05 |
| Televisions | INR 3,211,720.10 |
| Audio | INR 2,941,398.10 |
| Wearables | INR 1,771,286.65 |
| Accessories | INR 504,780.40 |

`labels = ["Laptops", "Smartphones", "Televisions", "Audio", "Wearables", "Accessories"]`  
`values = [11152212.55, 10477358.05, 3211720.10, 2941398.10, 1771286.65, 504780.40]`

**Basis:** Delivered line items in 2025 grouped by `products.category`; sum line amounts.

### Q16. Show a line chart of smartphone units sold per month in 2025.

**Answer:** Monthly quantities, chronological:

| Month | Units |
|---|---:|
| 2025-01 | 16 |
| 2025-02 | 23 |
| 2025-03 | 19 |
| 2025-04 | 16 |
| 2025-05 | 23 |
| 2025-06 | 16 |
| 2025-07 | 19 |
| 2025-08 | 20 |
| 2025-09 | 23 |
| 2025-10 | 18 |
| 2025-11 | 21 |
| 2025-12 | 20 |

`labels = ["2025-01", "2025-02", "2025-03", "2025-04", "2025-05", "2025-06", "2025-07", "2025-08", "2025-09", "2025-10", "2025-11", "2025-12"]`  
`values = [16, 23, 19, 16, 23, 16, 19, 20, 23, 18, 21, 20]`

**Basis:** Delivered 2025 line items where `category == "Smartphones"`; sum `quantity` by month.

## E. Web search (Chat 3, bonus)

### Q17. With web search off: What is Amazon India's return window for smartphones?

**Answer:** **I could not find that in the provided files.** The uploaded VoltKart documents do not state Amazon India’s return policy. With web search off, the app must not guess and must not show a web citation.

**Basis:** No Amazon source is present in `sample_bundle/`; this is the expected grounded-refusal behavior.

### Q18. Turn web search on and ask the same question, then: How does that compare with VoltKart's smartphone return window?

**Answer:** Amazon India generally lists **10 days** for new or certified refurbished mobiles/smartphones, with the exact window shown on the product page and some categories using 7/10-day replacement policies. VoltKart’s current 2025-09-01 policy gives **7 days** for smartphones for all membership tiers, so Amazon India’s common smartphone window is **3 days longer**.

**Basis / expected web citation:** “Amazon.in Returns Policy,” Amazon India, <https://www.amazon.in/gp/help/customer/display.html?language=en_IN&nodeId=202111910>; VoltKart_Return_Policy_2025-09-01.txt section 1. This is an expected answer for the unimplemented web-search bonus.

## F. Multiple chats and persistence

### Q19. Switch from Chat 2 back to Chat 1 and ask: Show the result of my first question as a bar chart of the top 5 stores.

**Answer:** Bar values for 2025 revenue, descending:

| Store | Revenue |
|---|---:|
| VoltKart Connaught Place | INR 5,839,148.75 |
| VoltKart Hitech City | INR 4,901,100.90 |
| VoltKart Salt Lake | INR 4,800,883.05 |
| VoltKart Andheri | INR 4,343,333.95 |
| VoltKart Anna Nagar | INR 3,724,744.55 |

`labels = ["VoltKart Connaught Place", "VoltKart Hitech City", "VoltKart Salt Lake", "VoltKart Andheri", "VoltKart Anna Nagar"]`  
`values = [5839148.75, 4901100.90, 4800883.05, 4343333.95, 3724744.55]`

**Basis:** “my first question” resolves to Q1 through Chat 1 memory; the chart uses the same Delivered 2025 revenue calculation, limited to the top 5 stores.

### Q20. Restart the backend, reopen Chat 2, and ask: Summarize what we discussed so far.

**Answer:** Chat 2 covered VoltKart’s dated policies and one mixed table/document check. Gold members have a 30-day return window, with a 7-day smartphone exception, and refunds take 5 business days. Damage on delivery must be reported within 48 hours under the 2024-04-01 policy, and opened earbuds are non-returnable under the 2025-01-15 policy. The newest ML Engineer role is in Bengaluru or Hyderabad, hybrid 3 days per week, INR 16–24 LPA; Ananya Rao is named as the reporting manager only in the older 2025-03-10 version. Current VoltCare costs 10% for 1 year or 18% for 2 years with no newer claim cap. Kavya Kapoor’s 12-day smartphone return is outside the 7-day window, but her Platinum status waives the restocking fee. Finally, the S03 Andheri December 2025 closure notice conflicts with three in-store orders in the order data.

**Basis:** This summary is derived from the persisted Chat 2 answers Q6–Q14; it must remain available after a backend restart.
