# Monthly Plan Editing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix monthly plan copying/editing so users can freely adjust the current month, including active plans, without hidden income or stale parent-category items blocking expense allocation.

**Architecture:** Keep `MonthlyPlan` as the monthly header and `MonthlyPlanItem` as expense allocation only. Add a small `budgets/plan_item_rules.py` module that centralizes "allocatable category" and safe copy/total logic, then use it from the web wizard and API. Keep production data cleanup explicit and separate from deploy.

**Tech Stack:** Django 5.2, Django TestCase, Django REST Framework, PostgreSQL in production, SQLite test DB locally.

---

## Spec

Use the approved spec: `docs/superpowers/specs/2026-07-01-monthly-plan-editing-design.md`.

Current known full-suite baseline: `./scripts/dj test` fails before this work in `core.tests.FrontendAssetTests.test_runtime_css_does_not_require_tailwind_build_step` because it expects deleted `static/css/custom.css`. Use targeted tests below for this bugfix, and do not claim the full suite is green unless that unrelated baseline is fixed separately.

## File Structure

- Modify: `budgets/models.py`
  - Strengthen `MonthlyPlanItem.clean()` for active expense categories.
  - Add `MonthlyPlanItem.save()` to call `full_clean()` for normal app saves.
- Create: `budgets/plan_item_rules.py`
  - Central rules for allocatable expense categories.
  - Safe copy from previous plan.
  - Safe allocated-total calculation.
- Modify: `budgets/views.py`
  - Use shared safe copy helper in `PlanningCopyView`.
  - Use shared allocated-total helper in `PlanningDistributeView`.
- Modify: `api/serializers.py`
  - Reject inactive and non-expense categories before model save.
- Modify: `api/views.py`
  - Use shared safe copy helper in `MonthlyPlanViewSet.copy_from_previous`.
- Modify: `budgets/tests.py`
  - Regression tests for model guard, web copy, distribution validation,
    active-plan editing, and monthly plan API item validation.

---

## Task 1: Model Guard For MonthlyPlanItem

**Files:**
- Modify: `budgets/tests.py`
- Modify: `budgets/models.py`

- [ ] **Step 1: Add failing model tests**

Add these tests inside `MonthlyPlanItemModelTests`, immediately after `test_income_category_rejected`:

```python
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
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
./scripts/dj test budgets.tests.MonthlyPlanItemModelTests.test_income_category_rejected_on_save budgets.tests.MonthlyPlanItemModelTests.test_inactive_category_rejected_on_save
```

Expected: both tests fail because `MonthlyPlanItem.objects.create()` currently bypasses `clean()`.

- [ ] **Step 3: Implement model validation**

In `budgets/models.py`, update `MonthlyPlanItem.clean()` to include inactive-category validation. Replace the `if self.category_id:` block with:

```python
        if self.category_id:
            try:
                if not self.category.is_active:
                    raise ValidationError(
                        {'category': 'Apenas categorias ativas podem ser planejadas.'}
                    )
                if self.category.category_type != 'EXPENSE':
                    raise ValidationError(
                        {'category': 'Apenas categorias de despesa podem ser planejadas.'}
                    )
                if self.monthly_plan_id and self.category.user != self.monthly_plan.user:
                    raise ValidationError(
                        {'category': 'A categoria deve pertencer ao mesmo usuário do plano.'}
                    )
            except (AttributeError, ObjectDoesNotExist):
                pass
```

Then add this method below `clean()`:

```python
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
```

- [ ] **Step 4: Run targeted model tests**

Run:

```bash
./scripts/dj test budgets.tests.MonthlyPlanItemModelTests
```

Expected: all `MonthlyPlanItemModelTests` pass.

- [ ] **Step 5: Commit**

```bash
git add budgets/models.py budgets/tests.py
git commit -m "fix: enforce monthly plan item category rules"
```

---

## Task 2: Shared Allocatable Category Rules

**Files:**
- Create: `budgets/plan_item_rules.py`
- Modify: `budgets/tests.py`

- [ ] **Step 1: Add failing web copy and distribution tests**

Add these helpers inside `PlanningWizardViewTests`:

```python
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
```

Add these tests after `test_copy_view_copies_items_from_previous_month`:

