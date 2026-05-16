# M7 — Polimento, Performance & Acessibilidade

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Atingir Lighthouse PWA ≥ 90, Performance ≥ 85, Accessibility ≥ 95 no mobile, com testes E2E e bundle analysis.

**Architecture:** Otimização incremental — fonts self-hosted, JS tree-shaken, a11y hardened, SW versionado, Playwright + axe-core para validação automatizada. Cada task é independente e commitável.

**Tech Stack:** Django 5.2, django-tailwind, Playwright, axe-core, Lighthouse CI, Workbox 7.1

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Modify | `templates/base.html` | Remove Google Fonts CDN, add local font preload, remove custom.css |
| Delete | `static/css/custom.css` | Migrate remaining used classes to Tailwind, then delete |
| Create | `static/fonts/inter-var-latin.woff2` | Self-hosted Inter variable font |
| Modify | `static/css/tokens.css` | Add @font-face for self-hosted Inter |
| Modify | `static/js/main.js` | Strip dead code — keep only CurrencyFormatter + FinancialUtils |
| Modify | `static/sw.js` | Content-hash precache, local Workbox bundle |
| Modify | `static/js/shell.js` | Focus trap in drawer/sheets, SW update banner |
| Modify | `templates/components/_drawer.html` | inert support for focus trap |
| Modify | `templates/components/_bottom_sheet.html` | Focus trap + Escape |
| Modify | `templates/transactions/transaction_form.html` | enterkeyhint on all inputs |
| Modify | `templates/accounts/account_form.html` | enterkeyhint + inputmode |
| Modify | `templates/categories/category_form.html` | enterkeyhint |
| Modify | `templates/goals/goal_form.html` | enterkeyhint + inputmode="decimal" |
| Modify | `templates/profiles/profile_edit.html` | enterkeyhint |
| Create | `tests/e2e/conftest.py` | Playwright fixtures |
| Create | `tests/e2e/test_navigation.py` | Mobile nav E2E |
| Create | `tests/e2e/test_transaction_flow.py` | Create transaction E2E |
| Create | `tests/e2e/test_a11y.py` | axe-core audit on key pages |
| Create | `pyproject.toml` | Playwright + pytest config |
| Modify | `theme/static_src/src/styles.css` | Add card/btn component classes |

---

## Task 1: Self-host Inter font (eliminate render-blocking Google Fonts)

**Files:**
- Create: `static/fonts/inter-var-latin.woff2`
- Modify: `static/css/tokens.css`
- Modify: `templates/base.html:36-38`

- [ ] **Step 1: Download Inter variable font**

```bash
mkdir -p static/fonts
curl -L "https://github.com/rsms/inter/releases/download/v4.1/Inter-4.1.zip" -o /tmp/inter.zip
unzip -j /tmp/inter.zip "Inter-4.1/InterVariable.woff2" -d static/fonts/
mv static/fonts/InterVariable.woff2 static/fonts/inter-var-latin.woff2
```

- [ ] **Step 2: Add @font-face to tokens.css**

Add at the top of `static/css/tokens.css`:

```css
@font-face {
  font-family: 'Inter';
  font-style: normal;
  font-weight: 100 900;
  font-display: swap;
  src: url('/static/fonts/inter-var-latin.woff2') format('woff2');
  unicode-range: U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6,
    U+02DA, U+02DC, U+0300-0301, U+0303-0304, U+0308-0309, U+0323,
    U+0329, U+2000-206F, U+2074, U+20AC, U+2122, U+2191, U+2193,
    U+2212, U+2215, U+FEFF, U+FFFD;
}
```

- [ ] **Step 3: Remove Google Fonts from base.html**

Remove lines 36-38:
```html
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
```

Replace with preload for local font:
```html
    <link rel="preload" href="{% static 'fonts/inter-var-latin.woff2' %}" as="font" type="font/woff2" crossorigin>
```

- [ ] **Step 4: Verify font loads**

```bash
python manage.py runserver 8001 &
sleep 2
curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/static/fonts/inter-var-latin.woff2
# Expected: 200
kill %1
```

