"""
Test suite for the budgets app.

Coverage:
- Budget model validation and constraints
- Calculated properties (spent_amount, percentage_used, remaining_amount,
  daily_* metrics) including subcategory aggregation and period boundaries
- Signal-driven cache refresh on Transaction save/delete
- View-level user isolation (List, Detail, Create, Update, Delete)
"""

from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from accounts.models import Account
from budgets.models import Budget, BudgetAlert
from categories.models import Category
from transactions.models import Transaction

User = get_user_model()


def _month_range(reference=None):
    """Return (first_day, last_day) of the month containing `reference`."""
    today = reference or date.today()
    first = today.replace(day=1)
    next_month = (first + timedelta(days=32)).replace(day=1)
    last = next_month - timedelta(days=1)
    return first, last


class BudgetTestMixin:
    """Shared fixtures for budget-related tests."""

    @classmethod
    def make_user(cls, suffix=""):
        return User.objects.create_user(
            username=f"alice{suffix}",
            email=f"alice{suffix}@example.com",
            password="testpass123",
        )

    @classmethod
    def make_expense_category(cls, user, name="Alimentação", parent=None):
        return Category.objects.create(
            user=user,
            name=name,
            category_type="EXPENSE",
            parent=parent,
        )

    @classmethod
    def make_account(cls, user, name="Conta Corrente"):
        return Account.objects.create(
            user=user,
            name=name,
            account_type="checking",
            balance=Decimal("10000.00"),
        )

    @classmethod
    def make_budget(cls, user, category, **overrides):
        first, last = _month_range()
        defaults = dict(
            user=user,
            category=category,
            name=f"Orçamento {category.name}",
            planned_amount=Decimal("500.00"),
            start_date=first,
            end_date=last,
            is_active=True,
        )
        defaults.update(overrides)
        return Budget.objects.create(**defaults)

    @classmethod
    def make_expense(cls, user, account, category, amount, when=None):
        return Transaction.objects.create(
            user=user,
            account=account,
            category=category,
            transaction_type="EXPENSE",
            amount=Decimal(str(amount)),
            description=f"Despesa {amount}",
            transaction_date=when or date.today(),
        )


class BudgetModelTests(BudgetTestMixin, TestCase):
    """Validation rules and constraints on the Budget model."""

    def setUp(self):
        self.user = self.make_user()
        self.category = self.make_expense_category(self.user)

    def test_create_valid_budget(self):
        budget = self.make_budget(self.user, self.category)
        self.assertEqual(budget.spent_amount, Decimal("0.00"))
        self.assertTrue(budget.is_active)
        self.assertEqual(str(budget), f"{budget.name} ({budget.start_date} - {budget.end_date})")

    def test_planned_amount_must_be_positive(self):
        with self.assertRaises(ValidationError):
            self.make_budget(self.user, self.category, planned_amount=Decimal("0.00"))

    def test_end_date_before_start_date_rejected(self):
        first, last = _month_range()
        with self.assertRaises(ValidationError):
            self.make_budget(
                self.user, self.category,
                start_date=last, end_date=first,
            )

    def test_period_longer_than_one_year_rejected(self):
        start = date.today().replace(day=1)
        with self.assertRaises(ValidationError):
            self.make_budget(
                self.user, self.category,
                start_date=start, end_date=start + timedelta(days=400),
            )

    def test_income_category_rejected(self):
        income_cat = Category.objects.create(
            user=self.user, name="Salário", category_type="INCOME",
        )
        with self.assertRaises(ValidationError):
            self.make_budget(self.user, income_cat)

    def test_inactive_category_rejected(self):
        self.category.is_active = False
        self.category.save()
        with self.assertRaises(ValidationError):
            self.make_budget(self.user, self.category)

    def test_category_must_belong_to_same_user(self):
        other_user = self.make_user(suffix="2")
        with self.assertRaises(ValidationError):
            self.make_budget(other_user, self.category)

    def test_overlapping_budgets_for_same_category_rejected(self):
        self.make_budget(self.user, self.category)
        with self.assertRaises(ValidationError):
            # Same category, overlapping period -> blocked
            self.make_budget(self.user, self.category, name="Outro nome")

    def test_non_overlapping_budgets_for_same_category_allowed(self):
        first, last = _month_range()
        self.make_budget(self.user, self.category)
        next_start = last + timedelta(days=1)
        next_end = next_start + timedelta(days=27)
        # Should not raise
        self.make_budget(
            self.user, self.category,
            name="Próximo mês",
            start_date=next_start, end_date=next_end,
        )

    def test_default_status_is_active_when_period_current(self):
        budget = self.make_budget(self.user, self.category)
        self.assertEqual(budget.status, "ACTIVE")
        self.assertEqual(budget.status_display, "Ativo")


