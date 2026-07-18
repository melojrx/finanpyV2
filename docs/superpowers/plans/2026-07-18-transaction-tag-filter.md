# Transaction Tag Filter Implementation Plan

> **Execution workflow:** implement task-by-task with a red-green-refactor cycle.

**Goal:** Complete the transaction tag filter so users can combine one or more
tags with the existing transaction filters on desktop and mobile without losing
the selection when changing status or page.

**Architecture:** Reuse the existing user-scoped `TransactionFilterForm` and
the existing `tags__in` plus `distinct()` queryset behavior. Keep the OR
semantics approved by the tags design spec: a transaction matches when it has
at least one selected tag. Present it through a reusable enhanced component:
real checkbox inputs remain the form contract, while a small vanilla
JavaScript controller provides search, compact summary, clear/done actions,
outside-click handling, and Escape support. No model, migration, API, or signal
changes.

**Tech Stack:** Django 5.2, Django templates, Django TestCase, TailwindCSS.

## Spec

Use the approved spec:
`docs/superpowers/specs/2026-05-31-tags-design.md`.

Current targeted baseline before this work:
`venv/bin/python manage.py test tags --verbosity 1` passes 29 tests.

## File Structure

- Modify: `tags/tests.py`
  - Cover desktop/mobile controls, OR semantics, duplicate suppression,
    user-scoped choices, selected state, pagination, and status navigation.
- Modify: `templates/transactions/transaction_list.html`
  - Render the professional multitag component on desktop and mobile.
  - Display selected tags as active filter chips.
  - Preserve repeated query parameters with Django's `{% querystring %}` tag.
- Create: `templates/components/_tag_filter_multiselect.html`
  - Reusable compact trigger and checkbox selection panel.
- Create: `static/js/tag-filter.js`
  - Progressive enhancement, search, summary, responsive synchronization,
    keyboard dismissal, and focus management.

## Task 1: Lock The Filter Contract With Tests

- [x] Add a test proving the tag control is rendered for desktop and mobile.
- [x] Add a test proving only the authenticated user's tags are offered.
- [x] Add a test proving multiple selected tags use OR semantics.
- [x] Ensure a transaction carrying multiple selected tags appears once.
- [x] Add a test proving selected tags remain selected in the rendered forms.
- [x] Add tests proving pagination and status links preserve every selected tag.
- [x] Run the new tests and confirm they fail for the missing UI/querystring
  behavior while the existing backend filter test remains green.

## Task 2: Expose Tags In Both Filter Interfaces

- [x] Render `filter_form.tags` in the desktop advanced-filter panel.
- [x] Render a separate mobile multiselect with a unique HTML id.
- [x] Reuse the bound form value to restore all selected options.
- [x] Render active chips with the selected tag names.
- [x] Keep the controls optional when the user has no tags.

## Task 3: Preserve The Complete Querystring

- [x] Replace hand-built status links with `{% querystring %}`.
- [x] Replace hand-built pagination links with `{% querystring %}`.
- [x] Remove `page` when changing status.
- [x] Preserve repeated `tags` parameters and all other active filters.

## Task 4: Validate And Review

- [x] Run the targeted transaction-tag integration tests.
- [x] Run the complete `tags` test suite.
- [x] Run `manage.py check`.
- [x] Review the diff for unrelated changes and confirm no migration is needed.

Validation result: all 36 `tags` tests pass, Django system checks pass, and
`makemigrations --check --dry-run` reports no changes. The full suite ran 318
tests with 317 passing; the only error is the pre-existing
`core.tests.FrontendAssetTests.test_runtime_css_does_not_require_tailwind_build_step`,
which still references the removed `static/css/custom.css` file and is outside
this feature's scope.

## Task 5: Professional Multiselect Redesign

### Critical review

The first UI exposed the browser's open multi-select list directly. Although
functionally correct, it was visually and behaviorally unsuitable for a compact
financial filter: it created a large empty block, made selection mechanics
unclear, broke the visual rhythm of the two-column panel, and pushed the primary
action away from the other controls.

Current reference behavior:

- Mobills keeps each filter criterion compact and opens selection in a temporary
  layer, with Cancel/Apply actions at panel level.
- Carbon's multiselect pattern uses a closed dropdown trigger and checkbox rows.
- WAI-ARIA guidance favors real checkbox semantics for independent multiple
  choices, visible labels, keyboard access, Escape dismissal, and explicit
  selected state.

### Revised tasks

- [x] Replace the visible native multi-select with a compact custom trigger.
- [x] Show a simple panel of real checkbox inputs.
- [x] Summarize zero, one, or many selections in the closed trigger.
- [x] Close on outside click and Escape.
- [x] Keep the dropdown above the transaction table.
- [x] Add regression tests for structure, checked state, unique ids, and assets.
- [x] Add clearly identifiable local demo transactions with multiple tag
  combinations for manual validation.
- [x] Validate the desktop behavior and rerun the relevant suite.

## Acceptance Criteria

- Users can select one or more of their tags on desktop and mobile.
- Results match transactions containing any selected tag.
- Results and financial totals do not contain duplicate transactions.
- Tag selections survive form submission, pagination, and status changes.
- Existing filters continue composing with the tag filter.
- No tag owned by another user is exposed in the filter controls.
- Existing local changes outside this feature remain untouched.