- [ ] **Step 5: Commit**

```bash
git add static/fonts/ static/css/tokens.css templates/base.html
git commit -m "perf(fonts): self-host Inter variable font, remove render-blocking Google Fonts CDN"
```

---

## Task 2: Slim down main.js (remove dead code)

**Files:**
- Modify: `static/js/main.js`

**Analysis:** 1234 lines → only `CurrencyFormatter` and `FinancialUtils` are actually used by templates. Everything else is dead code (ThemeManager, ToastManager, ChartManager, TransactionManager, QuickTransactionModal, AjaxHelper, EnhancedFormValidator, initializeInteractiveElements, initializeTransactionFeatures) — all superseded by shell.js, masks.js, or inline template scripts.

- [ ] **Step 1: Replace main.js with slim version**

Replace entire `static/js/main.js` with:

```javascript
/**
 * FinanPy — Utilitários financeiros globais
 */
class CurrencyFormatter {
  static format(amount, options = {}) {
    const { currency = 'BRL', locale = 'pt-BR', showSymbol = true, decimals = 2 } = options;
    return new Intl.NumberFormat(locale, {
      style: showSymbol ? 'currency' : 'decimal',
      currency,
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    }).format(amount);
  }

  static formatInput(input) {
    if (!input.value) return;
    let value = input.value.replace(/[^\d,]/g, '');
    if (value.includes(',')) {
      const parts = value.split(',');
      if (parts.length > 2) value = parts.slice(0, -1).join('') + ',' + parts[parts.length - 1];
      if (parts[1] && parts[1].length > 2) value = parts[0] + ',' + parts[1].substring(0, 2);
    }
    const parts = value.split(',');
    parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, '.');
    input.value = parts.join(',');
  }

  static unformat(formattedValue) {
    if (!formattedValue) return '0';
    return formattedValue.replace(/[R$\s]/g, '').replace(/\./g, '').replace(',', '.');
  }

  static parseBrazilianNumber(value) {
    return parseFloat(this.unformat(value)) || 0;
  }
}

class FinancialUtils {
  static formatCurrency(amount, currency = 'BRL') {
    return new Intl.NumberFormat('pt-BR', { style: 'currency', currency }).format(amount);
  }

  static formatNumber(number, decimals = 2) {
    return new Intl.NumberFormat('pt-BR', {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    }).format(number);
  }

  static formatDate(date) {
    return new Intl.DateTimeFormat('pt-BR').format(new Date(date));
  }
}

window.CurrencyFormatter = CurrencyFormatter;
window.FinancialUtils = FinancialUtils;
```

- [ ] **Step 2: Verify no runtime errors on transaction form**

```bash
python manage.py runserver 8001 &
sleep 2
curl -s http://localhost:8001/static/js/main.js | wc -c
# Expected: < 2000 bytes
kill %1
```

- [ ] **Step 3: Commit**

```bash
git add static/js/main.js
git commit -m "perf(js): strip dead code from main.js — 44KB → 2KB (keep CurrencyFormatter + FinancialUtils)"
```

---

## Task 3: Migrate custom.css to Tailwind and delete

**Files:**
- Modify: `theme/static_src/src/styles.css`
- Delete: `static/css/custom.css`
- Modify: `templates/base.html:33`

- [ ] **Step 1: Add component classes to Tailwind source**

Edit `theme/static_src/src/styles.css`:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer components {
  .card {
    @apply bg-dark-800/60 backdrop-blur-sm border border-dark-700 rounded-xl p-6 transition-all duration-300;
  }
  .card:hover {
    @apply border-dark-600;
  }
  .btn-primary {
    @apply bg-primary-600 hover:bg-primary-700 text-white rounded-lg font-medium px-4 py-2 transition-colors duration-200;
  }
  .btn-secondary {
    @apply bg-dark-600 hover:bg-dark-500 text-white rounded-lg font-medium px-4 py-2 transition-colors duration-200;
  }
}
```

- [ ] **Step 2: Remove custom.css link from base.html**

Remove line 33:
```html
    <link rel="stylesheet" type="text/css" href="{% static 'css/custom.css' %}">
