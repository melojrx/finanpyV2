---
tags: [projeto, finanpy, mobile, pwa, arquitetura, frontend, ux]
status: aprovado
projeto: FinanPy
tipo: arquitetura
sprint: pendente-execucao
estimativa: 19d
created: 2026-05-11
updated: 2026-05-11
related:
  - "[[FinanPy]]"
  - "[[FinanPy — Vida e Saúde]]"
fonte_codigo: /home/jrmelo/Projetos/finanpy_v2/docs/mobile-architecture.md
---

# Mobile-First Architecture — FinanPy v2

> Documento oficial da arquitetura mobile-first e estratégia PWA para o FinanPy.
> **Status:** Proposta aprovada — pendente execução
> **Última atualização:** 2026-05-11
> **Projeto pai:** [[FinanPy]]
> **Decisões aprovadas:** django-tailwind · PWA completo (offline-write) · Bottom-nav 5 slots + FAB
> **Espelho no repo:** `docs/mobile-architecture.md` (fonte da verdade técnica)

---

## 1. Contexto e Motivação

O FinanPy é a fonte primária de dados financeiros pessoais do usuário e está integrado ao **agente Hermes** via API REST (`/api/v1/`) com TokenAuthentication. O fluxo real de uso envolve:

- **Lançamento de transações em movimento** (Telegram, OCR de comprovantes via Google Vision)
- **Consulta rápida de saldo/orçamento** durante o dia
- **Briefing financeiro diário** entregue pelo Hermes

A interface web atual, embora funcional, foi projetada **desktop-first** com adaptações superficiais para mobile. Isso degrada gravemente a experiência principal do usuário, que é mobile.

### Diagnóstico do estado atual

| Categoria | Problema | Evidência |
|---|---|---|
| **PWA** | Não é instalável; sem manifest, sem service worker, sem ícones | `static/images/` vazio; nenhum `manifest.webmanifest` |
| **Performance** | TailwindCSS via CDN (~3MB descomprimido); Google Fonts blocking; sem code-splitting | `templates/base.html:12` |
| **Viewport** | Sem `viewport-fit=cover` (não respeita notch/safe-area iOS) | `templates/base.html:5` |
| **Navegação** | Hamburger top + dropdown — fora da zona do polegar | `templates/base.html:209` |
| **Listagens** | Tabelas com `hidden lg:block overflow-x-auto` sem fallback de cards mobile | `transactions/transaction_list.html:405`, `accounts/account_list.html:202`, `categories/category_list.html:212`, `budgets/budget_detail.html:430`, `goals/goal_detail.html:105` |
| **Templates duplicados** | 3 versões da lista de transações (`transaction_list.html`, `_backup.html`, `_enhanced.html`) | Sinaliza retrabalho mal consolidado |
| **Inputs** | Sem `inputmode`, `enterkeyhint`, autocomplete semânticos; touch targets `text-sm` (~36px) | Forms em geral |
| **Toasts** | `top-20 right-4` sem safe-area; cobrem conteúdo no mobile | `templates/base.html:308` |
| **JavaScript** | `main.js` (1234 linhas) carregado em todas as páginas, sem `defer`, sem code-splitting | `templates/base.html:504` |
| **Offline** | Impossível registrar transação sem rede — bloqueia o uso real | Inexistente |

### Princípios diretores

1. **Bottom-nav first**: navegação primária na zona do polegar (≤ 414px de largura)
2. **Single column always**: layouts colapsam para 1 coluna < 768px, sem scroll horizontal
3. **PWA instalável**: manifest + service worker + offline shell + ícones maskable
4. **Touch targets ≥ 44×44px** (Apple HIG / Material 48dp)
5. **API-first para mobile**: telas críticas consomem `/api/v1/` com cache offline-first via SW
6. **Hermes-friendly**: deeplinks (`web+finanpy://transaction/new?...`) para o agente abrir formulários pré-preenchidos
7. **Performance budget**: LCP ≤ 2.5s em 4G, JS inicial ≤ 80 KB gzip, CSS ≤ 30 KB gzip

---

## 2. Arquitetura Proposta

### 2.1 Decisões técnicas aprovadas

