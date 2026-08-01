from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"


def read_csv(name: str, **kwargs: object) -> pd.DataFrame:
    return pd.read_csv(RAW / name, low_memory=False, **kwargs)


def safe_pct(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    return np.where(denominator.ne(0), numerator / denominator, np.nan)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    customers = read_csv("olist_customers_dataset.csv")
    orders = read_csv("olist_orders_dataset.csv")
    items = read_csv("olist_order_items_dataset.csv")
    products = read_csv("olist_products_dataset.csv")
    sellers = read_csv("olist_sellers_dataset.csv")
    translations = read_csv("product_category_name_translation.csv")
    reviews = read_csv("olist_order_reviews_dataset.csv")
    payments = read_csv("olist_order_payments_dataset.csv")

    date_columns = [
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ]
    for column in date_columns:
        orders[column] = pd.to_datetime(orders[column], errors="coerce")

    reviews["review_answer_timestamp"] = pd.to_datetime(
        reviews["review_answer_timestamp"], errors="coerce"
    )
    reviews = (
        reviews.sort_values(["order_id", "review_answer_timestamp"])
        .drop_duplicates("order_id", keep="last")
        [["order_id", "review_score"]]
    )

    product_categories = products[["product_id", "product_category_name"]].merge(
        translations, on="product_category_name", how="left"
    )
    product_categories["category"] = product_categories[
        "product_category_name_english"
    ].fillna("unknown")

    item_detail = items.merge(
        product_categories[["product_id", "category"]], on="product_id", how="left"
    )
    item_detail["category"] = item_detail["category"].fillna("unknown")

    item_order = (
        item_detail.groupby("order_id", as_index=False)
        .agg(
            merchandise_gmv=("price", "sum"),
            freight_value=("freight_value", "sum"),
            item_count=("order_item_id", "count"),
            seller_count=("seller_id", "nunique"),
        )
    )
    payment_order = payments.groupby("order_id", as_index=False).agg(
        customer_payment=("payment_value", "sum")
    )

    order_fact = (
        orders.merge(customers, on="customer_id", how="left", validate="one_to_one")
        .merge(reviews, on="order_id", how="left", validate="one_to_one")
        .merge(item_order, on="order_id", how="left", validate="one_to_one")
        .merge(payment_order, on="order_id", how="left", validate="one_to_one")
    )
    order_fact["delivered_days"] = (
        order_fact["order_delivered_customer_date"]
        - order_fact["order_purchase_timestamp"]
    ).dt.total_seconds() / 86400
    # Compare calendar dates so delivery at any time on the promised date is on time.
    order_fact["delay_days"] = (
        order_fact["order_delivered_customer_date"].dt.normalize()
        - order_fact["order_estimated_delivery_date"].dt.normalize()
    ).dt.days
    order_fact["is_late"] = order_fact["delay_days"].gt(0)
    order_fact["low_review"] = order_fact["review_score"].le(2)
    order_fact["customer_outlay"] = (
        order_fact["merchandise_gmv"] + order_fact["freight_value"]
    )
    order_fact["freight_burden"] = safe_pct(
        order_fact["freight_value"], order_fact["customer_outlay"]
    )

    delivered = order_fact.loc[
        order_fact["order_status"].eq("delivered")
        & order_fact["order_delivered_customer_date"].notna()
        & order_fact["merchandise_gmv"].notna()
    ].copy()

    # Main KPI definitions use delivered orders only and merchandise price as GMV.
    customer_orders = delivered.groupby("customer_unique_id").agg(
        orders=("order_id", "nunique"),
        gmv=("merchandise_gmv", "sum"),
    )
    repeat_customers = customer_orders["orders"].gt(1)
    orders_from_repeat = int(
        customer_orders.loc[repeat_customers, "orders"].sum()
    )

    kpis = {
        "orders_all_statuses": int(len(order_fact)),
        "delivered_orders": int(delivered["order_id"].nunique()),
        "delivered_items": int(delivered["item_count"].sum()),
        "merchandise_gmv_brl": float(delivered["merchandise_gmv"].sum()),
        "freight_value_brl": float(delivered["freight_value"].sum()),
        "average_order_gmv_brl": float(delivered["merchandise_gmv"].mean()),
        "average_delivery_days": float(delivered["delivered_days"].mean()),
        "late_delivery_rate": float(delivered["is_late"].mean()),
        "average_review_score": float(delivered["review_score"].mean()),
        "low_review_rate": float(delivered["low_review"].mean()),
        "unique_customers": int(customer_orders.shape[0]),
        "repeat_customers": int(repeat_customers.sum()),
        "repeat_customer_rate": float(repeat_customers.mean()),
        "orders_from_repeat_customers_rate": float(
            orders_from_repeat / len(delivered)
        ),
        "review_coverage": float(delivered["review_score"].notna().mean()),
        "purchase_date_min": delivered["order_purchase_timestamp"].min().isoformat(),
        "purchase_date_max": delivered["order_purchase_timestamp"].max().isoformat(),
    }

    delay_buckets = pd.cut(
        delivered["delay_days"],
        bins=[-np.inf, 0, 3, 7, np.inf],
        labels=["On time / early", "1-3 days late", "4-7 days late", "8+ days late"],
        right=True,
    )
    delay_impact = (
        delivered.assign(delay_bucket=delay_buckets)
        .groupby("delay_bucket", observed=False)
        .agg(
            orders=("order_id", "nunique"),
            average_review=("review_score", "mean"),
            low_review_rate=("low_review", "mean"),
            average_delivery_days=("delivered_days", "mean"),
        )
        .reset_index()
    )

    monthly = delivered.assign(
        purchase_month=delivered["order_purchase_timestamp"].dt.to_period("M").astype(str)
    )
    monthly = (
        monthly.groupby("purchase_month", as_index=False)
        .agg(
            orders=("order_id", "nunique"),
            merchandise_gmv_brl=("merchandise_gmv", "sum"),
            average_order_gmv_brl=("merchandise_gmv", "mean"),
            late_delivery_rate=("is_late", "mean"),
            average_review=("review_score", "mean"),
        )
    )
    # 2016 and Sep-Oct 2018 are partial/sparse, so the main trend view uses complete months.
    monthly["complete_month"] = monthly["purchase_month"].between("2017-01", "2018-08")

    state_performance = (
        delivered.groupby("customer_state", as_index=False)
        .agg(
            orders=("order_id", "nunique"),
            merchandise_gmv_brl=("merchandise_gmv", "sum"),
            freight_value_brl=("freight_value", "sum"),
            average_review=("review_score", "mean"),
            late_delivery_rate=("is_late", "mean"),
            average_delivery_days=("delivered_days", "mean"),
        )
    )
    state_performance["freight_burden"] = safe_pct(
        state_performance["freight_value_brl"],
        state_performance["merchandise_gmv_brl"]
        + state_performance["freight_value_brl"],
    )
    state_performance["gmv_share"] = (
        state_performance["merchandise_gmv_brl"]
        / state_performance["merchandise_gmv_brl"].sum()
    )
    state_performance = state_performance.sort_values(
        "merchandise_gmv_brl", ascending=False
    )

    delivered_outcomes = delivered[
        ["order_id", "is_late", "review_score", "low_review"]
    ]
    order_category = (
        item_detail.groupby(["order_id", "category"], as_index=False)
        .agg(
            merchandise_gmv_brl=("price", "sum"),
            freight_value_brl=("freight_value", "sum"),
            items=("order_item_id", "count"),
        )
        .merge(delivered_outcomes, on="order_id", how="inner", validate="many_to_one")
    )
    category_performance = (
        order_category.groupby("category", as_index=False)
        .agg(
            orders=("order_id", "nunique"),
            merchandise_gmv_brl=("merchandise_gmv_brl", "sum"),
            freight_value_brl=("freight_value_brl", "sum"),
            average_review=("review_score", "mean"),
            late_delivery_rate=("is_late", "mean"),
            low_review_rate=("low_review", "mean"),
        )
    )
    category_performance["freight_burden"] = safe_pct(
        category_performance["freight_value_brl"],
        category_performance["merchandise_gmv_brl"]
        + category_performance["freight_value_brl"],
    )
    category_performance["gmv_share"] = (
        category_performance["merchandise_gmv_brl"]
        / category_performance["merchandise_gmv_brl"].sum()
    )
    category_performance = category_performance.sort_values(
        "merchandise_gmv_brl", ascending=False
    )

    # Seller risk is evaluated at the order-seller level. This avoids weighting a
    # seller multiple times when it supplied several items in the same order.
    # For multi-seller orders, the customer outcome is associated with every
    # participating seller; it is a prioritization signal, not sole-cause proof.
    order_seller = (
        item_detail.groupby(["order_id", "seller_id"], as_index=False)
        .agg(
            merchandise_gmv_brl=("price", "sum"),
            freight_value_brl=("freight_value", "sum"),
            items=("order_item_id", "count"),
        )
        .merge(delivered_outcomes, on="order_id", how="inner", validate="many_to_one")
        .merge(
            sellers[["seller_id", "seller_state"]],
            on="seller_id",
            how="left",
            validate="many_to_one",
        )
    )
    seller_performance = (
        order_seller.groupby(["seller_id", "seller_state"], as_index=False, dropna=False)
        .agg(
            orders=("order_id", "nunique"),
            merchandise_gmv_brl=("merchandise_gmv_brl", "sum"),
            freight_value_brl=("freight_value_brl", "sum"),
            average_review=("review_score", "mean"),
            late_delivery_rate=("is_late", "mean"),
            low_review_rate=("low_review", "mean"),
            low_review_orders=("low_review", "sum"),
        )
    )
    seller_performance["freight_burden"] = safe_pct(
        seller_performance["freight_value_brl"],
        seller_performance["merchandise_gmv_brl"]
        + seller_performance["freight_value_brl"],
    )
    seller_performance["scale_flag"] = seller_performance["orders"].ge(100)
    seller_performance["delay_risk_flag"] = seller_performance[
        "late_delivery_rate"
    ].gt(kpis["late_delivery_rate"])
    seller_performance["review_risk_flag"] = seller_performance[
        "low_review_rate"
    ].gt(kpis["low_review_rate"])
    seller_performance["priority_flag"] = (
        seller_performance["scale_flag"]
        & seller_performance["delay_risk_flag"]
        & seller_performance["review_risk_flag"]
    )
    seller_performance = seller_performance.sort_values(
        ["priority_flag", "low_review_orders", "orders"],
        ascending=[False, False, False],
    )

    payment_mix = (
        payments.merge(
            delivered[["order_id"]], on="order_id", how="inner", validate="many_to_one"
        )
        .groupby("payment_type", as_index=False)
        .agg(payment_records=("order_id", "size"), payment_value_brl=("payment_value", "sum"))
    )
    payment_mix["value_share"] = (
        payment_mix["payment_value_brl"] / payment_mix["payment_value_brl"].sum()
    )
    payment_mix = payment_mix.sort_values("payment_value_brl", ascending=False)

    # Concise, source-backed findings for the workbook/deck.
    on_time = delay_impact.loc[delay_impact["delay_bucket"].eq("On time / early")].iloc[0]
    very_late = delay_impact.loc[delay_impact["delay_bucket"].eq("8+ days late")].iloc[0]
    top_categories = category_performance.head(10)
    priority_categories = category_performance.loc[
        category_performance["orders"].ge(500)
        & category_performance["average_review"].lt(kpis["average_review_score"])
        & category_performance["merchandise_gmv_brl"].ge(
            category_performance.loc[category_performance["orders"].ge(500), "merchandise_gmv_brl"].median()
        )
    ].sort_values("merchandise_gmv_brl", ascending=False)
    high_freight_states = state_performance.loc[
        state_performance["orders"].ge(500)
    ].sort_values("freight_burden", ascending=False)
    priority_sellers = seller_performance.loc[
        seller_performance["priority_flag"]
    ].sort_values(["low_review_orders", "orders"], ascending=False)
    scaled_sellers = seller_performance.loc[seller_performance["scale_flag"]]

    findings = {
        "late_delivery_review_gap": float(
            on_time["average_review"] - very_late["average_review"]
        ),
        "very_late_low_review_multiplier": float(
            very_late["low_review_rate"] / on_time["low_review_rate"]
        ),
        "top_10_category_gmv_share": float(top_categories["gmv_share"].sum()),
        "priority_categories": priority_categories.head(8)[
            [
                "category",
                "orders",
                "merchandise_gmv_brl",
                "average_review",
                "late_delivery_rate",
            ]
        ].to_dict(orient="records"),
        "high_freight_states": high_freight_states.head(8)[
            [
                "customer_state",
                "orders",
                "freight_burden",
                "late_delivery_rate",
                "average_review",
            ]
        ].to_dict(orient="records"),
        "seller_risk": {
            "minimum_orders": 100,
            "scaled_sellers": int(len(scaled_sellers)),
            "priority_sellers": int(len(priority_sellers)),
            "priority_seller_orders": int(priority_sellers["orders"].sum()),
            "priority_seller_low_review_orders": int(
                priority_sellers["low_review_orders"].sum()
            ),
            "priority_seller_gmv_brl": float(
                priority_sellers["merchandise_gmv_brl"].sum()
            ),
        },
        "priority_sellers": priority_sellers.head(10)[
            [
                "seller_id",
                "seller_state",
                "orders",
                "merchandise_gmv_brl",
                "average_review",
                "late_delivery_rate",
                "low_review_rate",
                "low_review_orders",
            ]
        ].to_dict(orient="records"),
    }

    order_fact.to_csv(OUT / "order_fact.csv", index=False)
    delay_impact.to_csv(OUT / "delay_impact.csv", index=False)
    monthly.to_csv(OUT / "monthly_performance.csv", index=False)
    state_performance.to_csv(OUT / "state_performance.csv", index=False)
    category_performance.to_csv(OUT / "category_performance.csv", index=False)
    seller_performance.to_csv(OUT / "seller_performance.csv", index=False)
    payment_mix.to_csv(OUT / "payment_mix.csv", index=False)
    pd.DataFrame([kpis]).to_csv(OUT / "kpi_summary.csv", index=False)
    (OUT / "analysis_summary.json").write_text(
        json.dumps({"kpis": kpis, "findings": findings}, indent=2), encoding="utf-8"
    )
    workbook_payload = {
        "kpis": kpis,
        "findings": findings,
        "delay_impact": delay_impact.to_dict(orient="records"),
        "monthly_performance": monthly.to_dict(orient="records"),
        "state_performance": state_performance.to_dict(orient="records"),
        "category_performance": category_performance.to_dict(orient="records"),
        # pandas.to_json emits strict JSON nulls for missing seller metadata or
        # reviews; plain to_dict would leave NaN values that JSON.parse rejects.
        "seller_performance": json.loads(
            seller_performance.to_json(orient="records")
        ),
        "payment_mix": payment_mix.to_dict(orient="records"),
    }
    (OUT / "workbook_data.json").write_text(
        json.dumps(workbook_payload, indent=2), encoding="utf-8"
    )

    print(json.dumps({"kpis": kpis, "findings": findings}, indent=2))


if __name__ == "__main__":
    main()
