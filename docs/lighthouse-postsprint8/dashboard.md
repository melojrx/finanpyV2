# Lighthouse Pós-Sprint 8 — Dashboard

**Data da medição:** 2026-05-13
**Branch:** `feature/mobile-first-architecture` (commit `212550b` — pós M0+M1+M2+M3+M4+M5+M6+fix `{% include %}`)
**URL auditada:** `http://localhost:8001/dashboard/`
**Usuário autenticado:** `jrmeloafrf` (Token Auth)
**Lighthouse:** 13.0.2 (modo Navigation)
**User-Agent emulado:** Moto G Power (2022) — Android 11
**Viewport emulado:** 412 × 823 px @ DPR 1.75
**Throttling:** 4G simulado (RTT 150 ms, downlink 1.474 Kbps,
CPU slowdown 4×)
**BenchmarkIndex:** 3711

> Esta é a foto **pós-refactor mobile-first** comparada com
> `docs/lighthouse-baseline/dashboard.md`.

## Scores por categoria

| Categoria | Baseline | Pós-Sprint 8 | Delta |
|---|---|---|---|
| Performance | 72 | **89** | **+17** ✅ |
| Accessibility | 87 | **100** | **+13** 🏆 |
| Best Practices | 96 | **100** | **+4** 🏆 |
| SEO | 90 | 91 | +1 |

## Core Web Vitals & metrics

| Métrica | Baseline | Pós | Delta | Threshold p10 |
|---|---|---|---|---|
| FCP | 2.97 s | **1.98 s** | **−33%** ✅ | 1.8 s |
| LCP | 4.22 s | 3.49 s | **−17%** ✅ | 2.5 s |
| TBT | 367 ms | **27 ms** | **−93%** 🏆 | 200 ms |
| CLS | 0 | **0.0003** | manter ✅ | 0.1 |
| Speed Index | 2.97 s | **1.98 s** | **−33%** ✅ | 3.387 s |
| TTI | 4.22 s | 3.49 s | −17% ✅ | — |
| Max Potential FID | 292 ms | **81 ms** | **−72%** ✅ | — |
| TTFB | 41 ms | 16 ms | −61% ✅ | 600 ms |

## O que melhorou drasticamente

### 1. Render-blocking reduzido de 1.900 ms → 1.150 ms (M0+M4)

| Resource | Baseline blocking | Pós blocking | Delta |
|---|---|---|---|
| Tailwind CDN (3.4.17) | **818 ms** | 0 ms | **−100%** 🏆 |
| Chart.js | **1.520 ms** | 0 ms (lazy) | **−100%** 🏆 |
| date-fns CommonJS | 150 ms | 0 ms (removido) | **−100%** 🏆 |
| Inter (Google Fonts) | 869 ms | 977 ms | similar |
| custom.css | 159 ms | 473 ms | piorou (ver §A1) |
| **dist/styles.css (django-tailwind)** | n/a | 1.224 ms | novo (ver §A1) |

**Análise:** o ganho-chave foi remover Tailwind CDN (M0) e Chart.js
(M4 — virou lazy via `IntersectionObserver`). O CSS local
substituto entrou no caminho crítico mas é menor e cacheável.

### 2. TBT 367 ms → 27 ms (−93%)

O Chart.js síncrono dominava o main thread no baseline.
Agora ele só executa **depois** do FCP/LCP, fora do janela de TBT.

### 3. Acessibilidade 87 → 100 (resolvidos)

| Issue | Status |
|---|---|
| `heading-order` (H3 sem H2) | ✅ Resolvido — H1 + H2 hierárquicos no M4 |
| `select-name` (filtro 6 meses sem label) | ✅ Resolvido — substituído por segmented control |
| `identical-links-same-purpose` | ✅ Resolvido — `aria-label` distintivos |
| `target-size` | ✅ Touch targets ≥44×44px |
| Progress bars sem `aria-valuenow` | ✅ Resolvido em todas |

## Achados que persistem (M7 / fora do escopo)

### A1. Render-blocking dos CSS locais (M7)

`styles.css?v=...` (Tailwind buildado) bloqueia 1.224 ms +
`custom.css` 473 ms + `tokens.css` 173 ms = ~1.870 ms total.
**Total potencial de economia:** 1.150 ms (estimativa Lighthouse).

