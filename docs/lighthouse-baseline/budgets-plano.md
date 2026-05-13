# Lighthouse Baseline — Wizard de Planejamento Mensal

**Data da medição:** 2026-05-12
**Branch:** `main` (commit anterior à Sprint 8)
**URL auditada:** `http://127.0.0.1:8001/budgets/plano/2026/5/`
**Lighthouse:** 13.0.2 (modo Navigation)
**Viewport emulado:** 412 × 823 px @ DPR 1.75
**Throttling:** 4G simulado

## Scores por categoria

| Categoria | Score |
|---|---|
| Performance | **85** ✨ |
| Accessibility | **100** 🏆 |
| Best Practices | **100** 🏆 |
| SEO | **90** |

> ✨ **Esta é a melhor tela do sistema em qualidade técnica.** Vai
> servir como referência arquitetural durante o M6 (refactor das
> demais telas de budgets/planning).

## Core Web Vitals & metrics

| Métrica | Valor | Score |
|---|---|---|
| First Contentful Paint (FCP) | 2.52 s | 0.66 |
| Largest Contentful Paint (LCP) | 3.78 s | 0.56 |
| Total Blocking Time (TBT) | **0 ms** 🏆 | 1.00 |
| Cumulative Layout Shift (CLS) | 0 | 1.00 |
| Speed Index | 2.52 s | 0.98 |
| Time to Interactive (TTI) | 3.78 s | 0.90 |

## Top oportunidades

| Oportunidade | Economia | Métrica afetada |
|---|---|---|
| Render-blocking requests | **1.560 ms** | FCP, LCP |
| Reduce unused JS | 1.000 KiB | — |
| Cache lifetimes | 305 KiB | LCP |
| Minify JS | 132 KiB | — |
| Reduce unused CSS | 22 KiB | — |

### Render-blocking detalhado

| Resource | Transfer | Blocking |
|---|---|---|
| `cdn.tailwindcss.com/3.4.17` | 126.8 KB | **820 ms** |
| Google Fonts (Inter) | 1.4 KB | 981 ms |
| `static/css/custom.css` | 12.4 KB | 163 ms |

> Mesmo padrão das outras telas. M0 cura tudo.

## Acessibilidade — 100/100 🏆

Esta página passa todos os checks de a11y do Lighthouse:

- ✅ heading-order correto (H1 "Acompanhamento Mensal" como LCP)
- ✅ landmark-one-main presente
- ✅ html-has-lang válido
- ✅ button-name, link-name, color-contrast OK
- ✅ Não há selects sem label
- ✅ list/listitem corretos
- ✅ meta-viewport sem `user-scalable=no`

**Implicação:** o template `monthly_plan.html` (ou similar) tem boas
práticas que devem ser **replicadas no resto do sistema** durante
M2/M4/M6.

## Best Practices — 100/100 🏆

- ✅ Doctype, charset
- ✅ Sem deprecated APIs
- ✅ Sem cookies de terceiros
- ✅ Sem erros no console
- ✅ Sem permissões de geolocation/notification on load
- ✅ Inputs aceitam paste

## DOM stats

- Total elements: **351**
- Max depth: 12
- Most children: 9 (mobile menu)

## Bytes — distribuição

| Tipo | Requests | Transfer |
|---|---|---|
| Image | 1 | 256 KiB (avatar) |
| Script | 3 | 168 KiB |
| Document | 1 | 50 KiB |
| Font | 1 | 47 KiB |
| Stylesheet | 3 | 14 KiB |
| **Total** | **11** | **532 KiB** |

> Mais leve que dashboard (606 KiB) e transactions (565 KiB).

### `main.js` — uso real

- Transfer: 42.7 KiB
- **Não usado: 33.8 KiB (79%)**

> Mesmo padrão de desperdício das outras telas, mas aqui não impacta
> TBT por algum motivo (provavelmente menos handlers ativos).

## Long tasks (top 5)

| Task | Duration | Origem |
|---|---|---|
| `main.js` execution | 320 ms | Background |
| Tailwind CDN | 190 ms | M0 resolve |
| Chrome extension | 111 ms | Ignorar |
| Tailwind CDN | 102 ms | M0 resolve |
| `main.js` follow-up | 69 ms | — |

## LCP element

```html
<h1 class="text-3xl font-bold text-white">Acompanhamento Mensal</h1>
```
**Path:** `div.max-w-4xl > div.mb-6 > div > h1.text-3xl`
**LCP breakdown:** 90ms TTB + 335ms render delay = 425ms observed
LCP (lab apontou 3.78s simulado por Lantern; o observed é o valor
real de campo).

## Recomendações específicas para M6

Quando refatorar as outras telas de budgets/planning, manter o
padrão arquitetural deste template:

1. **H1 como primeiro elemento de conteúdo** (LCP otimizado)
2. **Sem selects soltos** (todos têm label/aria)
3. **DOM enxuto** (351 elementos vs 364 em transactions com modal
   embutido)
4. **Sem JS bloqueante após render** (TBT=0)
5. **Color-contrast respeitado** em todos os botões