```python
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
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
./scripts/dj test budgets.tests.PlanningWizardViewTests.test_copy_view_ignores_income_and_hidden_parent_items budgets.tests.PlanningWizardViewTests.test_distribute_validation_ignores_legacy_income_and_hidden_parent_items
```

Expected: at least one test fails because the web copy currently copies every item and distribution validation currently sums root items without allocatable filtering.

- [ ] **Step 3: Create shared rule module**

Create `budgets/plan_item_rules.py`:

```python
from decimal import Decimal

from django.db.models import Sum

from categories.models import Category


def get_allocatable_expense_category_ids(user):
    """Return active expense category IDs editable in the distribution UI."""
    active_expense = Category.objects.filter(
        user=user,
        category_type='EXPENSE',
        is_active=True,
    )
    parent_ids_with_active_children = (
        active_expense
        .filter(parent_id__isnull=False)
        .values_list('parent_id', flat=True)
        .distinct()
    )
    return set(
        active_expense
        .exclude(parent_id__isnull=True, id__in=parent_ids_with_active_children)
        .values_list('id', flat=True)
    )


def get_allocated_expense_total(plan):
    """Sum only allocatable expense items for ceiling validation."""
    category_ids = get_allocatable_expense_category_ids(plan.user)
    total = (
        plan.items
        .filter(category_id__in=category_ids)
        .aggregate(total=Sum('planned_amount'))['total']
    )
    return total or Decimal('0.00')


def copy_allocatable_plan_items(source_plan, target_plan):
    """Copy only currently allocatable expense items from source to target."""
    category_ids = get_allocatable_expense_category_ids(target_plan.user)
    copied = 0
    source_items = (
        source_plan.items
        .select_related('category')
        .filter(category_id__in=category_ids)
    )
    for src_item in source_items:
        _, created = target_plan.items.get_or_create(
            category=src_item.category,
            defaults={
                'planned_amount': src_item.planned_amount,
                'alert_threshold': src_item.alert_threshold,
            },
        )
        if created:
            copied += 1
    return copied
```

- [ ] **Step 4: Run helper import smoke test**

Run:

```bash
./scripts/dj shell -c "from budgets.plan_item_rules import get_allocatable_expense_category_ids, get_allocated_expense_total, copy_allocatable_plan_items; print('ok')"
```

Expected output includes:

```text
ok
```

- [ ] **Step 5: Leave tests red until Task 3**

Do not commit at this point. The tests added in this task are intentionally red
until `budgets/views.py` uses the shared helpers in Task 3.

---

## Task 3: Apply Shared Rules To Web Wizard

**Files:**
- Modify: `budgets/views.py`

- [ ] **Step 1: Import shared helpers**

In `budgets/views.py`, add this import near the existing local imports:

```python
from .plan_item_rules import (
    copy_allocatable_plan_items,
    get_allocated_expense_total,
)
```

- [ ] **Step 2: Replace distribution total validation**

In `PlanningDistributeView.post`, replace:

```python
        root_items = plan.items.filter(
            category__parent__isnull=True
        ).select_related('category')
        root_total = sum(i.planned_amount for i in root_items)
        if root_total > plan.teto_calculado:
```

with:

```python
        allocated_total = get_allocated_expense_total(plan)
        if allocated_total > plan.teto_calculado:
```

Then replace the message interpolation:

```python
                f'A soma das categorias raiz ({_fmt(root_total)}) excede o teto '
```

with:

```python
                f'A soma das despesas planejadas ({_fmt(allocated_total)}) excede o teto '
```

- [ ] **Step 3: Replace web copy loop**

In `PlanningCopyView.post`, replace:

```python
        for src_item in source.items.select_related('category'):
            MonthlyPlanItem.objects.get_or_create(
                monthly_plan=plan,
                category=src_item.category,
                defaults={'planned_amount': src_item.planned_amount},
            )
```

with:

```python
        copy_allocatable_plan_items(source, plan)
```

- [ ] **Step 4: Run targeted web tests**

Run:

```bash
./scripts/dj test budgets.tests.PlanningWizardViewTests.test_copy_view_ignores_income_and_hidden_parent_items budgets.tests.PlanningWizardViewTests.test_distribute_validation_ignores_legacy_income_and_hidden_parent_items budgets.tests.PlanningWizardViewTests.test_copy_view_copies_items_from_previous_month budgets.tests.PlanningWizardViewTests.test_distribute_view_post_creates_items
```