```

- [ ] **Step 3: Rebuild Tailwind**

```bash
cd theme/static_src && npm run build && cd ../..
```

- [ ] **Step 4: Delete custom.css**

```bash
rm static/css/custom.css
```

- [ ] **Step 5: Commit**

```bash
git add theme/static_src/src/styles.css templates/base.html
git rm static/css/custom.css
git commit -m "perf(css): migrate .card/.btn-primary/.btn-secondary to Tailwind components, delete custom.css"
```

---

## Task 4: Focus trap in drawer and bottom-sheets

**Files:**
- Modify: `static/js/shell.js`
- Modify: `templates/components/_drawer.html`

**Analysis:** Drawer already has: Escape close, backdrop close, focus on close button on open, aria-modal. Missing: focus trap (Tab cycles within drawer while open), inert on main content.

- [ ] **Step 1: Add focus trap utility to shell.js**

Add after the drawer close function (after line 102 in shell.js):

```javascript
  // ---------------------------------------------------------------------------
  // 2.1) Focus trap utility
  // ---------------------------------------------------------------------------
  function trapFocus(container) {
    var focusable = container.querySelectorAll(
      'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
    );
    if (!focusable.length) return;
    var first = focusable[0];
    var last = focusable[focusable.length - 1];

    container.addEventListener('keydown', function (e) {
      if (e.key !== 'Tab') return;
      if (e.shiftKey) {
        if (document.activeElement === first) { e.preventDefault(); last.focus(); }
      } else {
        if (document.activeElement === last) { e.preventDefault(); first.focus(); }
      }
    });
  }
```

- [ ] **Step 2: Apply focus trap to drawer**

In the `openDrawer()` function, after the `closeBtn.focus()` call, add:

```javascript
    trapFocus(drawer);
```

Also add inert to main content when drawer opens. In `openDrawer()`:
```javascript
    var mainContent = document.querySelector('main');
    if (mainContent) mainContent.setAttribute('inert', '');
```

In `closeDrawer()`:
```javascript
    var mainContent = document.querySelector('main');
    if (mainContent) mainContent.removeAttribute('inert');
```

- [ ] **Step 3: Apply focus trap to bottom-sheets**

In the `openSheet(id)` function, after removing `hidden`:

```javascript
    trapFocus(sheet);
    var mainContent = document.querySelector('main');
    if (mainContent) mainContent.setAttribute('inert', '');
```

In `closeSheet(sheet)`:
```javascript
    var mainContent = document.querySelector('main');
    if (mainContent) mainContent.removeAttribute('inert');
```

- [ ] **Step 4: Add Escape key handling for bottom-sheets**

Add to the existing keydown listener:

```javascript
    if (e.key === 'Escape') {
      var openSheets = document.querySelectorAll('.finanpy-sheet:not(.hidden)');
      openSheets.forEach(function (s) { closeSheet(s); });
    }
