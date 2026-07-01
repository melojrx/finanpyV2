# Monthly Plan Editing Design

## Problem

Production has a July 2026 monthly plan copied from June 2026 that contains
`MonthlyPlanItem` rows for income categories (`Salario` and `Aluguel Recebido`).
Those rows are invisible in the expense distribution screen, but the backend
still includes root-category items in the ceiling validation. The user then sees:

> A soma das categorias raiz (R$ 12.350,31) excede o teto calculado (R$ 11.627,32).

The observed root total is exactly the copied income total. This blocks normal
editing of the current month's expense plan, especially when adding new
subcategories that were not present in the copied plan.

## Goals

- Let the user copy the previous month's plan and freely adjust the current
  month afterward, including after the plan is active.
- Make `MonthlyPlanItem` represent expense allocation only.
- Prevent income categories from being created or copied as monthly plan items.
- Keep parent/child category behavior predictable in the distribution screen.
- Provide a safe production cleanup path for existing invalid rows.

## Non-Goals

- Do not redesign income forecasting. `MonthlyPlan.renda_prevista` remains the
  source of planned income.
- Do not introduce a new model for income plan items in this change.
- Do not block editing of active plans.
- Do not silently mutate production data during app startup or page load.

## Domain Rules

`MonthlyPlan` owns the monthly header:

- planned income (`renda_prevista`)
- savings goal
- reserves
- calculated expense ceiling (`teto_calculado`)
- status (`DRAFT`, `ACTIVE`, `CLOSED`)

`MonthlyPlanItem` owns only expense allocation:

- its category must belong to the same user as the plan
- its category must be active
- its category must have `category_type='EXPENSE'`
- its planned amount must be greater than zero

An active monthly plan remains editable. Saving changes to item amounts,
adding subcategories, or removing categories does not change `ACTIVE` back to
`DRAFT`.

## Parent And Child Category Behavior

The distribution UI keeps the current model:

- If a root expense category has active children, the user allocates values to
  the children.
- If a root expense category has no active children, the user may allocate a
  value directly to the root.
- An allocatable category is therefore either an active expense child category
  or an active root expense category with no active children.
- The backend validation compares total planned expenses against
  `plan.teto_calculado`.
- Backend validation must use only allocatable expense items, not income items
  and not stale parent items that are hidden because the parent has children.

This preserves the current user experience while removing invisible state from
the calculation.

## Web Flow

### Copy Previous Month

The web copy view copies the header fields from the previous plan as it does
today. For items, it copies only valid expense items:

- category belongs to the same user
- category is active
- category has `category_type='EXPENSE'`
- category is allocatable in the current category tree

Invalid legacy items are ignored. This prevents a bad historical plan from
poisoning newly copied months.

### Distribution Screen

The distribution screen remains the editing surface for the current month. It:

- renders active expense categories only
- creates or updates visible submitted items
- deletes visible unchecked items
- validates total expense allocation against `teto_calculado`

The validation must not include income items, non-expense rows, or hidden parent
rows that are no longer allocatable. If invalid legacy rows already exist on the
plan, they should not block editing. A separate cleanup task handles their
removal.

### Review And Activation

The review step may activate a draft plan as today. If the plan is already
active, editing the distribution and saving through the review flow keeps it
active.

## API Flow

The API `copy_from_previous` action follows the same rules as the web copy
flow: copy only valid active expense items.

The `MonthlyPlanItemSerializer` rejects non-expense categories and inactive
categories. API clients receive HTTP 400 with a field-level category error.

## Model Boundary

`MonthlyPlanItem` should enforce its domain rule reliably when saved through
normal application code. Add or update model validation so non-expense
categories cannot be saved. The serializer and view validations remain in place
to produce user-friendly errors earlier, but the model is the final guard.

## Production Cleanup

Existing invalid rows in production should be removed only after explicit
operator approval. The cleanup should be documented and auditable.

Read-only verification query:

```sql
SELECT mp.id AS plan_id, mp.year, mp.month, c.id AS category_id,
       c.name, c.category_type, mpi.planned_amount
FROM budgets_monthlyplanitem mpi
JOIN budgets_monthlyplan mp ON mp.id = mpi.monthly_plan_id
JOIN categories_category c ON c.id = mpi.category_id
WHERE c.category_type <> 'EXPENSE'
ORDER BY mp.year, mp.month, c.name;
```

Approved cleanup query:

```sql
DELETE FROM budgets_monthlyplanitem mpi
USING categories_category c
WHERE c.id = mpi.category_id
  AND c.category_type <> 'EXPENSE';
```

This cleanup is intentionally separate from the code deploy.

## Testing Strategy

Add regression coverage for:

- web copy ignores income-category items from the previous month
- API copy ignores income-category items from the previous month
- serializer rejects creating a monthly plan item for an income category
- distribution validation ignores legacy non-expense items so current expense
  edits can be saved
- active plans can still be edited without changing status back to draft

Keep tests focused in `budgets/tests.py` and `api/tests.py`, following the
existing test style.

## Deployment Notes

Implementation can be deployed without touching production data. After deploy,
run the read-only verification query. If invalid rows remain, request approval
and run the cleanup query once.

For the currently observed July 2026 issue, removing the two invalid income
items (`Salario` and `Aluguel Recebido`) from `budgets_monthlyplanitem` will
unblock the existing draft plan.
