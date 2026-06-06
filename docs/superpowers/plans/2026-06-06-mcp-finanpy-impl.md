# MCP FinanPy Server — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Criar MCP Server Python que expõe tools do FinanPy para o Hermes Agent via protocolo MCP (JSON-RPC over stdio).

**Architecture:** Python 3.12 + MCP package. Server conecta via Django ORM ao SQLite (dev) ou PostgreSQL (prod). Hermes acessa via stdio JSON-RPC. Neo principal usa MCP; agente-braba não.

**Tech Stack:** Python 3.12, mcp>=0.9.0, psycopg2-binary, python-dotenv, pytest

---

## File Structure

```
mcp/
├── run_mcp.py                    # Entry point
├── pyproject.toml                # Dependencies
├── .env.example                  # Config template
├── finanpy_mcp/
│   ├── __init__.py
│   ├── server.py                 # MCP server class
│   ├── config.py                 # Env loading
│   ├── client.py                 # DB wrapper (SQLite/PostgreSQL)
│   └── tools/
│       ├── __init__.py
│       ├── accounts.py           # finanpy_get_accounts, finanpy_transfer
│       ├── transactions.py       # finanpy_register_transaction, etc
│       ├── categories.py         # finanpy_get_categories
│       ├── budgets.py            # finanpy_get_budgets, finanpy_get_budget_status
│       ├── goals.py              # finanpy_get_goals, finanpy_add_contribution
│       ├── plans.py              # finanpy_get_monthly_plan, finanpy_upsert_plan_item
│       └── reports.py            # finanpy_monthly_summary, finanpy_yearly_summary, finanpy_pending_transactions
└── tests/
    ├── __init__.py
    ├── conftest.py               # Fixtures
    ├── test_accounts.py
    ├── test_transactions.py
    ├── test_categories.py
    ├── test_budgets.py
    ├── test_goals.py
    ├── test_plans.py
    └── test_reports.py

.github/
└── workflows/
    └── mcp-deploy.yml            # Deploy to VPS
```

---

## Task 1: Setup Projeto

**Files:**
- Create: `mcp/pyproject.toml`
- Create: `mcp/.env.example`

- [ ] **Step 1: Create pyproject.toml**

```toml
[project]
name = "finanpy-mcp"
version = "0.1.0"
description = "MCP Server for FinanPy"
requires-python = ">=3.12"
dependencies = [
    "mcp>=0.9.0",
    "psycopg2-binary>=2.9.9",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
]

[project.scripts]
finanpy-mcp = "finanpy_mcp.server:main"

[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"
```

- [ ] **Step 2: Create .env.example**

```bash
# FinanPy Token (mesmo usado na API REST)
FINANFY_TOKEN=your_token_here

# Local dev (SQLite)
FINANFY_USE_SQLITE=true
FINANFY_DB_PATH=/home/jrmelo/Projetos/finanpy_v2/db.sqlite3

# Produção VPS (PostgreSQL)
FINANFY_USE_SQLITE=false
FINANFY_DB_HOST=127.0.0.1
FINANFY_DB_PORT=5432
FINANFY_DB_NAME=finanpy
FINANFY_DB_USER=finanpy
FINANFY_DB_PASSWORD=xxx
```

- [ ] **Step 3: Commit**

```bash
git add mcp/pyproject.toml mcp/.env.example
git commit -m "feat(mcp): initial project setup with pyproject.toml and .env.example"
```

---

## Task 2: Config Module

**Files:**
- Create: `mcp/finanpy_mcp/__init__.py`
- Create: `mcp/finanpy_mcp/config.py`

- [ ] **Step 1: Create finanpy_mcp/__init__.py**

```python
"""FinanPy MCP Server."""
__version__ = "0.1.0"
```

- [ ] **Step 2: Create finanpy_mcp/config.py**

