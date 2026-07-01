"""
Test suite for the budgets app.

Coverage:
- Budget model validation and constraints
- Calculated properties (spent_amount, percentage_used, remaining_amount,
  daily_* metrics) including subcategory aggregation and period boundaries
- Signal-driven cache refresh on Transaction save/delete
- MonthlyPlan and MonthlyPlanItem model validation and KPIs
- Planning wizard views (entry, header, distribute, review, dashboard, copy)
- MonthlyPlan and MonthlyPlanItem REST API endpoints
"""

from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from accounts.models import Account
from budgets.models import Budget, BudgetAlert, MonthlyPlan, MonthlyPlanItem
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
            status="CONFIRMED",
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
            status="CONFIRMED",
        )
        self.budget.refresh_from_db()
        # spent_amount must remain 0 — income does not consume an EXPENSE budget
        self.budget.clear_cache()
        self.assertEqual(self.budget.spent_amount, Decimal("0.00"))


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
            status="CONFIRMED",
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


# ─────────────────────────────────────────────────────────────────────────────
# MonthlyPlan tests
# ─────────────────────────────────────────────────────────────────────────────

class MonthlyPlanTestMixin(BudgetTestMixin):
    """Shared helpers for MonthlyPlan tests."""

    @classmethod
    def make_income_category(cls, user, name="Salário"):
        return Category.objects.create(
            user=user,
            name=name,
            category_type="INCOME",
        )

    @classmethod
    def make_plan(cls, user, year=None, month=None, **overrides):
        today = date.today()
        defaults = dict(
            user=user,
            year=year or today.year,
            month=month or today.month,
            renda_prevista=Decimal("5000.00"),
            teto_despesas=Decimal("3000.00"),
            reserva_dividas=Decimal("500.00"),
            reserva_metas=Decimal("500.00"),
            reserva_investimentos=Decimal("500.00"),
        )
        defaults.update(overrides)
        plan = MonthlyPlan(**defaults)
        plan.save()
        return plan

    @classmethod
    def make_income(cls, user, account, category, amount, when=None):
        return Transaction.objects.create(
            user=user,
            account=account,
            category=category,
            transaction_type="INCOME",
            amount=Decimal(str(amount)),
            description=f"Receita {amount}",
            transaction_date=when or date.today(),
            status="CONFIRMED",
        )


