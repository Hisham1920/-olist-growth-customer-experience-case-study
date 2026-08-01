# Interview Guide

## 60-second project explanation

I wanted to build a consulting-style SQL project rather than a dashboard without a business question. I used Olist's public Brazilian marketplace dataset, which contains nine relational tables and roughly 100,000 orders. I framed the problem around how Olist could improve customer experience and support repeat growth. I created a MySQL schema, validated the data, and tested four hypotheses covering delivery delays, regional freight and service performance, category priorities, and repeat purchasing. The strongest finding was that average review score declined from 4.29 for on-time orders to 1.70 for orders delayed by eight or more days, while low-review risk became 8.4 times higher. I then built a transparent seller-risk screen: among sellers with at least 100 delivered orders, 58 exceeded both the overall delay and low-review benchmarks. I converted the findings into three recommendations: control delivery exceptions, fix regional fulfilment friction, and build a post-delivery retention loop.

## Why this is a business case, not only a SQL project

- It begins with a management question.
- Each query tests an explicit hypothesis.
- Metrics are defined before interpretation.
- Findings are translated into prioritized actions.
- Limitations and non-causal interpretation are stated clearly.

## SQL concepts used

- Multi-table joins
- Common table expressions
- Window function (`ROW_NUMBER`) for the latest review
- Conditional aggregation
- Date calculations and delay buckets
- Distinct customer and order counts
- Category and regional segmentation
- Analytical views
- Data-quality and referential-integrity checks

## Questions to prepare for

### Why did you use GMV instead of revenue?

The dataset provides item price and freight values but does not disclose Olist's commission, product cost, or operating expenses. Calling item price company revenue would therefore be inaccurate. I used merchandise GMV and excluded profitability claims.

### How did you define late delivery?

An order is late when the actual customer delivery calendar date is after the estimated delivery calendar date. Deliveries made at any time on the promised date are treated as on time.

### Why retain the latest review?

A small number of orders have multiple review records. Retaining the most recently answered review creates one outcome per order and avoids overweighting those orders.

### Does the delay analysis prove causality?

No. It shows a strong monotonic association and is useful for operational prioritization. A causal claim would require an experimental or quasi-experimental design and additional controls.

### How did you define a priority seller?

I used a transparent rule rather than an opaque weighted score: at least 100 delivered orders, a late-delivery rate above the 6.8% portfolio benchmark, and a low-review rate above the 12.7% portfolio benchmark. For multi-seller orders, the outcome is linked to every participating seller, so the screen identifies investigation targets rather than proving responsibility.

### Why might the repeat rate be understated?

The observation window is finite and customer behavior outside the dataset is unavailable. The metric is therefore an observed-window repeat rate, not lifetime retention.

### What would you do next with more data?

I would add carrier identifiers, commission and cost data, acquisition channel, customer support contacts, and controlled intervention data. That would support profitability analysis, deeper root-cause modeling and causal evaluation of recovery actions.

## Three recommendations to remember

1. **Control delivery exceptions:** pre-breach alerts, seller/carrier SLA reviews and proactive communication.
2. **Fix regional friction:** prioritize MA, CE, BA and PA and compare route and seller coverage.
3. **Build retention:** low-rating recovery, category-specific repeat tests and cohort monitoring.