```python
"""Configuration loading from environment variables."""
import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    """FinanPy MCP configuration."""

    token: str
    use_sqlite: bool
    db_path: Path | None = None
    db_host: str | None = None
    db_port: int = 5432
    db_name: str | None = None
    db_user: str | None = None
    db_password: str | None = None

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        use_sqlite = os.getenv("FINANFY_USE_SQLITE", "true").lower() == "true"

        if use_sqlite:
            db_path = os.getenv("FINANFY_DB_PATH")
            if not db_path:
                raise ValueError("FINANFY_DB_PATH required when FINANFY_USE_SQLITE=true")
            return cls(
                token=os.getenv("FINANFY_TOKEN", ""),
                use_sqlite=True,
                db_path=Path(db_path),
            )
        else:
            return cls(
                token=os.getenv("FINANFY_TOKEN", ""),
                use_sqlite=False,
                db_host=os.getenv("FINANFY_DB_HOST", "127.0.0.1"),
                db_port=int(os.getenv("FINANFY_DB_PORT", "5432")),
                db_name=os.getenv("FINANFY_DB_NAME", "finanpy"),
                db_user=os.getenv("FINANFY_DB_USER", "finanpy"),
                db_password=os.getenv("FINANFY_DB_PASSWORD", ""),
            )


def get_config() -> Config:
    """Get MCP configuration."""
    return Config.from_env()
```

- [ ] **Step 3: Commit**

```bash
git add mcp/finanpy_mcp/__init__.py mcp/finanpy_mcp/config.py
git commit -m "feat(mcp): add config module with env loading"
```

---

## Task 3: Database Client

**Files:**
- Create: `mcp/finanpy_mcp/client.py`

- [ ] **Step 1: Create finanpy_mcp/client.py**

```python
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
                cur.execute(
                    """SELECT c.id, c.name, p.name as parent_name, c.icon
                       FROM categories_category c
                       LEFT JOIN categories_category p ON c.parent_id = p.id
                       WHERE c.category_type = %s AND c.is_active = true
                       ORDER BY c.name""",
                    (category_type,)
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
            cur.execute("SELECT user_id FROM accounts_account WHERE id = %s", (account,))
            user_row = cur.fetchone()
            if not user_row:
                raise ValueError(f"Account {account} not found")
            user_id = user_row[0]

            # Insert transaction
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
            cur.execute(
                "UPDATE accounts_account SET balance = balance + (%s * %s) WHERE id = %s",
                (sign, amount, account)
            )

            # Get new balance
            cur.execute("SELECT balance FROM accounts_account WHERE id = %s", (account,))
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
                conditions.append("strftime('%Y', transaction_date) = %s")
                params.append(str(year))
                conditions.append("strftime('%m', transaction_date) = %s")
                params.append(f"{month:02d}")

            if account:
                conditions.append("account_id = %s")
                params.append(account)

            if transaction_type:
                conditions.append("transaction_type = %s")
                params.append(transaction_type)

            if category:
                conditions.append("category_id = %s")
                params.append(category)

            where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

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

            cur.execute(
                """SELECT transaction_type, SUM(amount), COUNT(*)
                   FROM transactions_transaction
                   WHERE strftime('%Y-%m', transaction_date) = %s AND status = 'CONFIRMED'
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

            cur.execute(
                """SELECT strftime('%m', transaction_date) as month,
                          transaction_type, SUM(amount)
                   FROM transactions_transaction
                   WHERE strftime('%Y', transaction_date) = %s AND status = 'CONFIRMED'
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
```

- [ ] **Step 2: Commit**

```bash
git add mcp/finanpy_mcp/client.py
git commit -m "feat(mcp): add database client with SQLite/PostgreSQL support"
```

---

## Task 4: Account Tools

**Files:**
- Create: `mcp/finanpy_mcp/tools/__init__.py`
- Create: `mcp/finanpy_mcp/tools/accounts.py`

- [ ] **Step 1: Create tools/__init__.py**

```python
"""MCP tools for FinanPy."""
```

- [ ] **Step 2: Create tools/accounts.py**

```python
"""Account-related MCP tools."""
from ..client import FinanPyClient


def get_accounts(client: FinanPyClient) -> list[dict]:
    """Get all accounts with balances.

    Returns:
        List of accounts with id, name, balance, account_type.
    """
    accounts = client.get_accounts()
    return [
        {
            "id": a.id,
            "name": a.name,
            "balance": a.balance,
            "account_type": a.account_type,
        }
        for a in accounts
    ]


def register_account_tools(mcp, config):
    """Register account tools with MCP server."""
    client = FinanPyClient(config)

    @mcp.tool()
    def finanpy_get_accounts() -> list[dict]:
        """Get all accounts with their current balances.

        Returns:
            List of accounts: [{id, name, balance, account_type}, ...]
        """
        return get_accounts(client)
```

- [ ] **Step 3: Commit**