class MonthlyPlanModelTests(MonthlyPlanTestMixin, TestCase):
    """Validation, constraints and calculated properties on MonthlyPlan."""

    def setUp(self):
        self.user = self.make_user()
        self.account = self.make_account(self.user)
        self.income_cat = self.make_income_category(self.user)
        self.expense_cat = self.make_expense_category(self.user)

    # ── creation & uniqueness ─────────────────────────────────────────────────

    def test_create_valid_plan(self):
        plan = self.make_plan(self.user)
        self.assertIsNotNone(plan.pk)
        self.assertEqual(str(plan), f"Plano {plan.month:02d}/{plan.year} — {self.user}")

    def test_duplicate_month_rejected(self):
        self.make_plan(self.user)
        from django.db import IntegrityError
        with self.assertRaises((IntegrityError, Exception)):
            self.make_plan(self.user)  # same user/year/month

    def test_different_users_same_month_allowed(self):
        other = self.make_user(suffix="2")
        self.make_plan(self.user)
        other_plan = self.make_plan(other)  # should not raise
        self.assertNotEqual(other_plan.user, self.user)

    def test_different_months_same_user_allowed(self):
        today = date.today()
        plan1 = self.make_plan(self.user, year=today.year, month=today.month)
        next_month = today.month % 12 + 1
        next_year = today.year + (1 if today.month == 12 else 0)
        plan2 = self.make_plan(self.user, year=next_year, month=next_month)
        self.assertNotEqual(plan1.month, plan2.month)

    # ── validation ────────────────────────────────────────────────────────────

    def test_reserves_exceeding_income_rejected(self):
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            self.make_plan(
                self.user,
                renda_prevista=Decimal("1000.00"),
                teto_despesas=Decimal("800.00"),
                reserva_dividas=Decimal("400.00"),  # 800+400 > 1000 → invalid
            )

    def test_negative_renda_rejected(self):
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            self.make_plan(
                self.user,
                renda_prevista=Decimal("-1.00"),
                teto_despesas=Decimal("0.00"),
            )

    def test_invalid_month_rejected(self):
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            self.make_plan(self.user, month=13)

    # ── planned side ─────────────────────────────────────────────────────────

    def test_sobra_planejada_calculation(self):
        plan = self.make_plan(
            self.user,
            renda_prevista=Decimal("5000.00"),
            teto_despesas=Decimal("3000.00"),
            reserva_dividas=Decimal("500.00"),
            reserva_metas=Decimal("200.00"),
            reserva_investimentos=Decimal("300.00"),
        )
        # 5000 - 3000 - 500 - 200 - 300 = 1000
        self.assertEqual(plan.sobra_planejada, Decimal("1000.00"))

    def test_total_reservas(self):
        plan = self.make_plan(
            self.user,
            renda_prevista=Decimal("5000.00"),
            teto_despesas=Decimal("3000.00"),
            reserva_dividas=Decimal("200.00"),
            reserva_metas=Decimal("300.00"),
            reserva_investimentos=Decimal("100.00"),
        )
        self.assertEqual(plan.total_reservas, Decimal("600.00"))

    # ── realised side (live from transactions) ────────────────────────────────

    def test_renda_realizada_sums_income_in_period(self):
        plan = self.make_plan(self.user)
        self.make_income(self.user, self.account, self.income_cat, "2000.00")
        self.make_income(self.user, self.account, self.income_cat, "1500.00")
        self.assertEqual(plan.renda_realizada, Decimal("3500.00"))

    def test_despesas_realizadas_sums_expenses_in_period(self):
        plan = self.make_plan(self.user)
        self.make_expense(self.user, self.account, self.expense_cat, "400.00")
        self.make_expense(self.user, self.account, self.expense_cat, "200.00")
        self.assertEqual(plan.despesas_realizadas, Decimal("600.00"))

    def test_transactions_outside_period_excluded(self):
        plan = self.make_plan(self.user)
        outside = plan.period_start - timedelta(days=1)
        self.make_expense(self.user, self.account, self.expense_cat, "999.00", when=outside)
        self.assertEqual(plan.despesas_realizadas, Decimal("0.00"))

    def test_other_users_transactions_excluded(self):
        plan = self.make_plan(self.user)
        other = self.make_user(suffix="2")
        other_acc = self.make_account(other)
        other_cat = self.make_expense_category(other)
        self.make_expense(other, other_acc, other_cat, "999.00")
        self.assertEqual(plan.despesas_realizadas, Decimal("0.00"))

    def test_saldo_disponivel(self):
        plan = self.make_plan(self.user)
        self.make_income(self.user, self.account, self.income_cat, "4000.00")
        self.make_expense(self.user, self.account, self.expense_cat, "1500.00")
        self.assertEqual(plan.saldo_disponivel, Decimal("2500.00"))

    # ── KPIs ─────────────────────────────────────────────────────────────────

    def test_percentual_consumido_zero_when_no_expenses(self):
        plan = self.make_plan(self.user)
        self.assertEqual(plan.percentual_consumido, Decimal("0.00"))

    def test_percentual_consumido_correct(self):
        plan = self.make_plan(
            self.user,
            renda_prevista=Decimal("5000.00"),
            teto_despesas=Decimal("2000.00"),
            reserva_dividas=Decimal("0.00"),
            reserva_metas=Decimal("0.00"),
            reserva_investimentos=Decimal("0.00"),
        )
        self.make_expense(self.user, self.account, self.expense_cat, "1000.00")
        self.assertEqual(plan.percentual_consumido, Decimal("50.00"))

    def test_status_ok_when_below_80(self):
        plan = self.make_plan(
            self.user,
            renda_prevista=Decimal("5000.00"),
            teto_despesas=Decimal("2000.00"),
            reserva_dividas=Decimal("0.00"),
            reserva_metas=Decimal("0.00"),
            reserva_investimentos=Decimal("0.00"),
        )
        self.make_expense(self.user, self.account, self.expense_cat, "500.00")
        self.assertEqual(plan.health_status, "ok")

    def test_status_atencao_at_80_percent(self):
        plan = self.make_plan(
            self.user,
            renda_prevista=Decimal("5000.00"),
            teto_despesas=Decimal("1000.00"),
            reserva_dividas=Decimal("0.00"),
            reserva_metas=Decimal("0.00"),
            reserva_investimentos=Decimal("0.00"),
        )
        self.make_expense(self.user, self.account, self.expense_cat, "800.00")
        self.assertEqual(plan.health_status, "atencao")

    def test_status_critico_at_100_percent(self):
        plan = self.make_plan(
            self.user,
            renda_prevista=Decimal("5000.00"),
            teto_despesas=Decimal("1000.00"),
            reserva_dividas=Decimal("0.00"),
            reserva_metas=Decimal("0.00"),
            reserva_investimentos=Decimal("0.00"),
        )
        self.make_expense(self.user, self.account, self.expense_cat, "1000.00")
        self.assertEqual(plan.health_status, "critico")

    def test_limite_diario_recomendado_zero_when_no_days_remaining(self):
        past = date.today() - timedelta(days=40)
        plan = self.make_plan(self.user, year=past.year, month=past.month)
        self.assertEqual(plan.limite_diario_recomendado, Decimal("0.00"))

    def test_limite_diario_recomendado_current_month(self):
        plan = self.make_plan(
            self.user,
            renda_prevista=Decimal("5000.00"),
            teto_despesas=Decimal("3000.00"),
            reserva_dividas=Decimal("0.00"),
            reserva_metas=Decimal("0.00"),
            reserva_investimentos=Decimal("0.00"),
        )
        # No spending → remaining = teto_despesas
        if plan.days_remaining > 0:
            expected = round(Decimal("3000.00") / Decimal(plan.days_remaining), 2)
            self.assertEqual(plan.limite_diario_recomendado, expected)

    # ── period helpers ────────────────────────────────────────────────────────

    def test_period_start_is_first_day_of_month(self):
        plan = self.make_plan(self.user, year=2026, month=5)
        self.assertEqual(plan.period_start, date(2026, 5, 1))

    def test_period_end_is_last_day_of_month(self):
        plan = self.make_plan(self.user, year=2026, month=2)
        self.assertEqual(plan.period_end, date(2026, 2, 28))

    def test_get_or_none_returns_none_when_missing(self):
        result = MonthlyPlan.get_or_none(self.user, 2099, 1)
        self.assertIsNone(result)

    def test_get_or_none_returns_plan_when_exists(self):
        plan = self.make_plan(self.user)
        found = MonthlyPlan.get_or_none(self.user, plan.year, plan.month)
        self.assertEqual(found.pk, plan.pk)