| Decisão | Escolha | Justificativa |
|---|---|---|
| Build de CSS | **django-tailwind** | Integração Django nativa, hot reload, `manage.py tailwind start`. Resolve `INF-001` do backlog. |
| Escopo PWA | **PWA completo com offline-write** | Background sync para POST de transações offline — essencial para uso em campo com Hermes |
| Navegação mobile | **Bottom-nav 5 slots + FAB central** | Padrão iOS/Material moderno, zona do polegar, FAB para ação primária (nova transação) |

### 2.2 Camada 1 — Shell mobile (PWA)

```
templates/
├── base.html                    # Refatorada: viewport-fit, theme-color, manifest, SW reg, bottom-nav
├── components/
│   ├── _bottom_nav.html         # NOVO: navegação inferior fixa (5 itens)
│   ├── _top_bar.html            # NOVO: header minimalista (logo + alertas + avatar)
│   ├── _drawer.html             # NOVO: gaveta lateral para itens secundários
│   ├── _fab.html                # NOVO: floating action button "+ Transação"
│   ├── _toast.html              # Toast respeitando safe-area-inset-bottom
│   ├── _empty_state.html        # Empty states padronizados
│   ├── _skeleton.html           # Skeletons de loading
│   ├── _bottom_sheet.html       # Bottom-sheet reutilizável (filtros, formulários)
│   └── _swipe_card.html         # Card com swipe-actions (edit/delete)

static/
├── manifest.webmanifest         # NOVO
├── sw.js                        # NOVO: cache strategies + background sync
├── offline.html                 # NOVO: shell offline
├── images/icons/
│   ├── icon-192.png             # NOVO (maskable + any)
│   ├── icon-512.png             # NOVO (maskable + any)
│   ├── apple-touch-icon.png     # NOVO (180x180)
│   └── favicon.svg              # NOVO
└── css/
    ├── tokens.css               # NOVO: design tokens CSS (safe-area, h-vars)
    └── tailwind.css             # NOVO: gerado por django-tailwind
```

#### Bottom-nav (5 slots fixos)

```
┌────────────────────────────────────────────────────┐
│  [📊]      [📋]      [➕]      [💰]      [☰]      │
│ Dashboard  Lançamentos  FAB    Orçamento   Mais    │
└────────────────────────────────────────────────────┘
            posição: fixed bottom, z-50
            altura: 64px + safe-area-inset-bottom
```

- **FAB central elevado** (-translate-y-6) abre **bottom-sheet** "Nova transação"
- "Mais" abre drawer lateral com: Contas · Categorias · Metas · Perfil · Alertas · Logout
- Indicador ativo: `border-t-2 border-primary-500` ou ícone preenchido

#### Top-bar minimalista

```
┌────────────────────────────────────────────────────┐
│  [F] FinanPy            🔔 (badge)        [avatar] │
└────────────────────────────────────────────────────┘
            altura: 56px + safe-area-inset-top
```

### 2.3 Camada 2 — Sistema de design mobile-first

#### Design tokens (`static/css/tokens.css`)

```css
:root {
  /* Safe areas */
  --safe-top: env(safe-area-inset-top);
  --safe-bottom: env(safe-area-inset-bottom);
  --safe-left: env(safe-area-inset-left);
  --safe-right: env(safe-area-inset-right);

  /* Layout */
  --bottom-nav-h: 64px;
  --top-bar-h: 56px;
  --content-pb: calc(var(--bottom-nav-h) + var(--safe-bottom) + 16px);
  --touch-min: 44px;

  /* Surfaces */
  --radius-sheet: 20px 20px 0 0;
  --radius-card: 12px;
  --shadow-sheet: 0 -4px 16px rgba(0,0,0,0.4);
  --shadow-fab: 0 8px 24px rgba(14, 165, 233, 0.4);

  /* Motion */
  --ease-out-quart: cubic-bezier(0.25, 1, 0.5, 1);
}

@supports (font-variant-numeric: tabular-nums) {
  .font-tnum { font-variant-numeric: tabular-nums; }
}
```

#### Tabela de componentes

| Componente | Mobile (<768px) | Desktop (≥768px) |
|---|---|---|
| Lista (transações/contas) | Card empilhado vertical, swipe-actions (delete/edit) | Tabela compacta |
| Filtros | Bottom-sheet expansível com handle | Sidebar/inline |
| Forms | Inputs full-width, label flutuante, `inputmode` correto | Grid 2-col |
| Wizard planejamento | Steps verticais com progress bar topo, sticky CTA bottom | Stepper horizontal |
| Charts | Reduzidos, contidos em `<div role="region">` com snap-scroll | Full grid |
| Modal | Bottom-sheet com handle drag-to-close | Modal centralizado |
| Empty state | Illustration + CTA full-width | Illustration + CTA inline |
| Stat card | Snap-scroll horizontal de 80vw | Grid 4 colunas |