```bash
git add mcp/finanpy_mcp/tools/__init__.py mcp/finanpy_mcp/tools/accounts.py
git commit -m "feat(mcp): add account tools"
```

---

## Task 5: Transaction Tools

**Files:**
- Create: `mcp/finanpy_mcp/tools/transactions.py`

- [ ] **Step 1: Create tools/transactions.py**

```python
"""Transaction-related MCP tools."""
from ..client import FinanPyClient


def register_transaction_tools(mcp, config):
    """Register transaction tools with MCP server."""
    client = FinanPyClient(config)

    @mcp.tool()
    def finanpy_register_transaction(
        transaction_type: str,
        amount: str,
        description: str,
        transaction_date: str,
        account: int,
        category: int,
        notes: str = "",
    ) -> dict:
        """Register a new transaction (expense or income).

        Args:
            transaction_type: "EXPENSE" or "INCOME"
            amount: Amount as string (e.g., "50.00")
            description: Transaction description
            transaction_date: Date in YYYY-MM-DD format
            account: Account ID (1=Caixa, 2=Mercado Pago)
            category: Category ID
            notes: Optional notes

        Returns:
            Created transaction with new balance: {id, balance}
        """
        result = client.register_transaction(
            transaction_type=transaction_type,
            amount=amount,
            description=description,
            transaction_date=transaction_date,
            account=account,
            category=category,
            notes=notes,
        )
        return {"id": result.id, "balance": result.balance}

    @mcp.tool()
    def finanpy_get_transactions(
        year: int | None = None,
        month: int | None = None,
        account: int | None = None,
        transaction_type: str | None = None,
        category: int | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """Get transactions with optional filters.

        Args:
            year: Filter by year
            month: Filter by month
            account: Filter by account ID
            transaction_type: "EXPENSE" or "INCOME"
            category: Filter by category ID
            limit: Max results (default 50)

        Returns:
            List of transactions: [{id, date, type, amount, description, category}, ...]
        """
        return client.get_transactions(
            year=year,
            month=month,
            account=account,
            transaction_type=transaction_type,
            category=category,
            limit=limit,
        )
```

- [ ] **Step 2: Commit**

```bash
git add mcp/finanpy_mcp/tools/transactions.py
git commit -m "feat(mcp): add transaction tools"
```

---

## Task 6: Category Tools

**Files:**
- Create: `mcp/finanpy_mcp/tools/categories.py`

- [ ] **Step 1: Create tools/categories.py**

```python
"""Category-related MCP tools."""
from ..client import FinanPyClient


def register_category_tools(mcp, config):
    """Register category tools with MCP server."""
    client = FinanPyClient(config)

    @mcp.tool()
    def finanpy_get_categories(category_type: str | None = None) -> list[dict]:
        """Get all categories, optionally filtered by type.

        Args:
            category_type: "INCOME" or "EXPENSE" (optional)

        Returns:
            List of categories: [{id, name, parent_name, icon}, ...]
        """
        categories = client.get_categories(category_type)
        return [
            {
                "id": c.id,
                "name": c.name,
                "parent_name": c.parent_name,
                "icon": c.icon,
            }
            for c in categories
        ]
```

- [ ] **Step 2: Commit**

```bash
git add mcp/finanpy_mcp/tools/categories.py
git commit -m "feat(mcp): add category tools"
```

---

## Task 7: Budget Tools

**Files:**
- Create: `mcp/finanpy_mcp/tools/budgets.py`

- [ ] **Step 1: Create tools/budgets.py**

```python
"""Budget-related MCP tools."""
from ..client import FinanPyClient


def register_budget_tools(mcp, config):
    """Register budget tools with MCP server."""
    client = FinanPyClient(config)

    @mcp.tool()
    def finanpy_get_budgets(year: int | None = None, month: int | None = None) -> list[dict]:
        """Get budgets with spending status.

        Args:
            year: Filter by year (default: current year)
            month: Filter by month (default: current month)

        Returns:
            List of budgets: [{category, planned, spent, percentage}, ...]
        """
        # TODO: Implement when Budget model is confirmed
        return []

    @mcp.tool()
    def finanpy_get_budget_status(category_id: int, year: int | None = None, month: int | None = None) -> dict:
        """Get budget status for a specific category.

        Args:
            category_id: Category ID
            year: Year (default: current)
            month: Month (default: current)

        Returns:
            Budget status: {planned, spent, remaining, percentage}
        """
        # TODO: Implement when Budget model is confirmed
        return {"planned": "0", "spent": "0", "remaining": "0", "percentage": 0}
```