Expected: all listed tests pass.

- [ ] **Step 5: Commit**

```bash
git add budgets/plan_item_rules.py budgets/tests.py budgets/views.py
git commit -m "fix: ignore hidden plan items in web planning flow"
```

---

## Task 4: API Validation And Safe Copy

**Files:**
- Modify: `budgets/tests.py`
- Modify: `api/serializers.py`
- Modify: `api/views.py`

- [ ] **Step 1: Add failing API tests**

Inside `MonthlyPlanAPITests.setUp`, after `self.expense_cat = ...`, add:

```python
        self.income_cat = self.make_income_category(self.user, name="Salário")
```

Add these tests after `test_copy_from_previous_copies_items`:

```python
    def test_copy_from_previous_ignores_income_items(self):
        prev_month = self.today.month - 1 if self.today.month > 1 else 12
        prev_year = self.today.year if self.today.month > 1 else self.today.year - 1
        prev_plan = MonthlyPlan.objects.create(
            user=self.user,
            year=prev_year,
            month=prev_month,
            renda_prevista=Decimal("5000.00"),
            teto_despesas=Decimal("3000.00"),
        )
        MonthlyPlanItem.objects.bulk_create([
            MonthlyPlanItem(
                monthly_plan=prev_plan,
                category=self.income_cat,
                planned_amount=Decimal("5000.00"),
            )
        ])
        self.item.delete()

        resp = self.client.post(f"{self._plan_url(pk=self.plan.pk)}copy_from_previous/")

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["copied_items"], 0)
        self.assertFalse(
            MonthlyPlanItem.objects.filter(
                monthly_plan=self.plan,
                category=self.income_cat,
            ).exists()
        )
```

Add this test after `test_create_item`:

```python
    def test_create_item_rejects_income_category(self):
        resp = self.client.post(self._item_url(), {
            "monthly_plan": self.plan.pk,
            "category": self.income_cat.pk,
            "planned_amount": "200.00",
        }, content_type="application/json")

        self.assertEqual(resp.status_code, 400)
        self.assertIn("category", resp.data)

    def test_create_item_rejects_inactive_category(self):
        inactive = Category.objects.create(
            user=self.user,
            name="Despesa Inativa",
            category_type="EXPENSE",
            is_active=False,
        )

        resp = self.client.post(self._item_url(), {
            "monthly_plan": self.plan.pk,
            "category": inactive.pk,
            "planned_amount": "200.00",
        }, content_type="application/json")

        self.assertEqual(resp.status_code, 400)
        self.assertIn("category", resp.data)
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
./scripts/dj test budgets.tests.MonthlyPlanAPITests.test_copy_from_previous_ignores_income_items budgets.tests.MonthlyPlanAPITests.test_create_item_rejects_income_category budgets.tests.MonthlyPlanAPITests.test_create_item_rejects_inactive_category
```

Expected: tests fail before API validation and safe copy are implemented.

- [ ] **Step 3: Update serializer validation**

In `api/serializers.py`, inside `MonthlyPlanItemSerializer.validate`, replace the category ownership block:

```python
        if category and category.user != user:
            raise serializers.ValidationError(
                {'category': 'Categoria não pertence ao usuário.'}
            )
```

with:

```python
        if category and category.user != user:
            raise serializers.ValidationError(
                {'category': 'Categoria não pertence ao usuário.'}
            )
        if category and not category.is_active:
            raise serializers.ValidationError(
                {'category': 'Apenas categorias ativas podem ser planejadas.'}
            )
        if category and category.category_type != 'EXPENSE':
            raise serializers.ValidationError(
                {'category': 'Apenas categorias de despesa podem ser planejadas.'}
            )
```

- [ ] **Step 4: Update API copy action**

In `api/views.py`, add this import near the existing imports:

```python
from budgets.plan_item_rules import copy_allocatable_plan_items
```

In `MonthlyPlanViewSet.copy_from_previous`, replace:

```python
        copied = 0
        for item in previous.items.all():
            _, created = MonthlyPlanItem.objects.get_or_create(
                monthly_plan=plan,
                category=item.category,
                defaults={
                    'planned_amount': item.planned_amount,
                    'alert_threshold': item.alert_threshold,
                },
            )
            if created:
                copied += 1
```