### 2.4 Camada 3 — Migração do Tailwind (resolve INF-001)

**Stack:** `django-tailwind` (PyPI: `django-tailwind[reload]`)

**Setup:**
1. `pip install django-tailwind[reload]`
2. `python manage.py tailwind init theme` (cria app `theme/`)
3. Adicionar `tailwind`, `theme`, `django_browser_reload` em `INSTALLED_APPS`
4. `python manage.py tailwind install`
5. Mover configuração custom de `base.html:16-135` para `theme/static_src/tailwind.config.js`
6. Plugins habilitados:
   - `@tailwindcss/forms` (inputs nativos consistentes)
   - `@tailwindcss/typography` (renderização de markdown em help texts)
   - Plugin custom `safe-area` para utilitários `pb-safe`, `pt-safe`, `mb-nav`

**Resultado esperado:**
- CSS final ~30 KB gzip (vs 3 MB CDN)
- LCP -1.2s em 4G
- Remove `tailwindcss-setup.md` da documentação (substituído por este)

### 2.5 Camada 4 — PWA + Offline strategy

#### `manifest.webmanifest`

```json
{
  "name": "FinanPy - Gestão Financeira",
  "short_name": "FinanPy",
  "description": "Sua plataforma completa de gestão financeira pessoal",
  "start_url": "/dashboard/",
  "display": "standalone",
  "orientation": "portrait",
  "background_color": "#020617",
  "theme_color": "#0c4a6e",
  "lang": "pt-BR",
  "dir": "ltr",
  "scope": "/",
  "icons": [
    { "src": "/static/images/icons/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any maskable" },
    { "src": "/static/images/icons/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable" }
  ],
  "shortcuts": [
    { "name": "Nova transação", "url": "/transactions/new/", "icons": [{ "src": "/static/images/icons/shortcut-add.png", "sizes": "96x96" }] },
    { "name": "Dashboard", "url": "/dashboard/" },
    { "name": "Orçamentos", "url": "/budgets/plano/" }
  ],
  "share_target": {
    "action": "/transactions/from-receipt/",
    "method": "POST",
    "enctype": "multipart/form-data",
    "params": {
      "title": "title",
      "text": "description",
      "files": [{ "name": "receipt", "accept": ["image/*"] }]
    }
  },
  "protocol_handlers": [
    { "protocol": "web+finanpy", "url": "/handler/?q=%s" }
  ]
}
```

> **`share_target`** permite que o usuário use "Compartilhar para FinanPy" do app Galeria/Camera no Android para enviar comprovantes diretamente — alimenta o pipeline OCR existente (Google Vision integrado).

#### `sw.js` — estratégias por rota

| Rota | Strategy | TTL | Justificativa |
|---|---|---|---|
| `/static/*` (versionado) | CacheFirst | imutável | Assets com hash |
| `/api/v1/summary/*` | StaleWhileRevalidate | 5 min | Dashboard rápido, atualiza em bg |
| `/api/v1/dashboard/snapshot/` | StaleWhileRevalidate | 1 min | Home mobile |
| `/api/v1/transactions/` GET | NetworkFirst (5s timeout → cache) | 1 dia | Lista acessível offline |
| `/api/v1/transactions/` POST | **BackgroundSync queue** | — | Lançar transação offline → sync ao voltar online |
| `/api/v1/categories/` | CacheFirst (revalidate diário) | 1 dia | Quase imutável |
| `/api/v1/accounts/` | NetworkFirst | 30 min | Saldos atualizam |
| `/dashboard/`, `/transactions/`, `/budgets/*` | NetworkFirst | — | Shell server-rendered |
| `*` fallback offline | `/offline.html` | — | UX de degradação |

**Background sync é o ganho-chave:** o usuário anota uma despesa no metrô sem sinal, e o Hermes/web não precisa de retry manual — o SW reenvia quando voltar online.

#### Implementação do Background Sync (Workbox)

