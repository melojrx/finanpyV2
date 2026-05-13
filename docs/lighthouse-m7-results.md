# M7 — Bundle Analysis & Performance Results

**Date:** 2026-05-13
**Branch:** feature/m7-polimento-perf-a11y

## Bundle Sizes

| Asset | Before M7 | After M7 | Target | Status |
|-------|-----------|----------|--------|--------|
| JS total (gzip) | ~18 KB | **4.0 KB** | ≤ 80 KB | ✅ |
| JS total (raw) | ~60 KB | **14.4 KB** | — | ✅ |
| CSS Tailwind (gzip) | unknown | **12.6 KB** | ≤ 30 KB | ✅ |
| CSS custom.css | 458 lines | **0 (deleted)** | — | ✅ |
| Google Fonts requests | 3 (render-blocking) | **0 (self-hosted)** | 0 | ✅ |
| Font file (Inter var) | CDN ~100KB+ | **352 KB local (preloaded)** | — | ✅ |

## JS Breakdown

| File | Raw | Purpose |
|------|-----|---------|
| main.js | 1.7 KB | CurrencyFormatter + FinancialUtils |
| shell.js | 10.9 KB | SW reg, drawer, sheets, toasts, focus trap |
| masks.js | 1.5 KB | Input masks |

## Performance Improvements Applied

1. **Fonts:** Self-hosted Inter variable woff2 with `font-display: swap` + `<link rel="preload">`
2. **JS:** Removed 1180 lines of dead code from main.js (44KB → 1.7KB)
3. **CSS:** Migrated custom.css to Tailwind `@layer components`, deleted legacy file
4. **SW:** Version-based precache revisions, removed auto-skipWaiting

## Accessibility Improvements Applied

1. **280 SVGs** — added `aria-hidden="true"` to all decorative icons
2. **Skip-to-content** link added to base.html
3. **Contrast** — upgraded 84 instances of `text-gray-500` → `text-gray-400` (4.5:1+ on dark)
4. **Focus trap** — drawer and bottom-sheets now trap Tab focus + set `inert` on background
5. **enterkeyhint** — added to all form inputs (accounts, categories, goals, profiles)
6. **inputmode** — `decimal` on all monetary inputs, `email`/`tel` where appropriate
7. **aria-current="page"** — already present on bottom-nav (verified)
8. **SW update banner** — `role="alert"` for screen reader announcement
9. **Sync toast** — `role="status"` for polite announcement

## Test Infrastructure

- Playwright + axe-core configured (pytest)
- 6 navigation tests (mobile nav, drawer, FAB)
- 2 transaction flow tests (form fill, FAB trigger)
- 7 accessibility tests (axe-core on 6 pages mobile + 1 desktop)

## Lighthouse Audit (pending manual run)

Run with:
```bash
npx lighthouse http://localhost:8001/dashboard/ \
  --only-categories=performance,accessibility,pwa \
  --form-factor=mobile \
  --chrome-flags="--headless"
```

**Expected scores based on changes:**
- Performance: ≥ 85 (eliminated render-blocking fonts, reduced JS 75%, CSS optimized)
- Accessibility: ≥ 95 (aria-hidden, contrast, focus trap, skip-link, enterkeyhint)
- PWA: ≥ 90 (manifest, SW, offline page, icons — all from M1)
