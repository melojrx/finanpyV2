"""Database client for FinanPy (SQLite/PostgreSQL)."""
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from decimal import Decimal
from typing import Any
import os
import sys

from .config import get_config


@dataclass
class TransactionResult:
    """Result of a transaction operation."""
    id: int
    balance: str
    description: str = ""


@dataclass
class AccountResult:
    """Account data."""
    id: int
    name: str
    balance: str
    account_type: str


@dataclass
class CategoryResult:
    """Category data."""
    id: int
    name: str
    parent_name: str | None
    icon: str


class FinanPyClient:
    """Client for FinanPy database."""

    def __init__(self, config=None):
        """Initialize client with config."""
        self.config = config or get_config()

    @contextmanager
    def _get_connection(self):
        """Get database connection based on config."""
        if self.config.use_sqlite:
            conn = sqlite3.connect(str(self.config.db_path))
            conn.row_factory = sqlite3.Row
            try:
                yield conn
            finally:
                conn.close()
        else:
            import psycopg2
            conn = psycopg2.connect(
                host=self.config.db_host,
                port=self.config.db_port,
                dbname=self.config.db_name,
                user=self.config.db_user,
                password=self.config.db_password,
            )
            try:
                yield conn
            finally:
                conn.close()

    def get_accounts(self) -> list[AccountResult]:
        """Get all accounts with balances."""
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, name, balance, account_type FROM accounts_account ORDER BY id"
            )
            return [
                AccountResult(
                    id=row[0],
                    name=row[1],
                    balance=str(row[2]),
                    account_type=row[3],
                )
                for row in cur.fetchall()
            ]

    def get_categories(self, category_type: str | None = None) -> list[CategoryResult]:
        """Get categories, optionally filtered by type."""
        with self._get_connection() as conn:
            cur = conn.cursor()
            if category_type:
                if self.config.use_sqlite:
                    cur.execute(
                        """SELECT c.id, c.name, p.name as parent_name, c.icon
                           FROM categories_category c
                           LEFT JOIN categories_category p ON c.parent_id = p.id
                           WHERE c.category_type = ? AND c.is_active = 1
                           ORDER BY c.name""",
                        (category_type,)
                    )
                else:
                    cur.execute(
                        """SELECT c.id, c.name, p.name as parent_name, c.icon
                           FROM categories_category c
                           LEFT JOIN categories_category p ON c.parent_id = p.id
                           WHERE c.category_type = %s AND c.is_active = true
                           ORDER BY c.name""",
                        (category_type,)
                    )
            else:
                if self.config.use_sqlite:
                    cur.execute(
                        """SELECT c.id, c.name, p.name as parent_name, c.icon
                           FROM categories_category c
                           LEFT JOIN categories_category p ON c.parent_id = p.id
                           WHERE c.is_active = 1
                           ORDER BY c.name"""
                    )
                else:
                    cur.execute(
                        """SELECT c.id, c.name, p.name as parent_name, c.icon
                           FROM categories_category c
                           LEFT JOIN categories_category p ON c.parent_id = p.id
                           WHERE c.is_active = true
                           ORDER BY c.name"""
                    )
            return [
                CategoryResult(
                    id=row[0],
                    name=row[1],
                    parent_name=row[2],
                    icon=row[3] or "",
                )
                for row in cur.fetchall()
            ]

    def register_transaction(
        self,
        transaction_type: str,
        amount: str,
        description: str,
        transaction_date: str,
        account: int,
        category: int,
        notes: str = "",
    ) -> TransactionResult:
        """Register a new transaction."""
        with self._get_connection() as conn:
            cur = conn.cursor()

            # Get user from account
            cur.execute("SELECT user_id FROM accounts_account WHERE id = ?", (account,))
            user_row = cur.fetchone()
            if not user_row:
                raise ValueError(f"Account {account} not found")
            user_id = user_row[0]

            # Insert transaction (use ? for SQLite, %s for PostgreSQL)
            if self.config.use_sqlite:
                cur.execute(
                    """INSERT INTO transactions_transaction
                       (user_id, account_id, category_id, transaction_type, amount,
                        description, transaction_date, status, notes, confirmed_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, 'CONFIRMED', ?, datetime('now'))""",
                    (user_id, account, category, transaction_type, amount,
                     description, transaction_date, notes)
                )
                tx_id = cur.lastrowid
            else:
                cur.execute(
                    """INSERT INTO transactions_transaction
                       (user_id, account_id, category_id, transaction_type, amount,
                        description, transaction_date, status, notes, confirmed_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, 'CONFIRMED', %s, CURRENT_TIMESTAMP)
                       RETURNING id""",
                    (user_id, account, category, transaction_type, amount,
                     description, transaction_date, notes)
                )
                tx_id = cur.fetchone()[0]

            # Update account balance
            sign = 1 if transaction_type == "INCOME" else -1
            if self.config.use_sqlite:
                cur.execute(
                    "UPDATE accounts_account SET balance = balance + (? * ?) WHERE id = ?",
                    (sign, amount, account)
                )
            else:
                cur.execute(
                    "UPDATE accounts_account SET balance = balance + (%s * %s) WHERE id = %s",
                    (sign, amount, account)
                )

            # Get new balance
            cur.execute("SELECT balance FROM accounts_account WHERE id = ?", (account,))
            new_balance = cur.fetchone()[0]

            conn.commit()

            return TransactionResult(
                id=tx_id,
                balance=str(new_balance),
                description=description,
            )

    def get_transactions(
        self,
        year: int | None = None,
        month: int | None = None,
        account: int | None = None,
        transaction_type: str | None = None,
        category: int | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """Get transactions with filters."""
        with self._get_connection() as conn:
            cur = conn.cursor()

            conditions = []
            params = []

            if year and month:
                if self.config.use_sqlite:
                    conditions.append("strftime('%Y', transaction_date) = ?")
                    params.append(str(year))
                    conditions.append("strftime('%m', transaction_date) = ?")
                    params.append(f"{month:02d}")
                else:
                    conditions.append("TO_CHAR(transaction_date, 'YYYY') = %s")
                    params.append(str(year))
                    conditions.append("TO_CHAR(transaction_date, 'MM') = %s")
                    params.append(f"{month:02d}")

            if account:
                if self.config.use_sqlite:
                    conditions.append("account_id = ?")
                else:
                    conditions.append("account_id = %s")
                params.append(account)

            if transaction_type:
                if self.config.use_sqlite:
                    conditions.append("transaction_type = ?")
                else:
                    conditions.append("transaction_type = %s")
                params.append(transaction_type)

            if category:
                if self.config.use_sqlite:
                    conditions.append("category_id = ?")
                else:
                    conditions.append("category_id = %s")
                params.append(category)

            where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

            if self.config.use_sqlite:
                cur.execute(
                    f"""SELECT t.id, t.transaction_date, t.transaction_type, t.amount,
                               t.description, c.name as category_name
                        FROM transactions_transaction t
                        JOIN categories_category c ON t.category_id = c.id
                        {where}
                        ORDER BY t.transaction_date DESC, t.created_at DESC
                        LIMIT ?""",
                    params + [limit]
                )
            else:
                cur.execute(
                    f"""SELECT t.id, t.transaction_date, t.transaction_type, t.amount,
                               t.description, c.name as category_name
                        FROM transactions_transaction t
                        JOIN categories_category c ON t.category_id = c.id
                        {where}
                        ORDER BY t.transaction_date DESC, t.created_at DESC
                        LIMIT %s""",
                    params + [limit]
                )

            return [
                {
                    "id": row[0],
                    "date": row[1],
                    "type": row[2],
                    "amount": str(row[3]),
                    "description": row[4],
                    "category": row[5],
                }
                for row in cur.fetchall()
            ]

    def monthly_summary(self, year: int, month: int) -> dict:
        """Get monthly summary."""
        with self._get_connection() as conn:
            cur = conn.cursor()

            month_str = f"{year}-{month:02d}"

            if self.config.use_sqlite:
                cur.execute(
                    """SELECT transaction_type, SUM(amount), COUNT(*)
                       FROM transactions_transaction
                       WHERE strftime('%Y-%m', transaction_date) = ? AND status = 'CONFIRMED'
                       GROUP BY transaction_type""",
                    (month_str,)
                )
            else:
                cur.execute(
                    """SELECT transaction_type, SUM(amount), COUNT(*)
                       FROM transactions_transaction
                       WHERE TO_CHAR(transaction_date, 'YYYY-MM') = %s AND status = 'CONFIRMED'
                       GROUP BY transaction_type""",
                    (month_str,)
                )

            result = {"income": "0", "expenses": "0", "balance": "0", "count": 0}

            for row in cur.fetchall():
                if row[0] == "INCOME":
                    result["income"] = str(row[1])
                elif row[0] == "EXPENSE":
                    result["expenses"] = str(row[1])
                result["count"] += row[2]

            income = Decimal(result["income"])
            expenses = Decimal(result["expenses"])
            result["balance"] = str(income - expenses)

            return result

    def yearly_summary(self, year: int) -> list[dict]:
        """Get yearly summary by month."""
        with self._get_connection() as conn:
            cur = conn.cursor()

            if self.config.use_sqlite:
                cur.execute(
                    """SELECT strftime('%m', transaction_date) as month,
                              transaction_type, SUM(amount)
                       FROM transactions_transaction
                       WHERE strftime('%Y', transaction_date) = ? AND status = 'CONFIRMED'
                       GROUP BY month, transaction_type
                       ORDER BY month""",
                    (str(year),)
                )
            else:
                cur.execute(
                    """SELECT TO_CHAR(transaction_date, 'MM') as month,
                              transaction_type, SUM(amount)
                       FROM transactions_transaction
                       WHERE TO_CHAR(transaction_date, 'YYYY') = %s AND status = 'CONFIRMED'
                       GROUP BY month, transaction_type
                       ORDER BY month""",
                    (str(year),)
                )

            months = {f"{i:02d}": {"income": Decimal("0"), "expenses": Decimal("0")}
                      for i in range(1, 13)}

            for row in cur.fetchall():
                m = row[0]
                if row[1] == "INCOME":
                    months[m]["income"] += row[2]
                elif row[1] == "EXPENSE":
                    months[m]["expenses"] += row[2]

            return [
                {
                    "month": int(m),
                    "income": str(data["income"]),
                    "expenses": str(data["expenses"]),
                    "balance": str(data["income"] - data["expenses"]),
                }
                for m, data in sorted(months.items())
            ]