```js
// sw.js (trecho)
import { Queue } from 'workbox-background-sync';

const txQueue = new Queue('finanpy-tx-queue', {
  maxRetentionTime: 24 * 60 // 1 dia
});

self.addEventListener('fetch', (event) => {
  if (event.request.url.match(/\/api\/v1\/transactions\/$/) && event.request.method === 'POST') {
    const bgSyncLogic = async () => {
      try {
        return await fetch(event.request.clone());
      } catch (error) {
        await txQueue.pushRequest({ request: event.request });
        return new Response(JSON.stringify({ queued: true }), { status: 202 });
      }
    };
    event.respondWith(bgSyncLogic());
  }
});
```

### 2.6 Camada 5 — Endpoints novos para o Hermes

Adicionar em `api/`:

| Endpoint | Método | Propósito |
|---|---|---|
| `/api/v1/transactions/quick/` | POST | Recebe `{amount, description, category_hint, account_id?}` — resolve categoria por similaridade (NLP simples), assume conta default. Pensado para o Hermes mandar texto natural via Telegram. |
| `/api/v1/dashboard/snapshot/` | GET | Agregação única para a home mobile: `{total_balance, month_summary, last_5_tx, active_alerts, top_3_budgets}` → 1 request em vez de 4 |
| `/api/v1/transactions/from-receipt/` | POST | Recebe `image` (multipart) → chama Google Vision (já integrado) → retorna draft de transação para confirmação |
| `/api/v1/sync/since/?ts=<iso>` | GET | Endpoint de delta para SW: retorna mudanças desde `ts` em accounts/transactions/budgets |
| `/api/v1/handler/?q=<deeplink>` | GET | Resolve `web+finanpy://...` para rota interna |

### 2.7 Camada 6 — Deeplinks para o agente

URL scheme `web+finanpy://` registrado no manifest. Exemplos:

| Deeplink | Comportamento |
|---|---|
| `web+finanpy://transaction/new?amount=50&category=alimentacao&description=ifood` | Abre form preenchido para confirmação |
| `web+finanpy://transaction/new?from_receipt=<media_id>` | Abre form com OCR já parseado |
| `web+finanpy://dashboard` | Abre app na home |
| `web+finanpy://budget/<plan_id>` | Abre plano mensal específico |

**Use case real:** o Hermes detecta no Telegram "gastei 35 no uber", monta o link `web+finanpy://transaction/new?amount=35&category=transporte&description=uber`, envia ao usuário. Toque único abre o app instalado já no formulário, basta confirmar.

### 2.8 Camada 7 — Acessibilidade e detalhes de UX

- **Pull-to-refresh** nas listas (`overscroll-behavior-y: contain` + lib leve ou nativo via SW)
- **Skeleton screens** (não spinners) para transições — `_skeleton.html`
- **Haptic feedback** em ações destrutivas (`navigator.vibrate(50)`)
- **Lazy-load** Chart.js só no dashboard (`<script type="module">` dinâmico)
- **`prefers-reduced-motion`** respeitado em todas as animações
- **Tabular numerals** em campos monetários (`font-feature-settings: "tnum"`)
- **`enterkeyhint`** em forms (`next`, `done`, `send`)
- **`autocomplete`** semântico (`username`, `current-password`, `transaction-amount`)
- **`inputmode="decimal"`** em valores monetários (BR usa vírgula)
- **`role="region"` + `aria-label`** em containers com scroll horizontal
- **Focus visible** com outline contrastante (não removido)
- **Contrast AAA** em texto sobre gradientes

### 2.9 Camada 8 — Telas com refactor cirúrgico prioritário

