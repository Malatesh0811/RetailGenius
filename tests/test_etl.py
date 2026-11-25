import pandas as pd

from retailgenius.etl import transform


def test_transform_snake_cases_columns_and_sets_types():
    raw = pd.DataFrame({
        "Order ID": [1], "Order Date": ["2012-01-10"], "Ship Date": ["2012-01-12"],
        "Product Sub-Category": ["Paper"], "Order Quantity": [3.0],
        "Sales": ["9.5"], "Profit": [1], "Discount": [0], "Unit Price": [3],
        "Shipping Cost": [1], "Product Base Margin": [None],
    })
    out = transform(raw)
    assert "product_sub_category" in out.columns and "order_date" in out.columns
    assert str(out["order_date"].dtype).startswith("datetime64")
    assert out["order_quantity"].dtype == "int64"
    assert out["sales"].dtype == "float64" and out["sales"].item() == 9.5
    assert list(raw.columns)[0] == "Order ID"   # input is not modified
