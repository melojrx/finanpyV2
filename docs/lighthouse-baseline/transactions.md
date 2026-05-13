# Lighthouse Baseline — Lista de Transações

**Data da medição:** 2026-05-12
**Branch:** `main` (commit anterior à Sprint 8)
**URL auditada:** `http://127.0.0.1:8001/transactions/`
**Lighthouse:** 13.0.2 (modo Navigation)
**Viewport emulado:** 412 × 823 px @ DPR 1.75
**Throttling:** 4G simulado (RTT 150 ms, downlink 1.474 Kbps,
CPU slowdown 4×)

> Run warning: extensões do Chrome influenciaram a medição. Ainda assim
> os números são úteis pois pioram igualmente as 3 telas da comparação,
> e os issues estruturais (a11y, render-blocking) independem da
> presença de extensões.

## Scores por categoria

| Categoria | Score |
|---|---|
| Performance | **82** |
| Accessibility | **82** ⚠️ (regressão vs dashboard 87) |
| Best Practices | **100** ✅ |
| SEO | **90** |

## Core Web Vitals & metrics

| Métrica | Valor | Score |
|---|---|---|
| First Contentful Paint (FCP) | 2.61 s | 0.63 |
| Largest Contentful Paint (LCP) | 4.08 s | 0.47 |
| Total Blocking Time (TBT) | 77 ms ✅ | 0.99 |
| Cumulative Layout Shift (CLS) | 0.000005 ⚠️ | 1.00 |
| Speed Index | 2.61 s | 0.97 |
| Time to Interactive (TTI) | 4.08 s | 0.87 |
| Time to First Byte (TTB) | 22 ms ✅ | — |

## Top oportunidades

| Oportunidade | Economia | Métrica afetada |
|---|---|---|
| Render-blocking requests | **1.550 ms** | FCP, LCP |
| Reduce unused JS | 1.000 KiB | LCP |
| Cache lifetimes | 305 KiB | LCP |
| Minify JS | 137 KiB | — |
| Reduce unused CSS | 10 KiB | — |
| Minify CSS | 4 KiB | — |

### Render-blocking detalhado

| Resource | Transfer | Blocking |
|---|---|---|
| `cdn.tailwindcss.com/3.4.17` | 126.7 KB | **818 ms** |
| Google Fonts (Inter) | 1 KB | 859 ms |
| `static/css/custom.css` | 12.4 KB | 312 ms |

## Issues de Acessibilidade

### `color-contrast` ❌ peso 7 — sério

**Problema sistêmico:** botões `bg-primary-600` (`#0284c7`) com texto
branco têm contraste **4.09:1**, abaixo do mínimo WCAG AA (4.5:1).

```
<button class="quick-action-btn bg-primary-600 hover:bg-primary-700
               text-white px-6 py-2 ...">
  Aplicar Filtros
</button>
```

**Elementos afetados** (apenas os 2 visíveis acima do fold; o problema
provavelmente atinge outros lugares):

1. `div.filter-card > form > div > button.quick-action-btn` — "Aplicar
   Filtros" (40×182px)
2. `div.transaction-card > div > div > button.quick-action-btn` —
   "Rápida" (36×101px)

**Solução:** escurecer o `primary-600` ou clarear o texto, ou trocar
ambos. Possíveis alternativas que atendem 4.5:1:

- `bg-primary-700` (`#0369a1`) com texto branco → contraste 5.39:1 ✅
- Manter `bg-primary-600` mas adicionar `font-weight: 600` ou maior
  (textos negrito/grandes têm threshold 3:1)

**Sprint:** M0 (afeta o tema todo — definir cor base correta antes
de migrar para django-tailwind) ou no design tokens (`tokens.css`).
Esta correção arruma de uma vez **todos os botões primary do
sistema**.

### `select-name` ❌ peso 10 — crítico × 3

Três selects sem `<label>` associado, `aria-label`, nem `title`:

| Select | id | Conteúdo |
|---|---|---|
| Tipo | `#id_transaction_type` | Todos / Receita / Despesa |
| Conta | `#id_account` | Todas as contas |
| Categoria | `#id_category` | 30 opções (hierarquia completa) |

**Path comum:** `form.space-y-4 > div.grid > div > select.form-select`

**Sprint:** M2 (refactor `transaction_list.html`).

### `heading-order` ❌ peso 3

`<h3>Filtros Avançados</h3>` aparece antes de qualquer H2 (só existe
H1 na top-bar). DOM jumps direto de H1 → H3.

**Sprint:** M2.

## DOM stats

- Total elements: **364**
- Max depth: 12
- Most children: 30 (o `select#id_category` com hierarquia inteira)

> Sugestão: o select com 30 opções vai ficar pesado em mobile. No M2,
> considerar **autocomplete searchable** (dropdown com filtro) em
> vez de `<select>` nativo. Resolve UX e reduz DOM.

## Bytes — distribuição

| Tipo | Requests | Transfer |
|---|---|---|
| Image | 1 | 256 KiB |
| Script | 3 | 168 KiB |
| Document | 1 | 79 KiB |
| Font | 1 | 47 KiB |
| Stylesheet | 3 | 14 KiB |
| Other | 3 | 4 KiB |
| **Total** | **12** | **565 KiB** |

> Repare: 79 KiB de **document** — esse template está pesado (vs 49 KiB
> do dashboard). Justifica-se pelo modal de "transação rápida" inline.
> No M2/M3, mover lógica do modal para componente separado e/ou
> defer reduz substancialmente.

### `main.js` — uso real

- Transfer: 42.7 KiB
- **Não usado: 33.8 KiB (79%)**

## Long tasks (top 5)

| Task | Duration | Origem |
|---|---|---|
| `main.js` execution | **317 ms** | Init quick-transaction modal |
| Web extension | 208 ms | Chrome extension (ignorar) |
| Tailwind CDN | 88 ms | Resolverá no M0 |

## Layout shift residual

Único shift de 0.000005 (CLS=0 efetivo) causado pelo carregamento
do woff2 da Inter via Google Fonts. Não afeta o score, mas reforça
a recomendação de **auto-hospedar a fonte** no M0/M1.

## Endpoint `/transactions/api/categories/` chamado 2×

Duplicidade detectada: a API de categorias é chamada duas vezes em
sequência (provavelmente um por filtros, um pelo modal). Cada
request gasta ~25 ms.

**Sprint:** M3/M5 (consolidar em uma chamada compartilhada com
estado em sessionStorage).