# =============================================================================
# Sprint 7 — MonthlyPlanItem model tests
# =============================================================================

class MonthlyPlanItemModelTests(MonthlyPlanTestMixin, TestCase):
    """MonthlyPlanItem validation, constraints and spent_amount calculation."""

    def setUp(self):
        self.user = self.make_user()
        self.other = self.make_user(suffix="2")
        self.account = self.make_account(self.user)
        self.parent_cat = self.make_expense_category(self.user, name="Alimentação")
        self.child_cat = Category.objects.create(
            user=self.user,
            name="Supermercado",
            category_type="EXPENSE",
            parent=self.parent_cat,
        )
        self.income_cat = Category.objects.create(
            user=self.user,
            name="Salário",
            category_type="INCOME",
        )
        today = date.today()
        self.plan = MonthlyPlan.objects.create(
            user=self.user,
            year=today.year,
            month=today.month,
            renda_prevista=Decimal("5000.00"),
            teto_despesas=Decimal("3000.00"),
            savings_goal=Decimal("500.00"),
        )

    def _make_item(self, category=None, amount="500.00"):
        return MonthlyPlanItem.objects.create(
            monthly_plan=self.plan,
            category=category or self.parent_cat,
            planned_amount=Decimal(amount),
        )

    def _make_tx(self, category, amount, delta_days=0):
        tx_date = date(self.plan.year, self.plan.month, 1)
        return Transaction.objects.create(
            user=self.user,
            account=self.account,
            category=category,
            transaction_type="EXPENSE",
            amount=Decimal(amount),
            description="Test",
            transaction_date=tx_date,
            status="CONFIRMED",
        )

    def test_create_valid_item(self):
        item = self._make_item()
        self.assertEqual(item.monthly_plan, self.plan)
        self.assertEqual(item.category, self.parent_cat)
        self.assertEqual(item.planned_amount, Decimal("500.00"))

    def test_income_category_rejected(self):
        with self.assertRaises(ValidationError):
            MonthlyPlanItem(
                monthly_plan=self.plan,
                category=self.income_cat,
                planned_amount=Decimal("100.00"),
            ).full_clean()

    def test_income_category_rejected_on_save(self):
        with self.assertRaises(ValidationError):
            MonthlyPlanItem.objects.create(
                monthly_plan=self.plan,
                category=self.income_cat,
                planned_amount=Decimal("100.00"),
            )

    def test_inactive_category_rejected_on_save(self):
        inactive = Category.objects.create(
            user=self.user,
            name="Despesa Inativa",
            category_type="EXPENSE",
            is_active=False,
        )

        with self.assertRaises(ValidationError):
            MonthlyPlanItem.objects.create(
                monthly_plan=self.plan,
                category=inactive,
                planned_amount=Decimal("100.00"),
            )

    def test_duplicate_item_rejected(self):
        self._make_item()
        from django.db import IntegrityError
        with self.assertRaises((IntegrityError, ValidationError)):
            MonthlyPlanItem.objects.create(
                monthly_plan=self.plan,
                category=self.parent_cat,
                planned_amount=Decimal("200.00"),
            )

    def test_spent_amount_sums_direct_transactions(self):
        item = self._make_item(self.parent_cat, "500.00")
        self._make_tx(self.parent_cat, "150.00")
        self._make_tx(self.parent_cat, "100.00")
        self.assertEqual(item.spent_amount, Decimal("250.00"))

    def test_spent_amount_includes_subcategory_transactions(self):
        item = self._make_item(self.parent_cat, "500.00")
        self._make_tx(self.child_cat, "200.00")
        self.assertEqual(item.spent_amount, Decimal("200.00"))

    def test_spent_amount_includes_direct_parent_and_child_transactions(self):
        item = self._make_item(self.parent_cat, "500.00")
        self._make_tx(self.parent_cat, "100.00")
        self._make_tx(self.child_cat, "150.00")
        self.assertEqual(item.spent_amount, Decimal("250.00"))

    def test_spent_amount_excludes_other_months(self):
        item = self._make_item(self.parent_cat, "500.00")
        other_month = date(self.plan.year, self.plan.month, 1) - timedelta(days=1)
        Transaction.objects.create(
            user=self.user,
            account=self.account,
            category=self.parent_cat,
            transaction_type="EXPENSE",
            amount=Decimal("300.00"),
            description="Other month",
            transaction_date=other_month,
            status="CONFIRMED",
        )
        self.assertEqual(item.spent_amount, Decimal("0.00"))

    def test_percentage_used_calculation(self):
        item = self._make_item(self.parent_cat, "500.00")
        self._make_tx(self.parent_cat, "250.00")
        self.assertEqual(item.percentage_used, Decimal("50.00"))

    def test_is_over_budget_when_spent_exceeds_planned(self):
        item = self._make_item(self.parent_cat, "100.00")
        self._make_tx(self.parent_cat, "150.00")
        self.assertTrue(item.is_over_budget)

    def test_alert_threshold_must_be_0_to_100(self):
        with self.assertRaises(ValidationError):
            MonthlyPlanItem(
                monthly_plan=self.plan,
                category=self.parent_cat,
                planned_amount=Decimal("100.00"),
                alert_threshold=101,
            ).full_clean()