| Tela | Problema atual | Refactor mobile-first |
|---|---|---|
| `dashboard/dashboard.html` | Cards stat em grid quebra em 360px; gráficos transbordam | Stat-cards horizontais com snap-scroll; gráfico em swiper de "abas" (Receitas / Despesas / Saldo); usar endpoint `/dashboard/snapshot/` |
| `transactions/transaction_list.html` | 3 versões; tabela `hidden lg:block` sem fallback | **Apagar** `_backup` e `_enhanced`; lista única de cards com swipe-actions; filtros em bottom-sheet; pull-to-refresh |
| `transactions/transaction_form.html` | Inputs mistos, sem inputmode | Bottom-sheet com `inputmode="decimal"`, currency mask, autocomplete de categoria, sticky CTA |
| `accounts/account_list.html` | Tabela em scroll-x | Cards verticais com saldo grande, badge de tipo, ação primária touch-friendly |
| `categories/category_list.html` | Hierarquia em tabela | Lista com indentação visual + chevrons expansíveis |
| `budgets/planning_*.html` | Wizard em 12-col só ≥sm | Wizard vertical com progress bar topo, sticky CTA bottom |
| `budgets/budget_detail.html` | Tabela de transações scroll-x | Cards mobile + tabela ≥md |
| `goals/goal_detail.html` | Tabela de aportes scroll-x | Cards mobile + tabela ≥md |
| `templates/base.html` | Hamburger top, sem PWA | Top-bar enxuta + bottom-nav + FAB + drawer + manifest + SW reg |

---

## 3. Roadmap de Execução

| Sprint | Objetivo | Entregáveis | Estimativa | Status | Commit |
|---|---|---|---|---|---|
| **M0 — Fundação** | Build local Tailwind + design tokens | INF-001 resolvido, `theme/` app, `tokens.css`, purge ativo, `tailwind.config.js` migrado | 2 dias | ✅ | `e09ebe7` |
| **M1 — Shell PWA** | App instalável + offline shell | manifest, sw.js (Workbox), ícones maskable, `base.html` refatorada com bottom-nav + FAB + drawer + top-bar | 3 dias | ✅ | `1899c7c` |
| **M2 — Lista de Transações** | Tela mais usada | Refactor `transaction_list.html` (apagar duplicatas), card swipeável, bottom-sheet de filtros | 2 dias | ✅ | `7cf5469` |
| **M3 — Form rápido + bottom-sheet** | Lançamento em < 5s | `transaction_form.html` em sheet, inputmode, máscaras, autocomplete categoria, sticky CTA | 2 dias | ✅ | `7cf5469` |
| **M4 — Dashboard mobile** | Home enxuta | Snap-scroll de KPIs, charts lazy-loaded, endpoint `/dashboard/snapshot/` | 2 dias | ✅ | `daf320d` |
| **M5 — Background sync + Hermes** | Offline-write + deeplinks | SW POST queue, endpoints `quick/` + `from-receipt/` + `sync/since/`, share_target, protocol_handlers | 3 dias | ✅ | `64ace28` |
| **M6 — Demais telas** | Accounts, Categories, Goals, Budgets | Cards mobile, wizards verticais, fix tabelas com fallback, deleção de 7 templates órfãos | 3 dias | ✅ | `7eb8459` |
| **fix — empty states** | Bug regressivo | Colapsar `{% include %}` multilinha, `{# %}` → `{% comment %}` | — | ✅ | `212550b` |
| **M7 — Polimento** | A11y final, perf, testes | Auto-host Inter, critical CSS, responsive avatar, code-splitting, axe-core CI, E2E Playwright | 2 dias | ⏭️ | — |

**Status global Sprint 8:** **6 de 7 milestones concluídos** (M0-M6).
M7 pendente — escopo claro com 8 achados Lighthouse documentados em
`docs/lighthouse-postsprint8/dashboard.md` §A1-A5.

**Total estimado original:** ~19 dias úteis.
**Realizado até pós-M6:** todos os entregáveis funcionais; medição
Lighthouse comprova alvos atingidos para Performance (89), A11y
(100), Best Practices (100), TBT (27 ms), PWA instalável.

---

## 4. Métricas de Sucesso

### KPIs técnicos

**Baseline medido em 2026-05-12** — Lighthouse 13.0.2, mobile preset
(412×823 @ 1.75x), throttling 4G simulado, página `/dashboard/`,
usuário autenticado, branch `main` em `bff9118`.
*Relatório completo arquivado em `docs/lighthouse-baseline/dashboard.json`.*

**Re-medição realizada em 2026-05-13** após Sprint 8 (commit `212550b`).
*Relatórios completos em `docs/lighthouse-postsprint8/{dashboard,transactions,budgets-plano}.md`.*