class BudgetCalculationTests(BudgetTestMixin, TestCase):
    """spent_amount aggregation, percentages, and daily metrics."""

    def setUp(self):
        self.user = self.make_user()
        self.account = self.make_account(self.user)
        self.parent_cat = self.make_expense_category(self.user, name="Alimentação")
        self.child_cat = self.make_expense_category(
            self.user, name="Restaurantes", parent=self.parent_cat,
        )
        self.budget = self.make_budget(
            self.user, self.parent_cat,
            planned_amount=Decimal("1000.00"),
        )

    def test_spent_amount_sums_direct_category_transactions(self):
        self.make_expense(self.user, self.account, self.parent_cat, "120.00")
        self.make_expense(self.user, self.account, self.parent_cat, "80.00")
        self.budget.refresh_from_db()
        self.budget.clear_cache()
        self.assertEqual(self.budget.spent_amount, Decimal("200.00"))

    def test_spent_amount_includes_subcategory_transactions(self):
        self.make_expense(self.user, self.account, self.parent_cat, "100.00")
        self.make_expense(self.user, self.account, self.child_cat, "150.00")
        self.budget.refresh_from_db()
        self.budget.clear_cache()
        self.assertEqual(self.budget.spent_amount, Decimal("250.00"))

    def test_spent_amount_ignores_transactions_outside_period(self):
        before_period = self.budget.start_date - timedelta(days=1)
        self.make_expense(
            self.user, self.account, self.parent_cat,
            "500.00", when=before_period,
        )
        self.budget.refresh_from_db()
        self.budget.clear_cache()
        self.assertEqual(self.budget.spent_amount, Decimal("0.00"))

    def test_spent_amount_ignores_other_users_transactions(self):
        other_user = self.make_user(suffix="2")
        other_account = self.make_account(other_user)
        # Same category name on the other user, but distinct row
        other_cat = self.make_expense_category(other_user, name="Alimentação")
        self.make_expense(other_user, other_account, other_cat, "999.00")
        self.budget.refresh_from_db()
        self.budget.clear_cache()
        self.assertEqual(self.budget.spent_amount, Decimal("0.00"))

    def test_percentage_used_and_remaining_amount(self):
        self.make_expense(self.user, self.account, self.parent_cat, "250.00")
        self.budget.refresh_from_db()
        self.budget.clear_cache()
        self.assertEqual(self.budget.percentage_used, Decimal("25.00"))
        self.assertEqual(self.budget.remaining_amount, Decimal("750.00"))
        self.assertFalse(self.budget.is_over_budget)

    def test_is_over_budget_when_spent_exceeds_planned(self):
        self.make_expense(self.user, self.account, self.parent_cat, "1200.00")
        self.budget.refresh_from_db()
        self.budget.clear_cache()
        self.assertTrue(self.budget.is_over_budget)
        self.assertLess(self.budget.remaining_amount, 0)

    def test_daily_budget_target_distributes_planned_amount_evenly(self):
        # 1000 planned over N days
        expected = round(Decimal("1000.00") / Decimal(self.budget.days_total), 2)
        self.assertEqual(self.budget.daily_budget_target, expected)

    def test_daily_average_spent_zero_when_no_days_elapsed(self):
        # Future budget: not started yet
        future_start = date.today() + timedelta(days=10)
        future = Budget.objects.create(
            user=self.user,
            category=self.make_expense_category(self.user, name="Lazer"),
            name="Futuro",
            planned_amount=Decimal("300.00"),
            start_date=future_start,
            end_date=future_start + timedelta(days=29),
        )
        self.assertEqual(future.daily_average_spent, Decimal("0.00"))
        self.assertEqual(future.daily_progress_percentage, Decimal("0.00"))

    def test_daily_progress_percentage_reflects_pace(self):
        # Spend exactly the daily target -> 100%
        target = self.budget.daily_budget_target
        days = self.budget.days_elapsed
        if days <= 0:
            self.skipTest("Budget period has not started yet")
        self.make_expense(
            self.user, self.account, self.parent_cat,
            (target * days),
        )
        self.budget.refresh_from_db()
        self.budget.clear_cache()
        # Allow rounding tolerance of 1pp
        self.assertAlmostEqual(
            float(self.budget.daily_progress_percentage), 100.0, delta=1.0,
        )