with:

```python
        copied = copy_allocatable_plan_items(previous, plan)
```

- [ ] **Step 5: Run targeted API tests**

Run:

```bash
./scripts/dj test budgets.tests.MonthlyPlanAPITests.test_copy_from_previous_ignores_income_items budgets.tests.MonthlyPlanAPITests.test_create_item_rejects_income_category budgets.tests.MonthlyPlanAPITests.test_create_item_rejects_inactive_category budgets.tests.MonthlyPlanAPITests.test_copy_from_previous_copies_items budgets.tests.MonthlyPlanAPITests.test_create_item
```

Expected: all listed tests pass.

- [ ] **Step 6: Commit**

```bash
git add api/serializers.py api/views.py budgets/tests.py
git commit -m "fix: validate monthly plan item API inputs"
```

---

## Task 5: Regression Sweep And Production Runbook

**Files:**
- Modify: `docs/superpowers/plans/2026-07-01-monthly-plan-editing.md` only if command output reveals a command correction is needed.

- [ ] **Step 1: Run focused Django regression suite**

Run:

```bash
./scripts/dj test budgets.tests.MonthlyPlanItemModelTests budgets.tests.PlanningWizardViewTests budgets.tests.MonthlyPlanAPITests
```

Expected: all targeted tests pass.

- [ ] **Step 2: Run project system check**

Run:

```bash
./scripts/dj check
```

Expected:

```text
System check identified no issues (0 silenced).
```

- [ ] **Step 3: Confirm full-suite baseline status**

Run:

```bash
./scripts/dj test
```

Expected current known outcome unless separately fixed:

```text
FAILED (errors=1)
FileNotFoundError: ... static/css/custom.css
```

If the full suite fails only for the known `core.tests.FrontendAssetTests.test_runtime_css_does_not_require_tailwind_build_step` baseline, record that in the final implementation summary. If new failures appear in monthly planning tests, stop and fix them before continuing.

- [ ] **Step 4: Prepare read-only production verification**

Use this command after deploy to list remaining invalid production rows. It is read-only:

```bash
ssh root@38.52.128.62 'docker exec -i finanpy-db-1 sh -lc '\''psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -P pager=off'\''' <<'SQL'
SELECT mp.id AS plan_id, mp.year, mp.month, c.id AS category_id,
       c.name, c.category_type, c.parent_id, mpi.planned_amount
FROM budgets_monthlyplanitem mpi
JOIN budgets_monthlyplan mp ON mp.id = mpi.monthly_plan_id
JOIN categories_category c ON c.id = mpi.category_id
WHERE c.category_type <> 'EXPENSE'
ORDER BY mp.year, mp.month, c.name;
SQL
```

Expected before cleanup in the observed production state: rows for `Salario` and `Aluguel Recebido`.

- [ ] **Step 5: Prepare explicit cleanup command for approval**

Do not run this without explicit approval in the implementation session. This removes non-expense monthly plan items:

```bash
ssh root@38.52.128.62 'docker exec -i finanpy-db-1 sh -lc '\''psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -P pager=off'\''' <<'SQL'
DELETE FROM budgets_monthlyplanitem mpi
USING categories_category c
WHERE c.id = mpi.category_id
  AND c.category_type <> 'EXPENSE'
RETURNING mpi.id, mpi.monthly_plan_id, mpi.category_id, mpi.planned_amount;
SQL
```

Expected for the observed production state: two deleted rows for the copied income items.

- [ ] **Step 6: Commit final verification notes only if changed**

If implementation changes this plan or adds a separate runbook file, commit it:

```bash
git add docs/superpowers/plans/2026-07-01-monthly-plan-editing.md
git commit -m "docs: add monthly plan cleanup runbook"
```

Skip this commit if the implementation only used the command text already present in this plan.

---

## Execution Notes

- Do not alter production data during code implementation.
- Deploy and production cleanup are separate decisions.
- Preserve existing unrelated worktree changes:
  - `mcp/finanpy_mcp/config.py`
  - `scripts/debug_python_env.sh`
  - `scripts/dj`
- Use `./scripts/dj` for Django commands in this repo to avoid local Python environment contamination.