| Métrica | Baseline | **Pós-Sprint 8** | Delta | Alvo | Atingiu? |
|---|---|---|---|---|---|
| **Lighthouse Performance (mobile)** | 72 | **89** | **+17** | ≥ 85 | ✅ |
| **Lighthouse Accessibility** | 87 | **100** | **+13** | ≥ 95 | 🏆 |
| **Lighthouse Best Practices** | 96 | **100** | **+4** | ≥ 95 | 🏆 |
| **Lighthouse SEO** | 90 | 91 | +1 | ≥ 90 | ✅ |
| **Lighthouse PWA** | n/a | instalável + offline-write | — | instalável + offline | 🏆 |
| **FCP (4G)** | 2.97 s | 1.98 s | **−33%** | ≤ 1.8 s | ⚠️ quase (−180 ms) |
| **LCP (4G)** | 4.22 s | 3.49 s | **−17%** | ≤ 2.5 s | ⚠️ falta (auto-host Inter no M7) |
| **TBT** | 367 ms | **27 ms** | **−93%** | ≤ 200 ms | 🏆 |
| **CLS** | 0 | 0.0003 | manter | ≤ 0.1 | ✅ |
| **Speed Index** | 2.97 s | 1.98 s | **−33%** | ≤ 2.5 s | ✅ |
| **TTI** | 4.22 s | 3.49 s | −17% | ≤ 3.5 s | ✅ |
| **Max Potential FID** | 292 ms | **81 ms** | **−72%** | ≤ 130 ms | ✅ |
| **Total bytes (transfer)** | 606 KiB | 561 KiB | −7% | ≤ 350 KiB | ❌ (avatar 256 KiB no M7) |
| **Tailwind CDN bundle** | 126 KiB transfer / 407 KiB descomprimido | substituído por CSS local 72 KiB | resolvido | ≤ 30 KiB | parcial |
| **JS render-blocking** | 1.520 ms (Chart.js) + 150 ms (date-fns) | **0 ms** | **−100%** | 0 ms | 🏆 |
| **CSS render-blocking** | 818 ms (Tailwind CDN) + 869 ms (Google Fonts) + 159 ms (custom) | 1.150 ms (CSS local + Inter Google Fonts) | melhorou | ≤ 200 ms | ❌ M7 |
| **`main.js` JS não usado** | 33.8 KiB / 42.6 KiB (79%) | 33.8 KiB / 42.6 KiB (79%) | igual | ≤ 20% via code-splitting | ❌ M7 |
| **Instalações PWA** | 0 | tracking habilitado (manifest+SW+share_target+protocol_handlers) | ✅ | tracking habilitado | 🏆 |

#### Resumo dos achados resolvidos

| Achado baseline | Sprint 8 | Status |
|---|---|---|
| `heading-order` (H3 sem H2) | M4 — H1+H2 hierárquicos no dashboard | ✅ |
| `select-name` (filtro 6 meses) | M4 — substituído por segmented control | ✅ |
| `identical-links-same-purpose` | M4 — `aria-label` distintivos | ✅ |
| Erro `date-fns CommonJS` no console | M0 — removido (não era usado) | ✅ |
| Tailwind CDN 818 ms render-blocking | M0 — django-tailwind local | ✅ |
| Chart.js 1.520 ms síncrono | M4 — lazy `import()` via IntersectionObserver | ✅ |
| Tabelas mobile sem fallback | M2/M6 — cards verticais < lg | ✅ |
| Touch targets <44px | M2-M6 — todos ≥44px | ✅ |
| Sem PWA / Service Worker | M1+M5 — manifest + Workbox + Background Sync | ✅ |

#### Achados que permanecem para o M7

1. **CSS render-blocking 1.150 ms total** — `styles.css` (Tailwind
   buildado, 1.224 ms) + `custom.css` (473 ms) + `tokens.css` (173 ms).
   *Solução:* preload + critical CSS inline + auto-host Inter.
2. **Avatar 256 KiB sem cache + sem responsive size**
   (32×40 visível ↔ 802×800 real) — economiza 254 KiB e 1.2 s LCP.
   *Solução:* `django-imagekit` + WebP + `Cache-Control: 1y`.
3. **`main.js` 79% não usado** — code-splitting por rota.
4. **Inter via Google Fonts: 977 ms na chain** — auto-host com
   `@fontsource/inter` ou `manage.py tailwind` + Inter local.
5. **`custom.css` 100% não usado** na rota `/budgets/plano/`,
   94% na `/dashboard/`. Pode ser deletado/integrado ao Tailwind.