Soluções para M7:
- `<link rel="preload" as="style">` + carregamento async
- Critical CSS inline (above-the-fold) + resto via `media="print"
  onload="this.media='all'"`
- Auto-host de Inter (remove Google Fonts da chain de 977 ms)

### A2. Avatar 256 KiB sem cache + sem responsive (LCP saving 1.2 s)

```
url: /media/avatars/1/ce88b048-...jpeg
totalBytes: 255 KiB
displayedSize: 32×40 px
actualSize: 802×800 px
wastedBytes: 254 KiB (99% desperdiçado!)
```

Ações para M7:
- Resize para 96×96 (top-bar) + cache-control: 1 ano
- Conversão WebP/AVIF (50% economia adicional)
- `<img>` com `srcset` ou Django ImageField com thumbnails
  (`django-imagekit` ou `easy-thumbnails`)

### A3. main.js 79% não usado (33.8 KiB)

Persiste do baseline. **Mitigação no M7:** code-splitting por rota
(carregar só os módulos necessários).

### A4. CSS unused 70 KiB (94% do `custom.css`, 83% do `styles.css`)

Resolução parcial: o `custom.css` (12.4 KiB) está praticamente
inteiro inutilizado — pode ser deletado ou reduzido drasticamente.
O `styles.css` é gerado pelo Tailwind purge, então o "unused" é
só CSS que existe pra outras rotas (acceitável para SPA-like).

### A5. Avisos remanescentes

- `aria-allowed-role` (informativo): drawer com `role="dialog"`
  enquanto fechado (`aria-hidden=true`) — Lighthouse pede
  remover o role quando hidden. Severidade: minor.
- `label-content-name-mismatch`: top-bar e bottom-nav têm
  `aria-label="FinanPy — ir para dashboard"` enquanto o texto
  visível é só "FinanPy". Same destination, então `aria-label`
  funciona, mas Lighthouse experimental flag pede igualdade.

Ambos M7.

## Bytes — distribuição

| Tipo | Baseline | Pós | Delta |
|---|---|---|---|
| Image (avatar) | 256 KiB | 256 KiB | igual ❌ |
| Script | 249 KiB | 127 KiB | **−49%** ✅ |
| Stylesheet | 14 KiB | **88 KiB** | +528% (CSS local 72 KiB substituiu CDN remoto não-contado) |
| Font | 48 KiB | 48 KiB | igual |
| Document | 49 KiB | 43 KiB | −12% |
| **Total** | **606 KiB** | **561 KiB** | **−7%** ✅ |

> O script caiu 49% porque Chart.js agora é lazy (não conta no payload inicial).

## Network dependency tree

```
/dashboard/ (43 KiB, 17 ms server)
├─ Inter Tight (Google Fonts) ........... 601 ms ← longest chain
├─ @kurkle/color (Chart.js lazy) ........ 482 ms
├─ chart.js (lazy import) ............... 443 ms
├─ Inter (Google Fonts) ................. 319 ms
│  └─ Inter woff2 ...................... 452 ms
├─ styles.css (django-tailwind) ......... 54 ms
├─ tokens.css ........................... 50 ms
├─ custom.css ........................... 49 ms
└─ manifest.webmanifest ................. 53 ms
```

**Longest chain:** 601 ms (Inter Tight) — Inter via Google Fonts
ainda é o maior ofensor. Auto-host de Inter resolve no M7.

## Conclusão

✅ **Sprint 8 cumpriu o alvo do mobile-first refactor.**

| KPI técnico | Alvo | Atingido |
|---|---|---|
| Performance ≥85 | sim | **89** ✅ |
| Accessibility ≥95 | sim | **100** 🏆 |
| Best Practices ≥95 | sim | **100** 🏆 |
| LCP ≤2.5 s | parcial | 3.49 s (baseline 4.22 s, melhorou mas ainda alto) |
| FCP ≤1.8 s | quase | 1.98 s (faltou 200 ms) |
| TBT ≤200 ms | sim | **27 ms** 🏆 |

Os dois alvos não 100% atingidos (LCP, FCP) caem para o M7, com
soluções claras: auto-host de Inter + critical CSS + responsive
avatar.

A página é **PWA instalável** (Lighthouse 13 não mais lista PWA
como score, mas validei manualmente: manifest, ícones maskable,
service worker registrado, `display: standalone`, `share_target`,
`protocol_handlers`).