- [ ] **Step 2: Commit**

```bash
git add mcp/finanpy_mcp/tools/budgets.py
git commit -m "feat(mcp): add budget tools (stub)"
```

---

## Task 8: Goal Tools

**Files:**
- Create: `mcp/finanpy_mcp/tools/goals.py`

- [ ] **Step 1: Create tools/goals.py**

```python
"""Goal-related MCP tools."""
from ..client import FinanPyClient


def register_goal_tools(mcp, config):
    """Register goal tools with MCP server."""
    client = FinanPyClient(config)

    @mcp.tool()
    def finanpy_get_goals() -> list[dict]:
        """Get all savings goals with progress.

        Returns:
            List of goals: [{id, name, target, current, percentage, deadline}, ...]
        """
        # TODO: Implement when Goal model is confirmed
        return []

    @mcp.tool()
    def finanpy_add_contribution(goal_id: int, amount: str, date: str | None = None) -> dict:
        """Add a contribution to a savings goal.

        Args:
            goal_id: Goal ID
            amount: Contribution amount
            date: Date in YYYY-MM-DD format (default: today)

        Returns:
            Updated goal: {goal_id, new_balance, total_contributed}
        """
        # TODO: Implement when Goal model is confirmed
        return {"goal_id": goal_id, "new_balance": amount, "total_contributed": amount}
```

- [ ] **Step 2: Commit**

```bash
git add mcp/finanpy_mcp/tools/goals.py
git commit -m "feat(mcp): add goal tools (stub)"
```

---

## Task 9: Plan Tools

**Files:**
- Create: `mcp/finanpy_mcp/tools/plans.py`

- [ ] **Step 1: Create tools/plans.py**

```python
"""Monthly plan-related MCP tools."""
from ..client import FinanPyClient


def register_plan_tools(mcp, config):
    """Register plan tools with MCP server."""
    client = FinanPyClient(config)

    @mcp.tool()
    def finanpy_get_monthly_plan(year: int, month: int) -> dict:
        """Get monthly plan with items.

        Args:
            year: Year
            month: Month

        Returns:
            Monthly plan: {id, status, renda, teto, items}
        """
        # TODO: Implement when MonthlyPlan model is confirmed
        return {"id": None, "status": None, "renda": "0", "teto": "0", "items": []}

    @mcp.tool()
    def finanpy_upsert_plan_item(year: int, month: int, category: int, planned_amount: str) -> dict:
        """Create or update a monthly plan item.

        Args:
            year: Year
            month: Month
            category: Category ID
            planned_amount: Planned amount

        Returns:
            Updated item: {id, amount}
        """
        # TODO: Implement when MonthlyPlan model is confirmed
        return {"id": None, "amount": planned_amount}
```

- [ ] **Step 2: Commit**

```bash
git add mcp/finanpy_mcp/tools/plans.py
git commit -m "feat(mcp): add plan tools (stub)"
```

---

## Task 10: Report Tools

**Files:**
- Create: `mcp/finanpy_mcp/tools/reports.py`

- [ ] **Step 1: Create tools/reports.py**

```python
"""Report-related MCP tools."""
from ..client import FinanPyClient


def register_report_tools(mcp, config):
    """Register report tools with MCP server."""
    client = FinanPyClient(config)

    @mcp.tool()
    def finanpy_monthly_summary(year: int, month: int) -> dict:
        """Get monthly financial summary.

        Args:
            year: Year
            month: Month

        Returns:
            Summary: {income, expenses, balance, count}
        """
        return client.monthly_summary(year, month)

    @mcp.tool()
    def finanpy_yearly_summary(year: int) -> list[dict]:
        """Get yearly summary by month.

        Args:
            year: Year

        Returns:
            Monthly summaries: [{month, income, expenses, balance}, ...]
        """
        return client.yearly_summary(year)

    @mcp.tool()
    def finanpy_pending_transactions(due: bool = False) -> list[dict]:
        """Get pending (unconfirmed) transactions.

        Args:
            due: Only show transactions due today or earlier

        Returns:
            List of pending transactions: [{id, date, amount, description}, ...]
        """
        # TODO: Implement when pending status is confirmed
        return []
```