class BudgetSignalTests(BudgetTestMixin, TestCase):
    """Cache invalidation driven by Transaction signals."""

    def setUp(self):
        self.user = self.make_user()
        self.account = self.make_account(self.user)
        self.category = self.make_expense_category(self.user)
        self.budget = self.make_budget(
            self.user, self.category, planned_amount=Decimal("400.00"),
        )

    def test_transaction_create_refreshes_cache(self):
        self.make_expense(self.user, self.account, self.category, "150.00")
        self.budget.refresh_from_db()
        # Signal should have updated the cache directly
        self.assertEqual(self.budget._cached_spent_amount, Decimal("150.00"))

    def test_transaction_update_refreshes_cache(self):
        tx = self.make_expense(self.user, self.account, self.category, "100.00")
        tx.amount = Decimal("250.00")
        tx.save()
        self.budget.refresh_from_db()
        self.assertEqual(self.budget._cached_spent_amount, Decimal("250.00"))

    def test_transaction_delete_refreshes_cache(self):
        tx = self.make_expense(self.user, self.account, self.category, "100.00")
        self.budget.refresh_from_db()
        self.assertEqual(self.budget._cached_spent_amount, Decimal("100.00"))

        tx.delete()
        self.budget.refresh_from_db()
        self.assertEqual(self.budget._cached_spent_amount, Decimal("0.00"))

    def test_signal_updates_parent_budget_when_subcategory_transaction_created(self):
        """Regression test: subcategory transactions must refresh parent budget cache."""
        parent = self.make_expense_category(self.user, name="Transporte")
        child = self.make_expense_category(self.user, name="Combustível", parent=parent)
        # Replace setUp budget with one bound to parent category
        self.budget.delete()
        parent_budget = self.make_budget(
            self.user, parent, planned_amount=Decimal("600.00"),
        )

        # Spending happens on the SUBCATEGORY
        self.make_expense(self.user, self.account, child, "200.00")

        parent_budget.refresh_from_db()
        # Cache must reflect the spend on the subcategory
        self.assertEqual(parent_budget._cached_spent_amount, Decimal("200.00"))

    def test_income_transaction_does_not_affect_budget(self):
        income_cat = Category.objects.create(
            user=self.user, name="Salário", category_type="INCOME",
        )
        Transaction.objects.create(
            user=self.user,
            account=self.account,
            category=income_cat,
            transaction_type="INCOME",
            amount=Decimal("3000.00"),
            description="Salário mensal",
            transaction_date=date.today(),
        )
        self.budget.refresh_from_db()
        # spent_amount must remain 0 — income does not consume an EXPENSE budget
        self.budget.clear_cache()
        self.assertEqual(self.budget.spent_amount, Decimal("0.00"))


