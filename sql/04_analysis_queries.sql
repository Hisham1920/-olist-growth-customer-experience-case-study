USE olist_case_study;

-- 1. Executive KPI summary. GMV is item price, not Olist company revenue.
SELECT
  COUNT(DISTINCT order_id) AS delivered_orders,
  SUM(item_count) AS delivered_items,
  ROUND(SUM(merchandise_gmv), 2) AS merchandise_gmv_brl,
  ROUND(SUM(freight_value), 2) AS freight_value_brl,
  ROUND(AVG(merchandise_gmv), 2) AS average_order_gmv_brl,
  ROUND(AVG(delivered_days), 2) AS average_delivery_days,
  ROUND(AVG(is_late) * 100, 2) AS late_delivery_rate_pct,
  ROUND(AVG(review_score), 2) AS average_review_score,
  ROUND(AVG(low_review) * 100, 2) AS low_review_rate_pct
FROM v_delivered_order_fact;

-- 2. Hypothesis 1: delivery delays reduce customer satisfaction.
WITH delay_segment AS (
  SELECT
    order_id,
    review_score,
    low_review,
    delivered_days,
    CASE
      WHEN delay_days <= 0 THEN 'On time / early'
      WHEN delay_days <= 3 THEN '1-3 days late'
      WHEN delay_days <= 7 THEN '4-7 days late'
      ELSE '8+ days late'
    END AS delay_bucket,
    CASE
      WHEN delay_days <= 0 THEN 1
      WHEN delay_days <= 3 THEN 2
      WHEN delay_days <= 7 THEN 3
      ELSE 4
    END AS bucket_order
  FROM v_delivered_order_fact
)
SELECT
  delay_bucket,
  COUNT(*) AS orders,
  ROUND(AVG(review_score), 2) AS average_review,
  ROUND(AVG(low_review) * 100, 2) AS low_review_rate_pct,
  ROUND(AVG(delivered_days), 2) AS average_delivery_days
FROM delay_segment
GROUP BY delay_bucket, bucket_order
ORDER BY bucket_order;

-- 3. Hypothesis 2: certain states combine high freight burden with poor service.
SELECT
  customer_state,
  COUNT(*) AS orders,
  ROUND(SUM(merchandise_gmv), 2) AS merchandise_gmv_brl,
  ROUND(
    SUM(freight_value) / NULLIF(SUM(merchandise_gmv + freight_value), 0) * 100,
    2
  ) AS freight_burden_pct,
  ROUND(AVG(is_late) * 100, 2) AS late_delivery_rate_pct,
  ROUND(AVG(review_score), 2) AS average_review
FROM v_delivered_order_fact
GROUP BY customer_state
HAVING COUNT(*) >= 500
ORDER BY freight_burden_pct DESC;

-- 4. Hypothesis 3: high-GMV categories with weak experience need priority action.
WITH order_category AS (
  SELECT
    i.order_id,
    COALESCE(t.product_category_name_english, 'unknown') AS category,
    SUM(i.price) AS merchandise_gmv,
    SUM(i.freight_value) AS freight_value
  FROM order_items i
  LEFT JOIN products p ON p.product_id = i.product_id
  LEFT JOIN category_translation t
    ON t.product_category_name = p.product_category_name
  GROUP BY i.order_id, COALESCE(t.product_category_name_english, 'unknown')
)
SELECT
  oc.category,
  COUNT(DISTINCT oc.order_id) AS orders,
  ROUND(SUM(oc.merchandise_gmv), 2) AS merchandise_gmv_brl,
  ROUND(AVG(f.review_score), 2) AS average_review,
  ROUND(AVG(f.is_late) * 100, 2) AS late_delivery_rate_pct,
  ROUND(AVG(f.low_review) * 100, 2) AS low_review_rate_pct,
  ROUND(
    SUM(oc.freight_value)
    / NULLIF(SUM(oc.merchandise_gmv + oc.freight_value), 0) * 100,
    2
  ) AS freight_burden_pct
FROM order_category oc
JOIN v_delivered_order_fact f ON f.order_id = oc.order_id
GROUP BY oc.category
HAVING COUNT(DISTINCT oc.order_id) >= 500
ORDER BY merchandise_gmv_brl DESC;