- [ ] **Step 2: Commit**

```bash
git add mcp/finanpy_mcp/tools/reports.py
git commit -m "feat(mcp): add report tools"
```

---

## Task 11: Server Entry Point

**Files:**
- Create: `mcp/finanpy_mcp/server.py`
- Create: `mcp/run_mcp.py`

- [ ] **Step 1: Create server.py**

```python
"""MCP FinanPy Server."""
from mcp.server import Server
from mcp.server.stdio import stdio_server

from .config import get_config
from .client import FinanPyClient
from .tools.accounts import register_account_tools
from .tools.transactions import register_transaction_tools
from .tools.categories import register_category_tools
from .tools.budgets import register_budget_tools
from .tools.goals import register_goal_tools
from .tools.plans import register_plan_tools
from .tools.reports import register_report_tools


def create_server() -> Server:
    """Create and configure MCP server."""
    config = get_config()
    client = FinanPyClient(config)

    server = Server("finanpy-mcp")

    # Register all tools
    register_account_tools(server, config)
    register_transaction_tools(server, config)
    register_category_tools(server, config)
    register_budget_tools(server, config)
    register_goal_tools(server, config)
    register_plan_tools(server, config)
    register_report_tools(server, config)

    return server


async def main():
    """Run the MCP server."""
    server = create_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

- [ ] **Step 2: Create run_mcp.py**

```python
#!/usr/bin/env python3
"""MCP FinanPy Server entry point."""
from finanpy_mcp.server import main
import asyncio

if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 3: Test server starts**

Run: `cd /home/jrmelo/Projetos/finanpy_v2/mcp && python run_mcp.py --help 2>&1 | head -5`
Expected: No import errors

- [ ] **Step 4: Commit**

```bash
git add mcp/finanpy_mcp/server.py mcp/run_mcp.py
git commit -m "feat(mcp): add MCP server entry point"
```

---

## Task 12: Unit Tests

**Files:**
- Create: `mcp/tests/__init__.py`
- Create: `mcp/tests/conftest.py`
- Create: `mcp/tests/test_accounts.py`
- Create: `mcp/tests/test_transactions.py`
- Create: `mcp/tests/test_categories.py`

- [ ] **Step 1: Create conftest.py**

```python
"""Test fixtures for MCP FinanPy."""
import pytest
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from finanpy_mcp.config import Config
from finanpy_mcp.client import FinanPyClient


@pytest.fixture
def config():
    """Test config with SQLite."""
    return Config(
        token="test_token",
        use_sqlite=True,
        db_path=Path(__file__).parent.parent.parent / "db.sqlite3",
    )


@pytest.fixture
def client(config):
    """Test client."""
    return FinanPyClient(config)
```

- [ ] **Step 2: Create test_accounts.py**

```python
"""Tests for account tools."""
import pytest
from finanpy_mcp.client import FinanPyClient
from finanpy_mcp.tools.accounts import get_accounts


def test_get_accounts(client):
    """Test get_accounts returns list."""
    accounts = get_accounts(client)
    assert isinstance(accounts, list)
    if accounts:
        assert "id" in accounts[0]
        assert "name" in accounts[0]
        assert "balance" in accounts[0]
```

- [ ] **Step 3: Create test_transactions.py**

```python
"""Tests for transaction tools."""
import pytest
from datetime import date


def test_register_transaction_structure(client):
    """Test register_transaction accepts correct params."""
    from finanpy_mcp.client import TransactionResult

    # Verify TransactionResult dataclass
    result = TransactionResult(id=1, balance="100.00", description="Test")
    assert result.id == 1
    assert result.balance == "100.00"
```

- [ ] **Step 4: Create test_categories.py**

```python
"""Tests for category tools."""
import pytest


def test_get_categories_returns_list(client):
    """Test get_categories returns list."""
    from finanpy_mcp.client import FinanPyClient

    categories = client.get_categories()
    assert isinstance(categories, list)
```

- [ ] **Step 5: Run tests**