# =============================================================================
# Sprint 7 — Planning wizard view tests
# =============================================================================

class PlanningWizardViewTests(MonthlyPlanTestMixin, TestCase):
    """HTTP-level tests for the planning wizard views."""

    def setUp(self):
        self.user = self.make_user()
        self.other = self.make_user(suffix="2")
        self.account = self.make_account(self.user)
        self.expense_cat = self.make_expense_category(self.user, name="Alimentação")
        self.client.force_login(self.user)
        self.today = date.today()
        self.year = self.today.year
        self.month = self.today.month

    def _make_plan(self, status="DRAFT", user=None):
        u = user or self.user
        return MonthlyPlan.objects.create(
            user=u,
            year=self.year,
            month=self.month,
            renda_prevista=Decimal("5000.00"),
            teto_despesas=Decimal("3000.00"),
            savings_goal=Decimal("500.00"),
            status=status,
        )

    def _previous_month(self):
        prev_month = self.month - 1 if self.month > 1 else 12
        prev_year = self.year if self.month > 1 else self.year - 1
        return prev_year, prev_month

    def _make_child_category(self, parent, name="Mercado"):
        return Category.objects.create(
            user=self.user,
            name=name,
            category_type="EXPENSE",
            parent=parent,
        )

    def _bulk_create_legacy_item(self, plan, category, amount):
        MonthlyPlanItem.objects.bulk_create([
            MonthlyPlanItem(
                monthly_plan=plan,
                category=category,
                planned_amount=Decimal(amount),
            )
        ])

    def _entry_url(self):
        return reverse("budgets:planning_entry")

    def _header_url(self):
        return reverse("budgets:planning_header")

    def _distribute_url(self):
        return reverse("budgets:planning_distribute", kwargs={"year": self.year, "month": self.month})

    def _review_url(self):
        return reverse("budgets:planning_review", kwargs={"year": self.year, "month": self.month})

    def _dashboard_url(self):
        return reverse("budgets:planning_dashboard", kwargs={"year": self.year, "month": self.month})

    def test_entry_view_returns_200_when_no_plan(self):
        resp = self.client.get(self._entry_url())
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, self._dashboard_url(), fetch_redirect_response=False)

    def test_entry_view_redirects_to_dashboard_when_active_plan_exists(self):
        self._make_plan(status="ACTIVE")
        resp = self.client.get(self._entry_url())
        self.assertRedirects(resp, self._dashboard_url(), fetch_redirect_response=False)

    def test_entry_view_redirects_to_distribute_when_draft_exists(self):
        self._make_plan(status="DRAFT")
        resp = self.client.get(self._entry_url())
        self.assertRedirects(resp, self._dashboard_url(), fetch_redirect_response=False)

    def test_header_view_get_returns_200(self):
        resp = self.client.get(self._header_url())
        self.assertEqual(resp.status_code, 200)

    def test_header_view_post_creates_draft_plan(self):
        resp = self.client.post(self._header_url(), {
            "renda_prevista": "5000.00",
            "savings_goal": "500.00",
            "teto_despesas": "3000.00",
            "reserva_dividas": "0.00",
            "reserva_metas": "0.00",
            "reserva_investimentos": "0.00",
            "notes": "",
        })
        self.assertEqual(resp.status_code, 302)
        plan = MonthlyPlan.objects.filter(user=self.user, year=self.year, month=self.month).first()
        self.assertIsNotNone(plan)
        self.assertEqual(plan.status, "DRAFT")

    def test_header_view_post_updates_existing_plan(self):
        self._make_plan()
        self.client.post(self._header_url(), {
            "renda_prevista": "6000.00",
            "savings_goal": "600.00",
            "teto_despesas": "3500.00",
            "reserva_dividas": "0.00",
            "reserva_metas": "0.00",
            "reserva_investimentos": "0.00",
            "notes": "",
        })
        self.assertEqual(MonthlyPlan.objects.filter(user=self.user).count(), 1)
        plan = MonthlyPlan.objects.get(user=self.user, year=self.year, month=self.month)
        self.assertEqual(plan.renda_prevista, Decimal("6000.00"))

    def test_distribute_view_get_returns_200(self):
        self._make_plan()
        resp = self.client.get(self._distribute_url())
        self.assertEqual(resp.status_code, 200)

    def test_distribute_view_post_creates_items(self):
        plan = self._make_plan()
        resp = self.client.post(self._distribute_url(), {
            f"amount_{self.expense_cat.pk}": "400.00",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(
            MonthlyPlanItem.objects.filter(monthly_plan=plan, category=self.expense_cat).exists()
        )

    def test_review_view_get_returns_200(self):
        plan = self._make_plan()
        MonthlyPlanItem.objects.create(
            monthly_plan=plan, category=self.expense_cat, planned_amount=Decimal("400.00")
        )
        resp = self.client.get(self._review_url())
        self.assertEqual(resp.status_code, 200)

    def test_review_view_post_activates_plan(self):
        plan = self._make_plan()
        MonthlyPlanItem.objects.create(
            monthly_plan=plan, category=self.expense_cat, planned_amount=Decimal("400.00")
        )
        self.client.post(self._review_url(), {})
        plan.refresh_from_db()
        self.assertEqual(plan.status, "ACTIVE")

    def test_dashboard_view_get_returns_200(self):
        self._make_plan(status="ACTIVE")
        resp = self.client.get(self._dashboard_url())
        self.assertEqual(resp.status_code, 200)

    def test_dashboard_view_shows_empty_state_when_no_plan(self):
        resp = self.client.get(self._dashboard_url())
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Nenhum planejamento para este mês')

    def test_copy_view_copies_items_from_previous_month(self):
        prev_month = self.month - 1 if self.month > 1 else 12
        prev_year = self.year if self.month > 1 else self.year - 1
        prev_plan = MonthlyPlan.objects.create(
            user=self.user, year=prev_year, month=prev_month,
            renda_prevista=Decimal("5000.00"), teto_despesas=Decimal("3000.00"),
            savings_goal=Decimal("500.00"),
        )
        MonthlyPlanItem.objects.create(
            monthly_plan=prev_plan, category=self.expense_cat, planned_amount=Decimal("400.00")
        )
        new_plan = self._make_plan()
        copy_url = reverse("budgets:planning_copy", kwargs={"year": self.year, "month": self.month})
        self.client.post(copy_url)
        self.assertTrue(
            MonthlyPlanItem.objects.filter(monthly_plan=new_plan, category=self.expense_cat).exists()
        )

    def test_copy_view_ignores_income_and_hidden_parent_items(self):
        prev_year, prev_month = self._previous_month()
        parent = self.make_expense_category(self.user, name="Alimentação Pai")
        child = self._make_child_category(parent, name="Supermercado")
        income = self.make_income_category(self.user, name="Salário")
        prev_plan = MonthlyPlan.objects.create(
            user=self.user,
            year=prev_year,
            month=prev_month,
            renda_prevista=Decimal("5000.00"),
            teto_despesas=Decimal("3000.00"),
            savings_goal=Decimal("500.00"),
        )
        self._bulk_create_legacy_item(prev_plan, income, "5000.00")
        self._bulk_create_legacy_item(prev_plan, parent, "900.00")
        MonthlyPlanItem.objects.create(
            monthly_plan=prev_plan,
            category=child,
            planned_amount=Decimal("400.00"),
        )
        new_plan = self._make_plan()
        copy_url = reverse(
            "budgets:planning_copy",
            kwargs={"year": self.year, "month": self.month},
        )

        self.client.post(copy_url)

        copied_categories = set(
            MonthlyPlanItem.objects.filter(monthly_plan=new_plan)
            .values_list("category_id", flat=True)
        )
        self.assertEqual(copied_categories, {child.pk})

    def test_distribute_validation_ignores_legacy_income_and_hidden_parent_items(self):
        parent = self.make_expense_category(self.user, name="Moradia")
        child = self._make_child_category(parent, name="Condomínio")
        income = self.make_income_category(self.user, name="Salário")
        plan = self._make_plan(status="ACTIVE")
        self._bulk_create_legacy_item(plan, income, "5000.00")
        self._bulk_create_legacy_item(plan, parent, "900.00")

        resp = self.client.post(self._distribute_url(), {
            "visible_categories": str(child.pk),
            f"amount_{child.pk}": "400.00",
        })

        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, self._review_url(), fetch_redirect_response=False)
        plan.refresh_from_db()
        self.assertEqual(plan.status, "ACTIVE")
        self.assertTrue(
            MonthlyPlanItem.objects.filter(
                monthly_plan=plan,
                category=child,
                planned_amount=Decimal("400.00"),
            ).exists()
        )

    def test_distribute_validation_ignores_hidden_grandchild_items(self):
        root = self.make_expense_category(self.user, name="Moradia")
        child = self._make_child_category(root, name="Casa")
        grandchild = self._make_child_category(child, name="Condomínio")
        plan = self._make_plan(status="ACTIVE")
        self._bulk_create_legacy_item(plan, grandchild, "5000.00")

        resp = self.client.post(self._distribute_url(), {
            "visible_categories": str(child.pk),
            f"amount_{child.pk}": "400.00",
        })

        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, self._review_url(), fetch_redirect_response=False)
        self.assertTrue(
            MonthlyPlanItem.objects.filter(
                monthly_plan=plan,
                category=child,
                planned_amount=Decimal("400.00"),
            ).exists()
        )

    def test_distribute_view_ignores_crafted_hidden_grandchild_submission(self):
        root = self.make_expense_category(self.user, name="Moradia")
        child = self._make_child_category(root, name="Casa")
        grandchild = self._make_child_category(child, name="Condomínio")
        plan = self._make_plan(status="ACTIVE")

        resp = self.client.post(self._distribute_url(), {
            "visible_categories": str(child.pk),
            f"amount_{child.pk}": "400.00",
            f"amount_{grandchild.pk}": "400.00",
        })

        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, self._review_url(), fetch_redirect_response=False)
        self.assertTrue(
            MonthlyPlanItem.objects.filter(
                monthly_plan=plan,
                category=child,
                planned_amount=Decimal("400.00"),
            ).exists()
        )
        self.assertFalse(
            MonthlyPlanItem.objects.filter(
                monthly_plan=plan,
                category=grandchild,
            ).exists()
        )

    def test_distribute_view_does_not_delete_hidden_item_from_crafted_zero_submission(self):
        root = self.make_expense_category(self.user, name="Moradia")
        child = self._make_child_category(root, name="Casa")
        grandchild = self._make_child_category(child, name="Condomínio")
        plan = self._make_plan(status="ACTIVE")
        self._bulk_create_legacy_item(plan, grandchild, "500.00")

        resp = self.client.post(self._distribute_url(), {
            "visible_categories": str(child.pk),
            f"amount_{child.pk}": "400.00",
            f"amount_{grandchild.pk}": "0.00",
        })

        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, self._review_url(), fetch_redirect_response=False)
        self.assertTrue(
            MonthlyPlanItem.objects.filter(
                monthly_plan=plan,
                category=child,
                planned_amount=Decimal("400.00"),
            ).exists()
        )
        self.assertTrue(
            MonthlyPlanItem.objects.filter(
                monthly_plan=plan,
                category=grandchild,
                planned_amount=Decimal("500.00"),
            ).exists()
        )

    def test_distribute_view_ignores_hidden_visible_id_without_amount_field(self):
        root = self.make_expense_category(self.user, name="Moradia")
        child = self._make_child_category(root, name="Casa")
        grandchild = self._make_child_category(child, name="Condomínio")
        plan = self._make_plan(status="ACTIVE")
        self._bulk_create_legacy_item(plan, grandchild, "500.00")

        resp = self.client.post(self._distribute_url(), {
            "visible_categories": f"{child.pk},{grandchild.pk}",
            f"amount_{child.pk}": "400.00",
        })

        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, self._review_url(), fetch_redirect_response=False)
        self.assertTrue(
            MonthlyPlanItem.objects.filter(
                monthly_plan=plan,
                category=child,
                planned_amount=Decimal("400.00"),
            ).exists()
        )
        self.assertTrue(
            MonthlyPlanItem.objects.filter(
                monthly_plan=plan,
                category=grandchild,
                planned_amount=Decimal("500.00"),
            ).exists()
        )

    def test_distribute_validation_ignores_active_child_under_inactive_root(self):
        inactive_root = self.make_expense_category(self.user, name="Moradia")
        inactive_root.is_active = False
        inactive_root.save(update_fields=["is_active"])
        hidden_child = self._make_child_category(inactive_root, name="Condomínio")
        visible_root = self.make_expense_category(self.user, name="Transporte")
        plan = self._make_plan(status="ACTIVE")
        self._bulk_create_legacy_item(plan, hidden_child, "5000.00")

        resp = self.client.post(self._distribute_url(), {
            "visible_categories": str(visible_root.pk),
            f"amount_{visible_root.pk}": "400.00",
        })

        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, self._review_url(), fetch_redirect_response=False)
        self.assertTrue(
            MonthlyPlanItem.objects.filter(
                monthly_plan=plan,
                category=visible_root,
                planned_amount=Decimal("400.00"),
            ).exists()
        )

    def test_anonymous_user_redirected(self):
        self.client.logout()
        resp = self.client.get(self._entry_url())
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login", resp.url)

    def test_other_user_cannot_access_plan(self):
        other_plan = self._make_plan(user=self.other)
        url = reverse("budgets:planning_distribute", kwargs={"year": self.year, "month": self.month})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 404)


