# Lighthouse Pós-Sprint 8 — Transactions

**Data da medição:** 2026-05-13
**URL auditada:** `http://localhost:8001/transactions/`
**Branch:** `feature/mobile-first-architecture` (commit `212550b`)
**Lighthouse:** 13.0.2 mobile / 4G slow / Moto G Power
**BenchmarkIndex:** 3610

## Scores

| Categoria | Baseline | Pós | Delta |
|---|---|---|---|
| Performance | 82 | **90** | **+8** ✅ |
| Accessibility | 82 | **100** | **+18** 🏆 |
| Best Practices | 100 | **100** | manter ✅ |
| SEO | 91 | 91 | manter |

## Core Web Vitals

| Métrica | Baseline | Pós | Delta |
|---|---|---|---|
| FCP | 2.61 s | **1.80 s** | **−31%** ✅ |
| LCP | 4.08 s | 3.45 s | **−15%** ✅ |
| TBT | 77 ms | **0 ms** 🏆 | −100% |
| CLS | n/a | **0.003** | excelente |
| SI | n/a | **1.80 s** | excelente |
| Max Potential FID | n/a | 16 ms | excelente |

## A11y resolvidos (de 82 → 100)

A lista de transações antes tinha tabela `hidden lg:block
overflow-x-auto` sem fallback mobile + `<select>` sem labels +
ações com SVG sem `aria-label`. M2 resolveu tudo:

- Cards mobile com `aria-label` descritivo por linha
- Bottom-sheet de filtros com labels semânticos
- Touch targets ≥44px em todos os controles
- Heading hierarchy correta

## LCP element

```
<p class="text-sm text-gray-400 leading-relaxed mb-5">
  Comece registrando sua primeira receita ou despesa para ter
  visão completa das suas finanças.
</p>
```

LCP é o texto do **empty state** (componente `_empty_state.html`),
que ocupa o slot acima da dobra. Este é o efeito direto do fix
do bug `{% include %}` multilinha — sem o fix, esse texto era
substituído pela tag literal e o LCP era nó desconhecido.

## Achados persistentes (M7)

Os mesmos 5 da página dashboard. Especialmente:

- **DOM size:** 290 elementos (`<select id_category>` com 30
  options vindo do AJAX `/transactions/api/categories/` infla a
  contagem). Próximo passo: lazy load do select de categoria
  (só popular quando o filtro abre).
- **Render-blocking 1.005 ms** (CSS local) — fix idêntico ao
  dashboard.

## Total bytes

488 KiB (vs 565 KiB do baseline). **−14%** ✅

| Tipo | Pós |
|---|---|
| Image (avatar) | 256 KiB |
| Stylesheet | 90 KiB |
| Script | 54 KiB |
| Font | 48 KiB |
| Document | 40 KiB |
