"""The agent's safety property, tested without calling the LLM: its database cannot be written to."""
import sqlite3

import pytest

from retailgenius.agent import read_only_db


def test_agent_db_can_read(orders_db):
    assert "6" in read_only_db(orders_db).run("SELECT COUNT(*) FROM orders")


@pytest.mark.parametrize("statement", [
    "DELETE FROM orders",
    "DROP TABLE orders",
    "UPDATE orders SET sales = 0",
    "INSERT INTO orders (order_id) VALUES (99)",
])
def test_agent_db_rejects_writes(orders_db, statement):
    with pytest.raises(Exception, match="readonly"):
        read_only_db(orders_db).run(statement)
    with sqlite3.connect(orders_db) as conn:          # data untouched
        assert conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 6