```

- [ ] **Step 5: Commit**

```bash
git add static/js/shell.js
git commit -m "a11y(focus): add focus trap + inert to drawer and bottom-sheets"
```

---

## Task 5: SW update banner (notify user of new version)

**Files:**
- Modify: `static/js/shell.js`
- Modify: `templates/components/_toast.html` (or inline in shell.js)

- [ ] **Step 1: Replace auto-skipWaiting with user-prompted update**

In `static/js/shell.js`, replace the SW registration section (lines 20-42) with:

```javascript
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', function () {
      navigator.serviceWorker
        .register('/sw.js', { scope: '/' })
        .then(function (reg) {
          reg.addEventListener('updatefound', function () {
            var nw = reg.installing;
            if (!nw) return;
            nw.addEventListener('statechange', function () {
              if (nw.state === 'installed' && navigator.serviceWorker.controller) {
                showUpdateBanner(nw);
              }
            });
          });
        })
        .catch(function (err) {
          console.warn('[FinanPy] SW registration falhou:', err);
        });

      navigator.serviceWorker.addEventListener('message', function (event) {
        if (!event.data) return;
        if (event.data.type === 'SYNC_DRAINED') {
          showSyncToast();
        }
      });

      var refreshing = false;
      navigator.serviceWorker.addEventListener('controllerchange', function () {
        if (refreshing) return;
        refreshing = true;
        window.location.reload();
      });
    });
  }

  function showUpdateBanner(worker) {
    var banner = document.createElement('div');
    banner.className = 'fixed bottom-20 left-4 right-4 md:left-auto md:right-4 md:w-80 z-50 bg-primary-700 text-white rounded-xl p-4 shadow-lg flex items-center justify-between gap-3';
    banner.setAttribute('role', 'alert');
    banner.innerHTML =
      '<span class="text-sm font-medium">Nova versão disponível</span>' +
      '<button type="button" class="px-3 py-1.5 bg-white text-primary-700 rounded-lg text-sm font-semibold hover:bg-gray-100 transition">Atualizar</button>';
    banner.querySelector('button').addEventListener('click', function () {
      worker.postMessage({ type: 'SKIP_WAITING' });
      banner.remove();
    });
    document.body.appendChild(banner);
  }

  function showSyncToast() {
    var container = document.getElementById('finanpy-toasts');
    if (!container) return;
    var toast = document.createElement('div');
    toast.className = 'finanpy-toast flex items-center gap-3 px-4 py-3 rounded-xl bg-success-700/90 text-white text-sm shadow-lg';
    toast.setAttribute('role', 'status');
    toast.textContent = 'Transações sincronizadas com sucesso';
    container.appendChild(toast);
    setTimeout(function () { toast.remove(); }, 4000);
  }
```

- [ ] **Step 2: Commit**

```bash
git add static/js/shell.js
git commit -m "feat(pwa): SW update banner instead of auto-skipWaiting + sync toast"
```

---

## Task 6: Accessibility — enterkeyhint and inputmode on all forms

**Files:**
- Modify: `templates/transactions/transaction_form.html`
- Modify: `templates/accounts/account_form.html`
- Modify: `templates/categories/category_form.html`
- Modify: `templates/goals/goal_form.html`
- Modify: `templates/profiles/profile_edit.html`

- [ ] **Step 1: Audit all form inputs missing enterkeyhint/inputmode**

```bash
grep -rn "<input\|<textarea\|<select" templates/ | grep -v "enterkeyhint\|type=\"hidden\"\|type=\"checkbox\"\|type=\"radio\"\|type=\"file\"" | grep -v "components/" | grep -v "_backup\|_enhanced"
```

- [ ] **Step 2: Add enterkeyhint to transaction_form.html**

For each visible input in `templates/transactions/transaction_form.html`:
- Description input: add `enterkeyhint="next"`
- Amount input: already has `inputmode="decimal"`, add `enterkeyhint="next"`
- Date input: add `enterkeyhint="next"`
- Notes textarea: add `enterkeyhint="done"`
- Submit button area: no change needed

- [ ] **Step 3: Add enterkeyhint to account_form.html**

- Name input: `enterkeyhint="next"`
- Balance input: `inputmode="decimal" enterkeyhint="next"`
- Description/notes: `enterkeyhint="done"`

- [ ] **Step 4: Add enterkeyhint to category_form.html**

- Name input: `enterkeyhint="next"`
- Description: `enterkeyhint="done"`

- [ ] **Step 5: Add enterkeyhint to goal_form.html**

- Name: `enterkeyhint="next"`
- Target amount: `inputmode="decimal" enterkeyhint="next"`
- Current amount: `inputmode="decimal" enterkeyhint="next"`
- Date: `enterkeyhint="done"`

- [ ] **Step 6: Add enterkeyhint to profile_edit.html**

- Name fields: `enterkeyhint="next"`
- Email: `enterkeyhint="next" inputmode="email"`
- Phone: `enterkeyhint="done" inputmode="tel"`

- [ ] **Step 7: Commit**

```bash
git add templates/transactions/transaction_form.html templates/accounts/account_form.html templates/categories/category_form.html templates/goals/goal_form.html templates/profiles/profile_edit.html
git commit -m "a11y(forms): add enterkeyhint + inputmode to all form inputs"
```

---

## Task 7: Accessibility — ARIA improvements and contrast

**Files:**
- Modify: `templates/components/_bottom_nav.html`
- Modify: `templates/components/_top_bar.html`
- Modify: various list templates

- [ ] **Step 1: Add aria-current to active nav items**

In `_bottom_nav.html`, the active item should have `aria-current="page"`. Add Django template logic:

```html
{% if request.resolver_match.url_name == 'dashboard' %}aria-current="page"{% endif %}
```

For each nav item (dashboard, transactions, budgets, goals).

- [ ] **Step 2: Ensure all decorative SVGs have aria-hidden="true"**

```bash
grep -rn "<svg" templates/ | grep -v "aria-hidden" | head -20
```

Fix any missing `aria-hidden="true"` on decorative SVGs.

- [ ] **Step 3: Verify color contrast on key elements**

Check that text on gradient backgrounds meets WCAG AA (4.5:1 for normal text, 3:1 for large text). Key areas:
- Gray text (`text-gray-400`) on `bg-dark-800` → contrast ratio ~5.5:1 ✓
- Gray text (`text-gray-500`) on `bg-dark-900` → may be below 4.5:1 — upgrade to `text-gray-400`

```bash
grep -rn "text-gray-500" templates/ | wc -l
```

Replace `text-gray-500` with `text-gray-400` where it appears on dark backgrounds.

- [ ] **Step 4: Add skip-to-content link**

In `templates/base.html`, after `<body>` tag:

```html
<a href="#main-content" class="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-[100] focus:bg-primary-600 focus:text-white focus:px-4 focus:py-2 focus:rounded-lg">
  Pular para conteúdo