-- 5. Hypothesis 4: repeat purchase is limited within the observation window.
WITH customer_orders AS (
  SELECT customer_unique_id, COUNT(*) AS order_count
  FROM v_delivered_order_fact
  GROUP BY customer_unique_id
)
SELECT
  COUNT(*) AS unique_customers,
  SUM(order_count > 1) AS repeat_customers,
  ROUND(AVG(order_count > 1) * 100, 2) AS repeat_customer_rate_pct,
  ROUND(
    SUM(CASE WHEN order_count > 1 THEN order_count ELSE 0 END)
    / SUM(order_count) * 100,
    2
  ) AS orders_from_repeat_customers_pct
FROM customer_orders;

-- 6. Monthly GMV and service trend. Use Jan 2017-Aug 2018 as complete months.
SELECT
  DATE_FORMAT(order_purchase_timestamp, '%Y-%m') AS purchase_month,
  COUNT(*) AS orders,
  ROUND(SUM(merchandise_gmv), 2) AS merchandise_gmv_brl,
  ROUND(AVG(merchandise_gmv), 2) AS average_order_gmv_brl,
  ROUND(AVG(is_late) * 100, 2) AS late_delivery_rate_pct,
  ROUND(AVG(review_score), 2) AS average_review
FROM v_delivered_order_fact
WHERE order_purchase_timestamp >= '2017-01-01'
  AND order_purchase_timestamp < '2018-09-01'
GROUP BY DATE_FORMAT(order_purchase_timestamp, '%Y-%m')
ORDER BY purchase_month;

-- 7. Payment mix by customer payment value.
SELECT
  p.payment_type,
  COUNT(*) AS payment_records,
  ROUND(SUM(p.payment_value), 2) AS payment_value_brl,
  ROUND(
    SUM(p.payment_value) / SUM(SUM(p.payment_value)) OVER () * 100,
    2
  ) AS value_share_pct
FROM order_payments p
JOIN v_delivered_order_fact f ON f.order_id = p.order_id
GROUP BY p.payment_type
ORDER BY payment_value_brl DESC;

-- 8. Operational-risk matrix: scaled sellers with above-average delay and
-- low-review rates. The customer outcome is associated with each seller in a
-- multi-seller order, so this prioritizes investigation rather than assigning
-- sole responsibility.
WITH order_seller AS (
  SELECT
    i.order_id,
    i.seller_id,
    SUM(i.price) AS merchandise_gmv,
    SUM(i.freight_value) AS freight_value
  FROM order_items i
  GROUP BY i.order_id, i.seller_id
),
seller_performance AS (
  SELECT
    os.seller_id,
    s.seller_state,
    COUNT(DISTINCT os.order_id) AS orders,
    SUM(os.merchandise_gmv) AS merchandise_gmv,
    AVG(f.review_score) AS average_review,
    AVG(f.is_late) AS late_delivery_rate,
    AVG(f.low_review) AS low_review_rate,
    SUM(f.low_review) AS low_review_orders
  FROM order_seller os
  JOIN v_delivered_order_fact f ON f.order_id = os.order_id
  LEFT JOIN sellers s ON s.seller_id = os.seller_id
  GROUP BY os.seller_id, s.seller_state
),
benchmarks AS (
  SELECT
    AVG(is_late) AS overall_late_rate,
    AVG(low_review) AS overall_low_review_rate
  FROM v_delivered_order_fact
)
SELECT
  sp.seller_id,
  sp.seller_state,
  sp.orders,
  ROUND(sp.merchandise_gmv, 2) AS merchandise_gmv_brl,
  ROUND(sp.average_review, 2) AS average_review,
  ROUND(sp.late_delivery_rate * 100, 2) AS late_delivery_rate_pct,
  ROUND(sp.low_review_rate * 100, 2) AS low_review_rate_pct,
  sp.low_review_orders
FROM seller_performance sp
CROSS JOIN benchmarks b
WHERE sp.orders >= 100
  AND sp.late_delivery_rate > b.overall_late_rate
  AND sp.low_review_rate > b.overall_low_review_rate
ORDER BY sp.low_review_orders DESC, sp.orders DESC;
