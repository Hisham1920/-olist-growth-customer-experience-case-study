USE olist_case_study;

-- Expected source row counts. Review these before analysis.
SELECT 'customers' AS table_name, COUNT(*) AS rows_loaded FROM customers
UNION ALL SELECT 'geolocation', COUNT(*) FROM geolocation
UNION ALL SELECT 'order_items', COUNT(*) FROM order_items
UNION ALL SELECT 'order_payments', COUNT(*) FROM order_payments
UNION ALL SELECT 'order_reviews', COUNT(*) FROM order_reviews
UNION ALL SELECT 'orders', COUNT(*) FROM orders
UNION ALL SELECT 'products', COUNT(*) FROM products
UNION ALL SELECT 'sellers', COUNT(*) FROM sellers
UNION ALL SELECT 'category_translation', COUNT(*) FROM category_translation;

-- Key integrity checks should return zero.
SELECT COUNT(*) AS items_without_orders
FROM order_items i LEFT JOIN orders o ON o.order_id = i.order_id
WHERE o.order_id IS NULL;

SELECT COUNT(*) AS orders_without_customers
FROM orders o LEFT JOIN customers c ON c.customer_id = o.customer_id
WHERE c.customer_id IS NULL;

SELECT COUNT(*) AS invalid_review_scores
FROM order_reviews
WHERE review_score NOT BETWEEN 1 AND 5;

CREATE OR REPLACE VIEW v_latest_review AS
SELECT order_id, review_score
FROM (
  SELECT
    order_id,
    review_score,
    ROW_NUMBER() OVER (
      PARTITION BY order_id
      ORDER BY review_answer_timestamp DESC, review_id DESC
    ) AS row_num
  FROM order_reviews
) ranked
WHERE row_num = 1;

CREATE OR REPLACE VIEW v_item_order AS
SELECT
  order_id,
  SUM(price) AS merchandise_gmv,
  SUM(freight_value) AS freight_value,
  COUNT(*) AS item_count,
  COUNT(DISTINCT seller_id) AS seller_count
FROM order_items
GROUP BY order_id;

CREATE OR REPLACE VIEW v_payment_order AS
SELECT order_id, SUM(payment_value) AS customer_payment
FROM order_payments
GROUP BY order_id;

CREATE OR REPLACE VIEW v_order_fact AS
SELECT
  o.order_id,
  o.customer_id,
  c.customer_unique_id,
  c.customer_city,
  c.customer_state,
  o.order_status,
  o.order_purchase_timestamp,
  o.order_delivered_customer_date,
  o.order_estimated_delivery_date,
  io.merchandise_gmv,
  io.freight_value,
  io.item_count,
  io.seller_count,
  po.customer_payment,
  lr.review_score,
  TIMESTAMPDIFF(
    HOUR, o.order_purchase_timestamp, o.order_delivered_customer_date
  ) / 24.0 AS delivered_days,
  DATEDIFF(
    DATE(o.order_delivered_customer_date),
    DATE(o.order_estimated_delivery_date)
  ) AS delay_days,
  CASE
    WHEN DATE(o.order_delivered_customer_date) > DATE(o.order_estimated_delivery_date)
      THEN 1 ELSE 0
  END AS is_late,
  CASE WHEN lr.review_score <= 2 THEN 1 ELSE 0 END AS low_review
FROM orders o
JOIN customers c ON c.customer_id = o.customer_id
LEFT JOIN v_item_order io ON io.order_id = o.order_id
LEFT JOIN v_payment_order po ON po.order_id = o.order_id
LEFT JOIN v_latest_review lr ON lr.order_id = o.order_id;

CREATE OR REPLACE VIEW v_delivered_order_fact AS
SELECT *
FROM v_order_fact
WHERE order_status = 'delivered'
  AND order_delivered_customer_date IS NOT NULL
  AND merchandise_gmv IS NOT NULL;

