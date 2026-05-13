# Lighthouse Pós-Sprint 8 — Budgets / Plano Mensal

**Data da medição:** 2026-05-13
**URL auditada:** `http://localhost:8001/budgets/plano/2026/5/`
**Branch:** `feature/mobile-first-architecture` (commit `212550b`)
**Lighthouse:** 13.0.2 mobile / 4G slow / Moto G Power
**BenchmarkIndex:** 3642

## Scores

| Categoria | Baseline | Pós | Delta |
|---|---|---|---|
| Performance | 85 | **90** | **+5** ✅ |
| Accessibility | 100 | **100** | manter 🏆 |
| Best Practices | 100 | **100** | manter ✅ |
| SEO | 91 | 91 | manter |

## Core Web Vitals

| Métrica | Baseline | Pós | Delta |
|---|---|---|---|
| FCP | 2.52 s | **1.81 s** | **−28%** ✅ |
| LCP | 3.78 s | 3.46 s | **−8%** ✅ |
| TBT | 0 ms | **0 ms** | manter 🏆 |
| CLS | n/a | **0.00008** | excelente |
| SI | n/a | **1.81 s** | excelente |

## Análise

Esta era a página mais bem-feita do baseline (já tinha A11y 100
e TBT 0). Os ganhos vêm puramente do M0 (django-tailwind) +
M6 (a11y nas setas de navegação de mês + role/aria-valuenow nas
progress bars + num-tabular nos valores).

LCP element é o `<h1>Acompanhamento Mensal</h1>` no header —
texto leve, render delay de 182 ms (75% do LCP) é dominado pelo
font swap do Inter. Auto-host de Inter no M7 deve trazer LCP
próximo de 2.5 s.

## Achados persistentes

Idênticos às outras páginas (CSS render-blocking, avatar JPEG não
otimizado, cache headers). Tratamento M7.

## Total bytes

486 KiB (vs 532 KiB baseline). **−9%** ✅