6. **DOM size na lista de transações** — 290 elementos, com
   `<select id_category>` carregando 30 options via AJAX.
   *Solução:* lazy-load do select só quando filtro abre.
7. **`aria-allowed-role`** (informativo) — drawer com
   `role="dialog"` + `aria-hidden="true"` quando fechado.
   *Solução:* remover role quando hidden via JS no shell.
8. **`label-content-name-mismatch`** — top-bar "FinanPy" e
   bottom-nav "Início" com `aria-label` divergente do texto
   visível. *Solução:* alinhar texto/label.

> ⚠️ **Observação sobre PWA score:** Lighthouse 13 removeu a categoria
> "PWA" como nota numérica. A validação será feita por checagens
> individuais no `manifest.webmanifest`, ícones maskable, Service Worker
> registrado, instalability prompt e `display: standalone`.

### Achados adicionais do baseline (oportunidades de M0–M7)

1. **Erro JavaScript no console** — `date-fns@2.29.3/index.min.js` lança
   `Uncaught ReferenceError: exports is not defined`. O build CommonJS
   está sendo carregado direto no browser. **Trocar para a versão ESM
   (`date-fns@latest/esm`)** ou remover dependência inútil. *(escopo do
   M5 ou M7 polish)*
2. **`heading-order` falha** — `<h3>Resumo Financeiro</h3>` sem H1/H2
   antecedendo no `dashboard.html`. *(corrigir no M4 — refactor do
   dashboard mobile)*
3. **`select-name` falha** — `<select>` "Últimos 6 meses" sem
   `<label>`/`aria-label`. *(corrigir no M4)*
4. **`identical-links-same-purpose`** — dois `<a>"Ver todas"</a>` apontam
   para `/transactions/` e `/goals/` mas têm o mesmo texto visível.
   *(corrigir no M4 — usar `aria-label` distintivo)*
5. **`avatar.jpeg` 256 KiB sem cache** — imagem grande do perfil sem
   `Cache-Control`. *(adicionar headers no Nginx no M0/M5)*
6. **`render-blocking-insight` estima 1.900 ms de economia só do M0**
   (Tailwind CDN + Chart.js síncrono). Excelente confirmação de que o
   M0 (django-tailwind) tem retorno gigantesco antes mesmo do M1.
7. **`unused-css-rules`** — 11.4 KiB de 12.2 KiB (94%) do `custom.css`
   não é usado no dashboard. *(purge automático do django-tailwind
   resolve no M0)*

### Comparativo entre as 3 telas medidas

| Métrica | Dashboard | Transactions | Budgets/Plano |
|---|---|---|---|
| Performance | 72 | 82 | **85** |
| Accessibility | 87 | 82 ⚠️ | **100** 🏆 |
| Best Practices | 96 | 100 | 100 |
| FCP | 2.97 s | 2.61 s | **2.52 s** |
| LCP | 4.22 s | 4.08 s | **3.78 s** |
| TBT | 367 ms | 77 ms | **0 ms** 🏆 |
| Total bytes | 606 KiB | 565 KiB | **532 KiB** |

> Detalhes individuais em `docs/lighthouse-baseline/{dashboard,transactions,budgets-plano}.md`.

**Observações cruzadas:**

1. **Render-blocking de ~1.5–1.9 s é universal** (Tailwind CDN + Google
   Fonts em todas as telas). M0 + auto-host de Inter resolverá em todas.
2. **`bg-primary-600` (`#0284c7`) com texto branco falha contraste WCAG
   AA (4.09:1 < 4.5:1)** — afeta TODA a aplicação. Definir paleta
   acessível como pré-requisito do M0 nos design tokens.
3. **`/budgets/plano/` é referência de qualidade técnica** — replicar o
   padrão (H1 LCP, selects com label, sem JS bloqueante após render) no
   M2/M4/M6.
4. **`main.js` não-usado: 79% em todas as telas** — code-splitting por
   rota (M5/M7) é alto valor.
5. **Avatar 256 KiB sem cache aparece nas 3** — fix de Nginx no M0/M5
   beneficia tudo.
6. **`/transactions/api/categories/` é chamado 2× na lista** —
   consolidar (M3).

### KPIs de produto

- Tempo médio para registrar uma transação (mobile): alvo **< 8s**
- Taxa de transações registradas com sucesso em modo offline (background sync): **> 99%**
- Adoção do FAB para nova transação vs. menu: **> 70%** das criações
- Engajamento com Hermes via deeplinks: medir CTR

