# Lighthouse Baseline — Dashboard

**Data da medição:** 2026-05-12
**Branch:** `main` (commit anterior à Sprint 8)
**URL auditada:** `http://127.0.0.1:8001/dashboard/`
**Usuário autenticado:** `jrmeloafrf@gmail.com`
**Lighthouse:** 13.0.2 (modo Navigation)
**User-Agent emulado:** Moto G Power (2022) — Android 11
**Viewport emulado:** 412 × 823 px @ DPR 1.75
**Throttling:** 4G simulado (RTT 150 ms, downlink 1.474 Kbps,
CPU slowdown 4×)

> Esta é a foto do estado **anterior** ao refactor mobile-first.
> Será comparada com nova medição após o M7 (polimento) da Sprint 8.

## Scores por categoria

| Categoria | Score |
|---|---|
| Performance | **72** |
| Accessibility | **87** |
| Best Practices | **96** |
| SEO | **90** |
| PWA | n/a (Lighthouse 13 removeu a categoria) |

## Core Web Vitals & metrics

| Métrica | Valor | Score | Threshold p10 |
|---|---|---|---|
| First Contentful Paint (FCP) | 2.97 s | 0.50 | 1.8 s |
| Largest Contentful Paint (LCP) | 4.22 s | 0.44 | 2.5 s |
| Total Blocking Time (TBT) | 367 ms | 0.71 | 200 ms |
| Cumulative Layout Shift (CLS) | 0 | 1.00 | 0.1 |
| Speed Index | 2.97 s | 0.94 | 3.387 s |
| Time to Interactive (TTI) | 4.22 s | 0.85 | — |
| Max Potential FID | 292 ms | 0.38 | — |
| Time to First Byte (TTB) | 41 ms | ✅ | 600 ms |

## Top oportunidades (por economia estimada)

| Oportunidade | Economia estimada | Métrica afetada |
|---|---|---|
| **Render-blocking requests** | **1.900 ms** | FCP, LCP |
| **Reduce unused JavaScript** | 1.001 KiB | LCP |
| **Reduce unused CSS** | 21 KiB | — |
| **Cache lifetimes** | 312 KiB (avatar.jpeg sem cache) | LCP |
| **Minify JavaScript** | 132 KiB | LCP |
| **Minify CSS** | 4 KiB | — |

### Detalhamento — Render-blocking (M0 resolverá a maior parte)

| Resource | Transfer | Blocking |
|---|---|---|
| `https://cdn.jsdelivr.net/npm/chart.js` | 72.1 KB | **1.520 ms** |
| `https://fonts.googleapis.com/css2?...Inter` | 1 KB | 869 ms |
| `https://cdn.tailwindcss.com/3.4.17` | 126.7 KB | **818 ms** |
| `http://127.0.0.1:8001/static/css/custom.css` | 12.4 KB | 159 ms |
| `https://cdn.jsdelivr.net/npm/date-fns@2.29.3` | 5.4 KB | 150 ms |

> Apenas eliminar o Tailwind CDN (M0 — django-tailwind) já corta
> ~818 ms do critical path. Lazy-load do Chart.js (M4) corta mais
> 1.520 ms. Total potencial: **2.3 s de redução de FCP/LCP só com
> M0 + M4.**

## Issues de Acessibilidade detectados

### `heading-order` (peso 3) ❌

```
<h3 class="text-xl font-semibold text-white">Resumo Financeiro</h3>
```
**Path:** `div.lg:col-span-2 > div.card > div.flex > h3.text-xl`
**Problema:** H3 sem H1/H2 antecedendo na ordem do DOM.
**Sprint:** M4 (refactor dashboard).

### `select-name` (peso 10) ❌

```
<select class="bg-dark-700 text-gray-300 text-sm rounded-lg px-3 py-1
               border border-dark-600 ...">
  Últimos 6 meses / Últimos 3 meses / Este ano
</select>
```
**Path:** `div.card > div.flex > div.flex > select.bg-dark-700`
**Problema:** select sem label/aria-label/title.
**Severidade:** crítica.
**Sprint:** M4.

### `identical-links-same-purpose` ⚠️ (informativo)

Dois links com texto "Ver todas" apontando para `/transactions/` e
`/goals/`. Solução: `aria-label="Ver todas as transações"` /
`aria-label="Ver todas as metas"`.
**Sprint:** M4.

## Erros no console

### `Uncaught ReferenceError: exports is not defined` ❌

**Origem:** `https://cdn.jsdelivr.net/npm/date-fns@2.29.3/index.min.js`
**Causa:** build CommonJS sendo carregado direto no `<script>` do
browser (UMD/ESM seria o correto).
**Impacto:** date-fns inteiro provavelmente não está funcionando, mas
ainda assim faz parse e congestiona main thread em ~150 ms.
**Sprint:** M5 (limpeza do JS) ou M7 (polish). Avaliar **remoção total**
se não for usado de fato.

## Bytes — distribuição

| Tipo | Requests | Transfer |
|---|---|---|
| Image | 1 | 256 KiB (avatar JPEG) |
| Script | 5 | 249 KiB |
| Document | 1 | 49 KiB |
| Font | 1 | 48 KiB (Inter woff2) |
| Stylesheet | 3 | 14 KiB |
| Other | 2 | 4 KiB |
| **Total** | **13** | **606 KiB** |

### `main.js` — uso real

- Transfer: 42.7 KiB
- Resource: 42.6 KiB
- **Não usado: 33.8 KiB (79%)**
- Conclusão: o `main.js` carrega lógica de praticamente todas as
  páginas em todas as páginas. Code-splitting por rota cortaria
  ~80% do payload na home.

## Network dependency tree (caminho crítico)

```
/dashboard/ (49 KiB, 74 ms)
├─ Inter Tight (Google Fonts)         800 ms ← longest chain
├─ Inter (Google Fonts)               197 ms
│  └─ Inter woff2                     660 ms
├─ /transactions/api/categories/      644 ms
├─ /static/js/masks.js                124 ms
├─ /static/css/custom.css              79 ms
├─ chart.js                           100 ms
├─ date-fns                            99 ms
├─ /static/js/main.js                  81 ms
└─ tailwindcss/3.4.17                 436 ms
```

**Longest chain:** 800 ms (Inter Tight via Google Fonts).
**Mitigação no M0:** auto-host Inter via `@fontsource/inter` ou usar
fonts locais empacotadas com `django-tailwind`.

## Run warning relevante

```
There may be stored data affecting loading performance in this
location: IndexedDB. Audit this page in an incognito window to
prevent those resources from affecting your scores.
```

> Para a re-medição final (pós-M7), rodar em **janela anônima** para
> baseline limpo.

## Próximas medições

Repetir esse baseline após cada milestone:

| Milestone | URL adicional para medir |
|---|---|
| Pós-M0 | `/dashboard/` (validar redução do render-blocking) |
| Pós-M1 | `/dashboard/` + Lighthouse PWA flags (manifest, SW) |
| Pós-M4 | `/dashboard/` (validar charts lazy + snapshot endpoint) |
| Pós-M7 | `/dashboard/`, `/transactions/`, `/budgets/plano/` (relatório final comparativo) |