class BudgetViewIsolationTests(BudgetTestMixin, TestCase):
    """User data isolation across all budget views."""

    def setUp(self):
        self.alice = self.make_user(suffix="-alice")
        self.bob = self.make_user(suffix="-bob")
        self.alice_cat = self.make_expense_category(self.alice)
        self.bob_cat = self.make_expense_category(self.bob)
        self.alice_budget = self.make_budget(self.alice, self.alice_cat)
        self.bob_budget = self.make_budget(self.bob, self.bob_cat)

    def test_list_view_only_shows_own_budgets(self):
        self.client.force_login(self.alice)
        resp = self.client.get(reverse("budgets:list"))
        self.assertEqual(resp.status_code, 200)
        budgets = list(resp.context["budgets"])
        self.assertIn(self.alice_budget, budgets)
        self.assertNotIn(self.bob_budget, budgets)

    def test_detail_view_blocks_other_users_budgets(self):
        self.client.force_login(self.alice)
        resp = self.client.get(reverse("budgets:detail", args=[self.bob_budget.pk]))
        self.assertEqual(resp.status_code, 404)

    def test_update_view_blocks_other_users_budgets(self):
        self.client.force_login(self.alice)
        resp = self.client.get(reverse("budgets:update", args=[self.bob_budget.pk]))
        self.assertEqual(resp.status_code, 404)

    def test_delete_view_blocks_other_users_budgets(self):
        self.client.force_login(self.alice)
        resp = self.client.get(reverse("budgets:delete", args=[self.bob_budget.pk]))
        self.assertEqual(resp.status_code, 404)

    def test_create_view_assigns_request_user(self):
        self.client.force_login(self.alice)
        first, last = _month_range()
        new_cat = self.make_expense_category(self.alice, name="Lazer")
        resp = self.client.post(
            reverse("budgets:create"),
            data={
                "category": new_cat.pk,
                "name": "Lazer Mensal",
                "planned_amount": "200.00",
                "start_date": first.isoformat(),
                "end_date": last.isoformat(),
                "is_active": "on",
            },
        )
        self.assertIn(resp.status_code, (302, 200))  # redirect on success
        budget = Budget.objects.filter(name="Lazer Mensal").first()
        self.assertIsNotNone(budget)
        self.assertEqual(budget.user, self.alice)

    def test_anonymous_user_redirected_from_list(self):
        resp = self.client.get(reverse("budgets:list"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login", resp.url)


class MonthlyBudgetViewTests(BudgetTestMixin, TestCase):
    """Bulk monthly editor: create/update/delete in one submission."""

    def setUp(self):
        self.user = self.make_user()
        self.account = self.make_account(self.user)
        self.food = self.make_expense_category(self.user, name="Alimentação")
        self.transport = self.make_expense_category(self.user, name="Transporte")
        self.client.force_login(self.user)
        first, last = _month_range()
        self.year, self.month = first.year, first.month
        self.first, self.last = first, last

    def _post_url(self):
        return reverse("budgets:monthly_for", args=[self.year, self.month])

    def _field(self, category):
        return f"planned_amount_{category.id}"

    def test_get_renders_one_row_per_active_expense_category(self):
        resp = self.client.get(reverse("budgets:monthly"))
        self.assertEqual(resp.status_code, 200)
        rows = resp.context["rows"]
        category_ids = {r["category"].id for r in rows}
        self.assertIn(self.food.id, category_ids)
        self.assertIn(self.transport.id, category_ids)

    def test_get_excludes_income_and_inactive_categories(self):
        Category.objects.create(
            user=self.user, name="Salário", category_type="INCOME",
        )
        inactive = self.make_expense_category(self.user, name="Antigo")
        inactive.is_active = False
        inactive.save()

        resp = self.client.get(reverse("budgets:monthly"))
        ids = {r["category"].id for r in resp.context["rows"]}
        self.assertNotIn(inactive.id, ids)
        # income categories should also not appear
        self.assertEqual(
            len([c for c in ids if Category.objects.get(pk=c).category_type != "EXPENSE"]),
            0,
        )

    def test_post_creates_budgets_for_filled_rows_only(self):
        resp = self.client.post(self._post_url(), data={
            self._field(self.food): "500.00",
            self._field(self.transport): "",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Budget.objects.filter(user=self.user, category=self.food).count(), 1)
        self.assertEqual(Budget.objects.filter(user=self.user, category=self.transport).count(), 0)

    def test_post_updates_existing_budget(self):
        existing = self.make_budget(
            self.user, self.food,
            planned_amount=Decimal("400.00"),
            start_date=self.first, end_date=self.last,
        )
        self.client.post(self._post_url(), data={
            self._field(self.food): "650.00",
            self._field(self.transport): "",
        })
        existing.refresh_from_db()
        self.assertEqual(existing.planned_amount, Decimal("650.00"))

    def test_post_removes_empty_budget_with_no_spending(self):
        budget = self.make_budget(
            self.user, self.food,
            planned_amount=Decimal("400.00"),
            start_date=self.first, end_date=self.last,
        )
        self.client.post(self._post_url(), data={
            self._field(self.food): "",
            self._field(self.transport): "",
        })
        self.assertFalse(Budget.objects.filter(pk=budget.pk).exists())

    def test_post_keeps_empty_budget_when_spending_exists(self):
        budget = self.make_budget(
            self.user, self.food,
            planned_amount=Decimal("400.00"),
            start_date=self.first, end_date=self.last,
        )
        self.make_expense(self.user, self.account, self.food, "50.00")

        self.client.post(self._post_url(), data={
            self._field(self.food): "",
            self._field(self.transport): "",
        })
        # Budget must NOT be deleted because it already has spend recorded
        self.assertTrue(Budget.objects.filter(pk=budget.pk).exists())

    def test_post_rejects_negative_value_with_inline_error(self):
        resp = self.client.post(self._post_url(), data={
            self._field(self.food): "-10",
            self._field(self.transport): "",
        }, follow=False)
        # On error, view re-renders (200) instead of redirecting
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Budget.objects.filter(user=self.user).count(), 0)
        rows = resp.context["rows"]
        food_row = next(r for r in rows if r["category"].id == self.food.id)
        self.assertIsNotNone(food_row["error"])

    def test_post_rejects_invalid_decimal(self):
        resp = self.client.post(self._post_url(), data={
            self._field(self.food): "abc",
            self._field(self.transport): "",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Budget.objects.count(), 0)

    def test_does_not_leak_other_users_categories(self):
        other = self.make_user(suffix="2")
        other_cat = self.make_expense_category(other, name="OutroUser")
        resp = self.client.get(reverse("budgets:monthly"))
        ids = {r["category"].id for r in resp.context["rows"]}
        self.assertNotIn(other_cat.id, ids)

    def test_anonymous_redirected(self):
        self.client.logout()
        resp = self.client.get(reverse("budgets:monthly"))
        self.assertEqual(resp.status_code, 302)


class BudgetAlertTests(BudgetTestMixin, TestCase):
    """BudgetAlert creation, idempotency, ack and isolation."""

    def setUp(self):
        self.user = self.make_user()
        self.account = self.make_account(self.user)
        self.category = self.make_expense_category(self.user)
        self.budget = self.make_budget(
            self.user, self.category, planned_amount=Decimal("100.00"),
        )

    def test_alert_fires_on_70_percent_threshold(self):
        # 70% of 100 = 70
        self.make_expense(self.user, self.account, self.category, "70.00")
        alerts = list(BudgetAlert.objects.filter(budget=self.budget))
        thresholds = sorted(a.threshold for a in alerts)
        self.assertEqual(thresholds, [70])

    def test_alerts_fire_for_each_crossed_threshold(self):
        # 100% should create 70/90/100 alerts in a single transaction event
        self.make_expense(self.user, self.account, self.category, "100.00")
        thresholds = sorted(
            BudgetAlert.objects.filter(budget=self.budget).values_list("threshold", flat=True)
        )
        self.assertEqual(thresholds, [70, 90, 100])

    def test_alerts_are_idempotent(self):
        # First spend pushes to 75%
        self.make_expense(self.user, self.account, self.category, "75.00")
        # Second spend pushes to 95% (crosses 90 too); previous 70 alert should not duplicate
        self.make_expense(self.user, self.account, self.category, "20.00")

        thresholds = sorted(
            BudgetAlert.objects.filter(budget=self.budget).values_list("threshold", flat=True)
        )
        self.assertEqual(thresholds, [70, 90])
        # Exactly one alert per threshold
        self.assertEqual(BudgetAlert.objects.filter(budget=self.budget, threshold=70).count(), 1)

    def test_no_alert_below_first_threshold(self):
        # 50% — below 70
        self.make_expense(self.user, self.account, self.category, "50.00")
        self.assertFalse(BudgetAlert.objects.filter(budget=self.budget).exists())

    def test_alert_snapshots_spent_and_percentage(self):
        self.make_expense(self.user, self.account, self.category, "75.00")
        alert = BudgetAlert.objects.get(budget=self.budget, threshold=70)
        self.assertEqual(alert.spent_at_trigger, Decimal("75.00"))
        self.assertEqual(alert.percentage_at_trigger, Decimal("75.00"))

    def test_acknowledge_marks_alert_read(self):
        self.make_expense(self.user, self.account, self.category, "75.00")
        alert = BudgetAlert.objects.get(budget=self.budget, threshold=70)
        self.assertFalse(alert.is_acknowledged)
        alert.acknowledge()
        alert.refresh_from_db()
        self.assertTrue(alert.is_acknowledged)
        self.assertIsNotNone(alert.acknowledged_at)

    def test_acknowledge_is_idempotent(self):
        self.make_expense(self.user, self.account, self.category, "75.00")
        alert = BudgetAlert.objects.get(budget=self.budget, threshold=70)
        alert.acknowledge()
        first_ack = alert.acknowledged_at
        alert.acknowledge()  # second call should not change timestamp
        alert.refresh_from_db()
        self.assertEqual(alert.acknowledged_at, first_ack)

    def test_unacknowledged_manager_filters_correctly(self):
        self.make_expense(self.user, self.account, self.category, "75.00")
        a1 = BudgetAlert.objects.get(budget=self.budget, threshold=70)
        a1.acknowledge()
        # Push to 95% - new threshold fires
        self.make_expense(self.user, self.account, self.category, "20.00")

        unread = list(BudgetAlert.objects.unacknowledged_for_user(self.user))
        self.assertEqual(len(unread), 1)
        self.assertEqual(unread[0].threshold, 90)


class BudgetAlertViewTests(BudgetTestMixin, TestCase):
    """HTTP routes for listing and acknowledging alerts."""

    def setUp(self):
        self.user = self.make_user()
        self.account = self.make_account(self.user)
        self.category = self.make_expense_category(self.user)
        self.budget = self.make_budget(
            self.user, self.category, planned_amount=Decimal("100.00"),
        )
        self.client.force_login(self.user)
        # Trigger a 70% alert
        self.make_expense(self.user, self.account, self.category, "75.00")
        self.alert = BudgetAlert.objects.get(budget=self.budget, threshold=70)

    def test_alert_list_only_shows_own_alerts(self):
        # Other user's alert
        other = self.make_user(suffix="-bob")
        other_acc = self.make_account(other)
        other_cat = self.make_expense_category(other, name="Outro")
        other_budget = self.make_budget(other, other_cat, planned_amount=Decimal("100.00"))
        Transaction.objects.create(
            user=other, account=other_acc, category=other_cat,
            transaction_type="EXPENSE", amount=Decimal("80.00"),
            description="x", transaction_date=date.today(),
        )

        resp = self.client.get(reverse("budgets:alerts"))
        self.assertEqual(resp.status_code, 200)
        alerts = list(resp.context["alerts"])
        self.assertIn(self.alert, alerts)
        self.assertFalse(any(a.user == other for a in alerts))

    def test_ack_endpoint_marks_alert_read(self):
        resp = self.client.post(reverse("budgets:alert_ack", args=[self.alert.pk]))
        self.assertEqual(resp.status_code, 302)
        self.alert.refresh_from_db()
        self.assertTrue(self.alert.is_acknowledged)

    def test_ack_blocks_other_users_alerts(self):
        other = self.make_user(suffix="-bob")
        self.client.force_login(other)
        resp = self.client.post(reverse("budgets:alert_ack", args=[self.alert.pk]))
        self.assertEqual(resp.status_code, 404)
        self.alert.refresh_from_db()
        self.assertFalse(self.alert.is_acknowledged)

    def test_ack_all_acknowledges_every_unread(self):
        # Trigger two more thresholds
        self.make_expense(self.user, self.account, self.category, "30.00")
        self.assertEqual(
            BudgetAlert.objects.unacknowledged_for_user(self.user).count(), 3,
        )
        resp = self.client.post(reverse("budgets:alert_ack_all"))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(
            BudgetAlert.objects.unacknowledged_for_user(self.user).count(), 0,
        )