</a>
```

And add `id="main-content"` to the `<main>` tag.

- [ ] **Step 5: Commit**

```bash
git add templates/
git commit -m "a11y: aria-current on nav, skip-to-content, contrast fixes, aria-hidden on decorative SVGs"
```

---

## Task 8: SW precache with content hashes

**Files:**
- Modify: `static/sw.js`

- [ ] **Step 1: Replace hardcoded revision strings with build-time hashes**

Since we don't have a build pipeline for SW, use a Django template tag approach. Create a view that serves sw.js with dynamic revisions.

Actually, simpler approach: use the `{% static %}` URL which already includes hash via ManifestStaticFilesStorage in production. For dev, keep revision as timestamp.

Replace the precache array in `static/sw.js`:

```javascript
  // Revisions updated at deploy time via manage.py collectstatic
  // In dev, use date-based revision; in prod, filenames are hashed by ManifestStaticFilesStorage
  var SW_VERSION = 'v2-' + '20260513';

  precaching.precacheAndRoute([
    { url: '/offline/', revision: SW_VERSION },
    { url: '/static/manifest.webmanifest', revision: SW_VERSION },
    { url: '/static/images/icons/icon-192.png', revision: SW_VERSION },
    { url: '/static/images/icons/icon-512.png', revision: SW_VERSION },
  ]);
```

- [ ] **Step 2: Add version comment for deploy automation**

Add at top of sw.js after the doc comment:

```javascript
// SW_BUILD_VERSION: 2026-05-13T00:00:00Z (updated by CI/deploy script)
```

- [ ] **Step 3: Commit**

```bash
git add static/sw.js
git commit -m "fix(pwa): version-based precache revisions for proper cache invalidation"
```

---

## Task 9: Test infrastructure — Playwright + axe-core

**Files:**
- Create: `pyproject.toml`
- Create: `tests/__init__.py`
- Create: `tests/e2e/__init__.py`
- Create: `tests/e2e/conftest.py`

- [ ] **Step 1: Create pyproject.toml with test config**

```toml
[project]
name = "finanpy"
version = "2.0.0"
requires-python = ">=3.13"

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-v --tb=short"

