-- Olist Growth & Customer Experience Case Study
-- MySQL 8.0+

DROP DATABASE IF EXISTS olist_case_study;
CREATE DATABASE olist_case_study
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
USE olist_case_study;

CREATE TABLE customers (
  customer_id CHAR(32) PRIMARY KEY,
  customer_unique_id CHAR(32) NOT NULL,
  customer_zip_code_prefix INT,
  customer_city VARCHAR(100),
  customer_state CHAR(2),
  INDEX idx_customers_unique (customer_unique_id),
  INDEX idx_customers_state (customer_state)
);

CREATE TABLE geolocation (
  geolocation_zip_code_prefix INT,
  geolocation_lat DECIMAL(10, 7),
  geolocation_lng DECIMAL(10, 7),
  geolocation_city VARCHAR(100),
  geolocation_state CHAR(2),
  INDEX idx_geolocation_zip (geolocation_zip_code_prefix)
);

CREATE TABLE order_items (
  order_id CHAR(32) NOT NULL,
  order_item_id INT NOT NULL,
  product_id CHAR(32) NOT NULL,
  seller_id CHAR(32) NOT NULL,
  shipping_limit_date DATETIME,
  price DECIMAL(12, 2),
  freight_value DECIMAL(12, 2),
  PRIMARY KEY (order_id, order_item_id),
  INDEX idx_items_product (product_id),
  INDEX idx_items_seller (seller_id)
);

CREATE TABLE order_payments (
  order_id CHAR(32) NOT NULL,
  payment_sequential INT NOT NULL,
  payment_type VARCHAR(30),
  payment_installments INT,
  payment_value DECIMAL(12, 2),
  PRIMARY KEY (order_id, payment_sequential),
  INDEX idx_payments_type (payment_type)
);

CREATE TABLE order_reviews (
  review_id CHAR(32) NOT NULL,
  order_id CHAR(32) NOT NULL,
  review_score TINYINT,
  review_comment_title TEXT,
  review_comment_message TEXT,
  review_creation_date DATETIME,
  review_answer_timestamp DATETIME,
  INDEX idx_reviews_order (order_id),
  INDEX idx_reviews_score (review_score)
);

CREATE TABLE orders (
  order_id CHAR(32) PRIMARY KEY,
  customer_id CHAR(32) NOT NULL,
  order_status VARCHAR(30),
  order_purchase_timestamp DATETIME,
  order_approved_at DATETIME,
  order_delivered_carrier_date DATETIME,
  order_delivered_customer_date DATETIME,
  order_estimated_delivery_date DATETIME,
  INDEX idx_orders_customer (customer_id),
  INDEX idx_orders_purchase_date (order_purchase_timestamp),
  INDEX idx_orders_status (order_status)
);

CREATE TABLE products (
  product_id CHAR(32) PRIMARY KEY,
  product_category_name VARCHAR(100),
  product_name_length INT,
  product_description_length INT,
  product_photos_qty INT,
  product_weight_g DECIMAL(12, 2),
  product_length_cm DECIMAL(12, 2),
  product_height_cm DECIMAL(12, 2),
  product_width_cm DECIMAL(12, 2),
  INDEX idx_products_category (product_category_name)
);

CREATE TABLE sellers (
  seller_id CHAR(32) PRIMARY KEY,
  seller_zip_code_prefix INT,
  seller_city VARCHAR(100),
  seller_state CHAR(2),
  INDEX idx_sellers_state (seller_state)
);

CREATE TABLE category_translation (
  product_category_name VARCHAR(100) PRIMARY KEY,
  product_category_name_english VARCHAR(100)
);