---

## 5. Plano de Testes

### E2E (Playwright em modo mobile)

- Login → navegação por bottom-nav → criar transação via FAB → confirmar saldo atualizado
- Modo offline: criar transação → recuperar conexão → confirmar sync
- Instalação PWA → abrir via ícone → verificar `display: standalone`
- Share target: enviar imagem do app de fotos → confirmar que abre form com OCR

### Unitários (pytest + django.test)

- Endpoints novos (`/quick/`, `/snapshot/`, `/from-receipt/`, `/sync/since/`)
- Resolução de categoria por similaridade (`/quick/`)

### Acessibilidade

- axe-core em CI para todas as rotas autenticadas
- Manual: navegação por teclado, screen reader (TalkBack/VoiceOver) nos fluxos críticos

### Performance

- Lighthouse CI no GitHub Actions (mobile preset, throttling 4G slow)
- Bundle analyzer (django-tailwind output + JS bundles)

---

## 6. Impactos em Documentação Existente

Documentos a atualizar após implementação:

| Documento | Atualização |
|---|---|
| `docs/architecture.md` | Adicionar seção sobre PWA, SW, manifest |
| `docs/frontend-guidelines.md` | Reescrever em mobile-first, design tokens, bottom-nav |
| `docs/tailwindcss-setup.md` | Substituir por instruções django-tailwind |
| `docs/JAVASCRIPT_FEATURES.md` | Documentar SW, background sync, share_target, deeplinks |
| `docs/B1-API-REST-SPEC.md` | Adicionar endpoints `/quick/`, `/snapshot/`, `/from-receipt/`, `/sync/since/` |
| `docs/setup-guide.md` | Adicionar `manage.py tailwind start` no fluxo dev |
| `docs/deployment.md` | Adicionar build do Tailwind no Dockerfile |
| `docs/tasks.md` | Mover INF-001 para "concluído" após M0 |
| Obsidian `FinanPy.md` | Adicionar entrada "Mobile-first refactor" no Histórico de Sprints |

---

## 7. Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| Background sync falhar em iOS Safari (suporte parcial) | Alta | Médio | Fallback: queue em IndexedDB + retry on `online` event |
| Quebra de templates desktop durante refactor | Média | Alto | Testes E2E desktop antes de cada PR; feature flags por rota |
| Aumento da complexidade do build (django-tailwind + node) | Média | Baixo | Documentar setup; CI roda `tailwind build` no release |
| Service Worker cachear versão antiga após deploy | Alta | Médio | Versionamento via hash + skipWaiting controlado + banner "Nova versão disponível" |
| Deeplinks não funcionarem antes do app instalado | Alta | Baixo | Fallback para web normal via `/handler/?q=` |
| Performance do endpoint `/snapshot/` (agregação pesada) | Média | Médio | Cache em Redis (alinhado com INF-002) ou cache de view por user/min |

---

## 8. Próximos Passos

1. ✅ **Documento aprovado** (este arquivo)
2. ⏭️ Criar issues no Jira/Obsidian para M0 a M7
3. ⏭️ Iniciar **M0 — Fundação** (django-tailwind + tokens)
4. ⏭️ Definir métricas baseline com Lighthouse atual antes do refactor (para comparação)

---

## 9. Referências

- [Web.dev — PWA Checklist](https://web.dev/pwa-checklist/)
- [Workbox — Background Sync](https://developer.chrome.com/docs/workbox/modules/workbox-background-sync/)
- [Material Design — Bottom Navigation](https://m3.material.io/components/navigation-bar/overview)
- [Apple HIG — Touch targets](https://developer.apple.com/design/human-interface-guidelines/components/menus-and-actions)
- [django-tailwind docs](https://django-tailwind.readthedocs.io/)
- [Web Share Target API](https://web.dev/web-share-target/)
- [URL Protocol Handlers](https://web.dev/url-protocol-handler/)
- [[FinanPy]] — nota mestre do projeto na vault
- [[FinanPy — Vida e Saúde]] — módulo health (backlog HS-001 a HS-010)
- `docs/architecture.md` (repo)
- `docs/B1-API-REST-SPEC.md` (repo)
- `docs/frontend-guidelines.md` (repo)
