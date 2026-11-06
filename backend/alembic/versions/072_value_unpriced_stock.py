"""Give a value to stock movements recorded at ₹0 where a cost is known.

- Finished goods from production output went into stock at ₹0 (the cost
  field was never filled in): value them at the product's cost price, which
  production keeps at the lot's actual cost per piece.
- Some stock issued out at ₹0 because its warehouse had no priced receipt:
  value them at the product's average priced receipt cost, else its cost
  price, so the stock left behind isn't overstated.

Receipts that genuinely came in without a rate (GRN / receipt price ₹0) are
left alone — the Stock Balance page marks them "No rate".

Revision ID: 072_value_unpriced_stock
Revises: 071_cost_basis
"""
from alembic import op

revision = "072_value_unpriced_stock"
down_revision = "071_cost_basis"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        UPDATE inventory_transactions t
        SET unit_cost = p.cost_price, total_cost = t.quantity * p.cost_price
        FROM products p
        WHERE p.id = t.product_id
          AND t.reference_type = 'production_output' AND t.direction = 1
          AND COALESCE(t.unit_cost, 0) = 0 AND COALESCE(p.cost_price, 0) > 0
    """)
    op.execute("""
        UPDATE production_outputs o
        SET unit_cost = t.unit_cost, total_cost = ROUND(o.quantity * t.unit_cost, 2)
        FROM inventory_transactions t
        WHERE t.id = o.inv_transaction_id AND COALESCE(o.unit_cost, 0) = 0 AND t.unit_cost > 0
    """)
    op.execute("""
        WITH avg_cost AS (
            SELECT product_id, SUM(quantity * unit_cost) / NULLIF(SUM(quantity), 0) AS cost
            FROM inventory_transactions
            WHERE direction = 1 AND unit_cost > 0
            GROUP BY product_id
        )
        UPDATE inventory_transactions t
        SET unit_cost = COALESCE(a.cost, p.cost_price),
            total_cost = t.quantity * COALESCE(a.cost, p.cost_price)
        FROM products p
        LEFT JOIN avg_cost a ON a.product_id = p.id
        WHERE p.id = t.product_id
          AND t.transaction_type = 'stock_out'
          AND COALESCE(t.unit_cost, 0) = 0
          AND COALESCE(a.cost, p.cost_price, 0) > 0
    """)


def downgrade() -> None:
    # Data repair only; the original ₹0 values carried no information to restore.
    pass
