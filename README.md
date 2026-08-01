# Olist Growth & Customer Experience Case Study

An end-to-end SQL business case built from Olist's public Brazilian e-commerce dataset. The project answers a consulting-style question:

> How can Olist improve customer experience and support repeat growth using operational data?

The work combines a nine-table relational model, data-quality checks, hypothesis-led SQL analysis, an auditable Excel workbook, and an eight-slide recommendation deck.

## Executive answer

Delivery reliability is the clearest observed customer-experience lever. Average review score falls from **4.29/5 for on-time orders to 1.70/5 for orders delayed by 8+ days**, while the risk of a 1-2 rating becomes **8.4x higher**. A transparent operational-risk screen flags **58 of 210 scaled sellers** above both the overall delay and low-review benchmarks. Regional and category analysis then identifies where intervention should begin, while a **3.0% observed repeat-customer rate** highlights a longer-term retention opportunity.

## Dataset and scope

- Source: [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)
- Source tables: 9
- Total orders: 99,441
- Delivered orders used in the analytical base: 96,470
- Delivered items: 110,189
- Observation window: September 2016-August 2018
- Main monthly trend: January 2017-August 2018 to exclude partial months

Monetary values are in Brazilian real. **Merchandise GMV** means the sum of item prices; it is not Olist company revenue or profit because the dataset does not disclose commissions, cost or margin.

## Hypotheses

1. Delivery delays are associated with materially weaker customer reviews.
2. Some states experience both higher freight burden and poorer delivery outcomes.
3. High-GMV categories with below-average satisfaction are priority intervention areas.
4. Repeat purchase is limited within the available observation window.

## Key findings

| Finding | Evidence | Implication |
|---|---:|---|
| Delivery reliability | Review falls from 4.29 on-time to 1.70 at 8+ days late | Control exceptions before promised dates are breached |
| Late-order dissatisfaction | Low-review risk is 8.4x higher at 8+ days late | Prioritize seller/carrier SLA management and proactive communication |
| Regional friction | MA: 20.8% freight burden, 17.4% late rate, 3.83 review | Diagnose routes, seller coverage and fulfilment capacity |
| Category concentration | Top 10 categories represent 62.4% of merchandise GMV | Focus service improvements where scale and rating gaps overlap |
| Seller operational risk | 58 of 210 scaled sellers exceed both delay and low-review benchmarks | Start SLA investigation with the highest-volume flagged sellers |
| Retention gap | 3.0% of observed customers repeat | Add post-delivery recovery and category-based repeat tests |

These are observational relationships. They support prioritization but do not prove causality.

## Recommended actions

1. **Control delivery exceptions:** alert teams before promised dates are missed, review seller/carrier SLAs, and trigger proactive customer communication.
2. **Fix regional friction:** prioritize MA, CE, BA and PA diagnostics and track freight burden alongside service levels.
3. **Build the retention loop:** recover low-rating customers, test category-specific repeat offers, and monitor repeat cohorts with satisfaction.

## Repository structure

```text
analysis/
  audit_data.py                 # Row counts, columns, duplicates and null audit
  build_analysis.py             # Reproducible analytical pipeline
data/
  processed/                    # Compact analytical outputs
  raw/                          # Place the nine downloaded CSV files here
sql/
  01_create_schema.sql
  02_load_data_template.sql
  03_quality_checks_and_views.sql
  04_analysis_queries.sql
output/
  Olist_Case_Study_Analysis.xlsx
  Olist_Growth_Customer_Experience_Case_Study.pptx
INTERVIEW_GUIDE.md
RESUME_BULLETS.txt
```

## Run the Python analysis

1. Download the dataset and place all nine CSV files inside `data/raw/`.
2. Install Python 3.10+ and the packages in `requirements.txt`.
3. Run:

```bash
python analysis/audit_data.py
python analysis/build_analysis.py
```

The processed tables and summary JSON will be written to `data/processed/`.

## Run the SQL analysis in MySQL Workbench

1. Use MySQL 8.0+ and enable `LOCAL INFILE` for the connection.
2. Run `sql/01_create_schema.sql`.
3. Open `sql/02_load_data_template.sql` and replace `C:/olist-data/` with the folder containing your CSV files.
4. Run `sql/02_load_data_template.sql`.
5. Run `sql/03_quality_checks_and_views.sql` and confirm the row counts and integrity checks.
6. Run `sql/04_analysis_queries.sql` to reproduce the business outputs.

## Interview caveats

- Profitability was not estimated because commission, product cost and operating expense data are unavailable.
- A customer can appear under different `customer_id` values, so retention uses `customer_unique_id`.
- Multi-category orders can appear in more than one category-level row.
- Customer outcomes are associated with every seller in a multi-seller order, so the seller screen prioritizes investigation rather than assigning sole responsibility.
- Repeat rate is bounded by the available observation window.
- Review analysis retains the most recently answered review per order.