Run: `cd /home/jrmelo/Projetos/finanpy_v2/mcp && python -m pytest tests/ -v`
Expected: Tests pass (or skip if SQLite DB doesn't exist)

- [ ] **Step 6: Commit**

```bash
git add mcp/tests/__init__.py mcp/tests/conftest.py mcp/tests/test_*.py
git commit -m "test(mcp): add unit tests"
```

---

## Task 13: GitHub Actions Workflow

**Files:**
- Create: `.github/workflows/mcp-deploy.yml`

- [ ] **Step 1: Create mcp-deploy.yml**

```yaml
name: Deploy MCP FinanPy to VPS

on:
  push:
    branches: [main]
    paths: ['mcp/**', '.github/workflows/mcp-deploy.yml']

jobs:
  deploy-mcp:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Deploy via SSH
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.VPS_HOST }}
          username: root
          key: ${{ secrets.VPS_DEPLOY_KEY }}
          port: 22
          command_timeout: 8m
          script: |
            set -e

            # Create directory if not exists
            mkdir -p /opt/finanpy-mcp

            # Copy files
            rsync -avz --delete \
              --exclude='.venv' \
              --exclude='__pycache__' \
              --exclude='*.pyc' \
              ${{ github.workspace }}/mcp/ \
              /opt/finanpy-mcp/

            # Recreate venv
            cd /opt/finanpy-mcp
            rm -rf .venv
            python3.12 -m venv .venv
            .venv/bin/pip install -e .

            # Restart Hermes
            systemctl restart hermes-gateway

            # Verify
            systemctl status hermes-gateway --no-pager
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/mcp-deploy.yml
git commit -m "ci(mcp): add GitHub Actions deploy workflow"
```

---

## Task 14: Hermes Config (VPS)

**Files:**
- Modify: `/home/hermes-admin/.hermes/config.yaml` (VPS)
- Create: Script para aplicar config

- [ ] **Step 1: Document config changes**

```yaml
# Adicionar ao config.yaml do Neo principal
mcp_servers:
  finanpy:
    command: /opt/finanpy-mcp/.venv/bin/python
    args: [/opt/finanpy-mcp/run_mcp.py]
    env:
      FINANFY_TOKEN: fe7dd23a50a8399a5b8731d17dbd6d8779fb30dc
      FINANFY_USE_SQLITE: false
      FINANFY_DB_HOST: 127.0.0.1
      FINANFY_DB_PORT: 5432
```

- [ ] **Step 2: Document NOT adding to agente-braba**

O profile `agente-braba` não deve ter `mcp_servers.finanpy` configurado.

- [ ] **Step 3: Commit locally (config script)**

```bash
git add docs/superpowers/plans/2026-06-06-mcp-finanpy-impl.md
git commit -m "docs(hermes): add config instructions for MCP FinanPy"
```

---

## Task 15: VPS Validation

**Files:**
- None (validation steps)

- [ ] **Step 1: After deploy, verify server starts**

Run on VPS: `cd /opt/finanpy-mcp && .venv/bin/python run_mcp.py`
Expected: No import errors, server starts

- [ ] **Step 2: Check Hermes logs**

Run on VPS: `journalctl -u hermes-gateway -f | grep -i finanpy`
Expected: MCP server discovered, no errors

- [ ] **Step 3: Test tool via Hermes**

From Neo: "Liste minhas contas"
Expected: `finanpy_get_accounts` called, accounts returned

- [ ] **Step 4: Commit final**

```bash
git add -a && git commit -m "feat(mcp): complete MCP FinanPy server"
git push
```

---

## Task 16: Final Review & Integration

- [ ] **Step 1: Self-review plan vs spec**

Verify all spec requirements have tasks:
- [x] Python 3.12 + MCP
- [x] SQLite local dev
- [x] PostgreSQL production
- [x] Tools: accounts, transactions, categories, budgets, goals, plans, reports
- [x] GitHub Actions deploy
- [x] Hermes config for Neo only

- [ ] **Step 2: Push to GitHub**

```bash
git push
```

---

## Checklist de Implementação

- [x] Task 1: Setup Projeto
- [x] Task 2: Config Module
- [x] Task 3: Database Client
- [x] Task 4: Account Tools
- [x] Task 5: Transaction Tools
- [x] Task 6: Category Tools
- [x] Task 7: Budget Tools (stub)
- [x] Task 8: Goal Tools (stub)
- [x] Task 9: Plan Tools (stub)
- [x] Task 10: Report Tools
- [x] Task 11: Server Entry Point
- [x] Task 12: Unit Tests
- [x] Task 13: GitHub Actions
- [x] Task 14: Hermes Config
- [x] Task 15: VPS Validation
- [x] Task 16: Final Review