# =============================================================================
# Sprint 7 — MonthlyPlan REST API tests
# =============================================================================

class MonthlyPlanAPITests(MonthlyPlanTestMixin, TestCase):
    """REST API tests for MonthlyPlan and MonthlyPlanItem endpoints."""

    def setUp(self):
        from rest_framework.authtoken.models import Token
        from rest_framework.test import APIClient
        self.user = self.make_user()
        self.other = self.make_user(suffix="2")
        self.account = self.make_account(self.user)
        self.expense_cat = self.make_expense_category(self.user, name="Alimentação")
        self.token = Token.objects.create(user=self.user)
        self.other_token = Token.objects.create(user=self.other)
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        self.today = date.today()
        self.plan = MonthlyPlan.objects.create(
            user=self.user,
            year=self.today.year,
            month=self.today.month,
            renda_prevista=Decimal("5000.00"),
            teto_despesas=Decimal("3000.00"),
            savings_goal=Decimal("500.00"),
            status="DRAFT",
        )
        self.item = MonthlyPlanItem.objects.create(
            monthly_plan=self.plan,
            category=self.expense_cat,
            planned_amount=Decimal("400.00"),
        )

    def _plan_url(self, pk=None, action=None):
        if action:
            return reverse(f"api-monthly-plan-{action}", kwargs={"pk": pk})
        if pk:
            return reverse("api-monthly-plan-detail", kwargs={"pk": pk})
        return reverse("api-monthly-plan-list")

    def _item_url(self, pk=None):
        if pk:
            return reverse("api-monthly-plan-item-detail", kwargs={"pk": pk})
        return reverse("api-monthly-plan-item-list")

    def test_list_returns_only_own_plans(self):
        MonthlyPlan.objects.create(
            user=self.other, year=self.today.year, month=self.today.month,
            renda_prevista=Decimal("4000.00"), teto_despesas=Decimal("2000.00"),
        )
        resp = self.client.get(self._plan_url())
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data["results"]), 1)
        self.assertEqual(resp.data["results"][0]["id"], self.plan.pk)

    def test_create_plan(self):
        resp = self.client.post(self._plan_url(), {
            "year": self.today.year,
            "month": self.today.month - 1 if self.today.month > 1 else 12,
            "renda_prevista": "4000.00",
            "teto_despesas": "2500.00",
            "savings_goal": "300.00",
            "reserva_dividas": "0.00",
            "reserva_metas": "0.00",
            "reserva_investimentos": "0.00",
        }, content_type="application/json")
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["renda_prevista"], "4000.00")

    def test_retrieve_plan_includes_kpis(self):
        resp = self.client.get(self._plan_url(pk=self.plan.pk))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("teto_calculado", resp.data)
        self.assertIn("status_display", resp.data)

    def test_activate_action_changes_status(self):
        resp = self.client.post(f"{self._plan_url(pk=self.plan.pk)}activate/")
        self.assertEqual(resp.status_code, 200)
        self.plan.refresh_from_db()
        self.assertEqual(self.plan.status, "ACTIVE")

    def test_activate_rejects_non_draft(self):
        self.plan.status = "ACTIVE"
        self.plan.save(update_fields=["status"])
        resp = self.client.post(f"{self._plan_url(pk=self.plan.pk)}activate/")
        self.assertEqual(resp.status_code, 400)

    def test_summary_action_includes_items(self):
        resp = self.client.get(f"{self._plan_url(pk=self.plan.pk)}summary/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("items", resp.data)
        self.assertEqual(len(resp.data["items"]), 1)

    def test_copy_from_previous_copies_items(self):
        prev_month = self.today.month - 1 if self.today.month > 1 else 12
        prev_year = self.today.year if self.today.month > 1 else self.today.year - 1
        prev_plan = MonthlyPlan.objects.create(
            user=self.user, year=prev_year, month=prev_month,
            renda_prevista=Decimal("5000.00"), teto_despesas=Decimal("3000.00"),
        )
        MonthlyPlanItem.objects.create(
            monthly_plan=prev_plan, category=self.expense_cat,
            planned_amount=Decimal("300.00"),
        )
        # Remove existing item from current plan to avoid unique constraint
        self.item.delete()
        resp = self.client.post(f"{self._plan_url(pk=self.plan.pk)}copy_from_previous/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["copied_items"], 1)

    def test_other_user_plan_returns_404(self):
        other_plan = MonthlyPlan.objects.create(
            user=self.other, year=self.today.year, month=self.today.month,
            renda_prevista=Decimal("4000.00"), teto_despesas=Decimal("2000.00"),
        )
        resp = self.client.get(self._plan_url(pk=other_plan.pk))
        self.assertEqual(resp.status_code, 404)

    def test_list_items_filtered_by_plan(self):
        resp = self.client.get(f"{self._item_url()}?monthly_plan={self.plan.pk}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data["results"]), 1)
        self.assertEqual(resp.data["results"][0]["id"], self.item.pk)

    def test_create_item(self):
        cat2 = self.make_expense_category(self.user, name="Transporte")
        resp = self.client.post(self._item_url(), {
            "monthly_plan": self.plan.pk,
            "category": cat2.pk,
            "planned_amount": "200.00",
        }, content_type="application/json")
        self.assertEqual(resp.status_code, 201)

    def test_item_response_includes_spent_amount(self):
        resp = self.client.get(self._item_url(pk=self.item.pk))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("spent_amount", resp.data)
        self.assertIn("percentage_used", resp.data)

    def test_unauthenticated_request_rejected(self):
        self.client.credentials()
        resp = self.client.get(self._plan_url())
        self.assertEqual(resp.status_code, 401)