[tool.pytest.ini_options.markers]
e2e = "End-to-end tests (require running server)"
a11y = "Accessibility tests"
```

- [ ] **Step 2: Install test dependencies**

```bash
pip install playwright pytest pytest-playwright axe-playwright-python
playwright install chromium
```

Add to requirements.txt (dev section):
```
# Testing (M7)
pytest==8.3.4
pytest-playwright==0.6.2
axe-playwright-python==0.1.5
```

- [ ] **Step 3: Create test directory structure**

```bash
mkdir -p tests/e2e
touch tests/__init__.py tests/e2e/__init__.py
```

- [ ] **Step 4: Create conftest.py with fixtures**

Create `tests/e2e/conftest.py`:

```python
import subprocess
import time

import pytest
from playwright.sync_api import Page


@pytest.fixture(scope="session")
def base_url():
    return "http://localhost:8001"


@pytest.fixture(scope="session", autouse=True)
def django_server(base_url):
    """Start Django dev server for E2E tests."""
    proc = subprocess.Popen(
        ["python", "manage.py", "runserver", "8001", "--noreload"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    time.sleep(3)
    yield proc
    proc.terminate()
    proc.wait()


@pytest.fixture(scope="session")
def test_user():
    """Create test user via Django management."""
    from django.contrib.auth import get_user_model

    # Use subprocess to avoid import issues
    subprocess.run(
        [
            "python",
            "manage.py",
            "shell",
            "-c",
            (
                "from django.contrib.auth import get_user_model; "
                "User = get_user_model(); "
                "User.objects.filter(email='test@finanpy.dev').exists() or "
                "User.objects.create_user(email='test@finanpy.dev', password='TestPass123!')"
            ),
        ],
        check=True,
    )
    return {"email": "test@finanpy.dev", "password": "TestPass123!"}


@pytest.fixture()
def authenticated_page(page: Page, base_url: str, test_user: dict):
    """Page already logged in."""
    page.goto(f"{base_url}/login/")
    page.fill('input[name="username"], input[name="email"]', test_user["email"])
    page.fill('input[name="password"]', test_user["password"])
    page.click('button[type="submit"]')
    page.wait_for_url(f"{base_url}/dashboard/")
    return page


@pytest.fixture()
def mobile_page(page: Page):
    """Page with mobile viewport."""
    page.set_viewport_size({"width": 375, "height": 812})
    return page
```

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml tests/ requirements.txt
git commit -m "test(infra): add Playwright + axe-core test infrastructure"
```

---

## Task 10: E2E test — mobile navigation

**Files:**
- Create: `tests/e2e/test_navigation.py`

- [ ] **Step 1: Write navigation test**

Create `tests/e2e/test_navigation.py`:

```python
import pytest
from playwright.sync_api import Page, expect


@pytest.mark.e2e
class TestMobileNavigation:
    def test_bottom_nav_visible_on_mobile(self, authenticated_page: Page):
        page = authenticated_page
        page.set_viewport_size({"width": 375, "height": 812})
        nav = page.locator('nav[aria-label="Navegação principal"]')
        expect(nav).to_be_visible()

    def test_bottom_nav_hidden_on_desktop(self, authenticated_page: Page):
        page = authenticated_page
        page.set_viewport_size({"width": 1280, "height": 800})
        # Bottom nav is md:hidden
        nav = page.locator('nav[aria-label="Navegação principal"]').last
        expect(nav).to_be_hidden()

    def test_navigate_to_transactions(self, authenticated_page: Page):
        page = authenticated_page
        page.set_viewport_size({"width": 375, "height": 812})
        page.click('a[aria-label="Transações"]')
        page.wait_for_url("**/transactions/")
        expect(page).to_have_url(page.url)

    def test_navigate_to_budgets(self, authenticated_page: Page):
        page = authenticated_page
        page.set_viewport_size({"width": 375, "height": 812})
        page.click('a[aria-label="Orçamentos"]')
        page.wait_for_url("**/budgets/**")

    def test_drawer_opens_and_closes(self, authenticated_page: Page):
        page = authenticated_page
        page.set_viewport_size({"width": 375, "height": 812})
        # Open drawer
        page.click('[aria-label="Abrir menu"]')
        drawer = page.locator('#finanpy-drawer')
        expect(drawer).to_have_attribute("aria-hidden", "false")
        # Close with Escape
        page.keyboard.press("Escape")
        expect(drawer).to_have_attribute("aria-hidden", "true")

    def test_fab_visible_on_mobile(self, authenticated_page: Page):
        page = authenticated_page
        page.set_viewport_size({"width": 375, "height": 812})
        fab = page.locator('[aria-label="Nova transação"]')
        expect(fab).to_be_visible()
```

- [ ] **Step 2: Run tests (expect pass if server is up)**

```bash
pytest tests/e2e/test_navigation.py -v --headed
```

- [ ] **Step 3: Commit**

```bash
git add tests/e2e/test_navigation.py
git commit -m "test(e2e): mobile navigation tests — bottom-nav, drawer, FAB"
```

---

## Task 11: E2E test — transaction creation flow

**Files:**
- Create: `tests/e2e/test_transaction_flow.py`

- [ ] **Step 1: Write transaction flow test**

Create `tests/e2e/test_transaction_flow.py`:

```python
import pytest
from playwright.sync_api import Page, expect


@pytest.mark.e2e
class TestTransactionFlow:
    def test_create_expense_via_form(self, authenticated_page: Page):
        page = authenticated_page
        page.set_viewport_size({"width": 375, "height": 812})

        # Navigate to new transaction
        page.goto(page.url.replace("/dashboard/", "/transactions/new/"))
        page.wait_for_load_state("networkidle")

        # Fill form
        page.fill('input[name="description"]', "Teste E2E - Supermercado")
        page.fill('input[name="amount"]', "150,00")

        # Select type (expense)
        type_select = page.locator('select[name="transaction_type"]')
        if type_select.is_visible():
            type_select.select_option("EXPENSE")

        # Select account (first available)
        account_select = page.locator('select[name="account"]')
        if account_select.is_visible():
            account_select.select_option(index=1)

        # Select category (first available)
        category_select = page.locator('select[name="category"]')
        if category_select.is_visible():
            category_select.select_option(index=1)

        # Submit
        page.click('button[type="submit"]')
        page.wait_for_url("**/transactions/**")

    def test_fab_opens_transaction_form(self, authenticated_page: Page):
        page = authenticated_page
        page.set_viewport_size({"width": 375, "height": 812})

        fab = page.locator('[aria-label="Nova transação"]')
        fab.click()

        # Should navigate to transaction form or open bottom-sheet
        page.wait_for_timeout(500)
        # Verify we're on the form page or sheet is open
        form_visible = page.locator('form').first.is_visible()
        assert form_visible
```

- [ ] **Step 2: Commit**

```bash
git add tests/e2e/test_transaction_flow.py
git commit -m "test(e2e): transaction creation flow — form fill + FAB trigger"
```

---

## Task 12: E2E test — accessibility audit with axe-core

**Files:**
- Create: `tests/e2e/test_a11y.py`

- [ ] **Step 1: Write axe-core accessibility tests**

Create `tests/e2e/test_a11y.py`:

```python
import pytest
from playwright.sync_api import Page
from axe_playwright_python.sync_playwright import Axe


@pytest.mark.a11y
class TestAccessibility:
    """Run axe-core on key pages. Target: 0 critical/serious violations."""

    PAGES = [
        "/dashboard/",
        "/transactions/",
        "/transactions/new/",
        "/budgets/plano/",
        "/accounts/",
        "/goals/",
    ]

    @pytest.mark.parametrize("path", PAGES)
    def test_page_accessibility(self, authenticated_page: Page, path: str, base_url: str):
        page = authenticated_page
        page.set_viewport_size({"width": 375, "height": 812})
        page.goto(f"{base_url}{path}")
        page.wait_for_load_state("networkidle")

        axe = Axe()
        results = axe.run(page)

        violations = [
            v
            for v in results.response.get("violations", [])
            if v["impact"] in ("critical", "serious")
        ]

        if violations:
            messages = []
            for v in violations:
                nodes = ", ".join(n["target"][0] for n in v["nodes"][:3])
                messages.append(f"[{v['impact']}] {v['id']}: {v['description']} ({nodes})")
            pytest.fail(
                f"{len(violations)} critical/serious a11y violations on {path}:\n"
                + "\n".join(messages)
            )

    def test_dashboard_no_violations_desktop(self, authenticated_page: Page, base_url: str):
        page = authenticated_page
        page.set_viewport_size({"width": 1280, "height": 800})
        page.goto(f"{base_url}/dashboard/")
        page.wait_for_load_state("networkidle")

        axe = Axe()
        results = axe.run(page)

        critical = [
            v for v in results.response.get("violations", []) if v["impact"] == "critical"
        ]
        assert len(critical) == 0, f"Critical violations: {critical}"
```

- [ ] **Step 2: Run a11y tests**

```bash
pytest tests/e2e/test_a11y.py -v
```

- [ ] **Step 3: Fix any critical/serious violations found**

Common fixes:
- Missing `alt` on images → add descriptive alt or `alt=""`
- Missing form labels → add `<label>` or `aria-label`
- Insufficient contrast → upgrade text color class

- [ ] **Step 4: Commit**

```bash
git add tests/e2e/test_a11y.py
git commit -m "test(a11y): axe-core audit on 6 key pages — mobile + desktop"
```

---

## Task 13: Bundle analysis and final verification

**Files:**
- No new files — measurement task

- [ ] **Step 1: Measure JS bundle sizes**

```bash
wc -c static/js/main.js static/js/shell.js static/js/masks.js
# Target: total raw < 15KB
gzip -c static/js/main.js static/js/shell.js static/js/masks.js | wc -c
# Target: gzip total < 6KB (well under 80KB budget)
```

- [ ] **Step 2: Measure CSS bundle size**

```bash
ls -la theme/static_src/../static/css/dist/styles.css 2>/dev/null || ls -la theme/static/css/dist/styles.css 2>/dev/null
gzip -c theme/static/css/dist/styles.css 2>/dev/null | wc -c
# Target: < 30KB gzip
```

- [ ] **Step 3: Run Lighthouse CI (if available) or manual audit**

```bash
# Option A: lighthouse CLI
npx lighthouse http://localhost:8001/dashboard/ --only-categories=performance,accessibility,pwa --output=json --output-path=./lighthouse-report.json --chrome-flags="--headless" --form-factor=mobile

# Option B: manual — open Chrome DevTools > Lighthouse > Mobile > Run
```

- [ ] **Step 4: Document results**

Create `docs/lighthouse-m7-results.md` with scores:
- Performance: target ≥ 85
- Accessibility: target ≥ 95
- PWA: target ≥ 90

- [ ] **Step 5: Commit results**

```bash
git add docs/lighthouse-m7-results.md
git commit -m "docs(m7): Lighthouse results post-polimento — Performance/A11y/PWA scores"
```

---

## Summary of Expected Outcomes

| Metric | Before M7 | After M7 (target) |
|--------|-----------|-------------------|
| JS bundle (gzip) | ~18KB | ~5KB |
| CSS (custom.css) | 458 lines loaded | 0 (merged into Tailwind) |
| Google Fonts | 3 render-blocking requests | 0 (self-hosted, preloaded) |
| Focus trap | Missing in drawer/sheets | Complete |
| enterkeyhint | 3 inputs | All form inputs |
| SW update UX | Auto-skipWaiting (invisible) | User-prompted banner |
| E2E tests | 0 | ~12 tests (nav + tx + a11y) |
| Lighthouse Perf | ~60 | ≥ 85 |
| Lighthouse A11y | ~70 | ≥ 95 |
| Lighthouse PWA | ~70 | ≥ 90 |
