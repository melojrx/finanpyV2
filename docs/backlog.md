# Backlog Futuro - FinanPy

Este documento é o espelho documental do backlog do projeto Jira `FIN` e também
reúne itens técnicos locais que ainda não bloqueiam o deploy inicial em VPS.

O Jira continua sendo a fonte operacional principal para prioridade, status e
execução. Este arquivo existe para manter rastreabilidade entre Jira, código e
documentação do repositório.

## Fonte Jira

- Site: `https://melojrxdev.atlassian.net`
- Projeto: `FIN` - Finanpy
- Tipo: Jira Software, team-managed / next-gen
- Fonte local de referência: nota Obsidian
  `2026-05-03-setup-jira-pessoal-finanpy.md`

## Mapa Jira FIN

| Jira | Tipo | Título | Estado no código | Estado nos docs | Observação |
|---|---|---|---|---|---|
| `FIN-1` | Épico | Orçamento, Dívidas, Metas e Liberdade Financeira | Parcial | Parcial | Agrupa funcionalidades já existentes e módulos futuros. |
| `FIN-2` | Tarefa | FPY-FIN-001 - Orçamento global mensal | Parcial / implementado | Parcial | O app `budgets` tem orçamento mensal, telas e métricas; falta validar se cobre todo o escopo Jira. |
| `FIN-3` | Tarefa | FPY-FIN-002 - API de budgets/orçamento mensal | Concluído | Concluído | Sprint 7: `MonthlyPlanViewSet` + `MonthlyPlanItemViewSet` com CRUD, activate, copy_from_previous, summary. |
| `FIN-4` | Tarefa | FPY-FIN-003 - Briefing financeiro diário via Neo/Telegram | Não implementado | Ausente | Requer integração externa e rotina de geração de briefing. |
| `FIN-5` | Tarefa | FPY-FIN-004 - Alertas proativos de orçamento via Telegram | Parcial | Parcial | Existe `BudgetAlert` local; não há envio via Telegram. |
| `FIN-6` | Tarefa | FPY-FIN-005 - Recorrências e contas fixas | Parcial | Parcial | `Transaction` tem campos de recorrência; não há geração automática de contas fixas. |
| `FIN-7` | Tarefa | FPY-FIN-006 - Módulo de dívidas e plano de liquidação | Não implementado | Ausente | Há suporte genérico a cartão como tipo de conta, mas não um módulo de dívidas. |
| `FIN-8` | Tarefa | FPY-FIN-007 - Parcelamentos, cartão e faturas | Parcial | Ausente | Existe tipo de conta `credit_card`; não há parcelamentos ou faturas. |
| `FIN-9` | Tarefa | FPY-FIN-008 - API e automação de metas financeiras | Parcial | Parcial | O app `goals` foi implementado; não há API de metas nem automações. |
| `FIN-10` | Tarefa | FPY-FIN-009 - Investimentos, rendimento e patrimônio líquido | Parcial | Ausente | Existe tipo de conta `investment`; não há módulo de investimentos/rendimentos. |
| `FIN-11` | Tarefa | FPY-FIN-010 - Fluxo de caixa futuro | Não implementado | Ausente | Requer projeções com recorrências, contas fixas e vencimentos. |
| `FIN-12` | Tarefa | FPY-FIN-011 - Dashboard de liberdade financeira | Parcial | Ausente | Existe dashboard geral; não há visão específica de liberdade financeira. |
| `FIN-13` | Tarefa | FPY-FIN-012 - Correção da suíte de testes/CI financeiro | Parcial | Parcial | Testes locais estão documentados; o workflow atual é de deploy e não executa CI de testes. |
| `FIN-14` | Tarefa | FPY-FIN-013 - Status de transação (Pendente/Efetivada/Cancelada) | Não implementado | Spec pronto | Pré-requisito para FIN-6 e FIN-11. Spec: `docs/superpowers/specs/2026-05-16-transaction-status-design.md`. |

## Backlog Técnico Local

## Produto

- Adicionar anexos/comprovantes em transações.
- Adicionar preferências avançadas no perfil do usuário, como tema, moeda padrão
  e preferências de dashboard.
- Adicionar relatórios financeiros mais completos além do dashboard atual.
- Adicionar vínculo opcional entre aportes de metas, transações e contas.
- Adicionar API REST para orçamentos, metas, perfis e relatórios avançados.

## Infraestrutura

- **INF-001 — Migrar TailwindCSS CDN para build local com `django-tailwind`.**
  Decisão aprovada em `docs/mobile-architecture.md` (Sprint 8 / M0). Resolve
  CSS de ~3 MB (CDN) → ~30 KB gzip (build), libera plugins
  `@tailwindcss/forms` e `@tailwindcss/typography`, e habilita CSP estrito.
  *(Em execução na branch `feature/mobile-first-architecture`.)*
- **INF-002 — Adicionar Redis/cache** após identificar gargalo real (alinhado
  com cache do endpoint `/api/v1/dashboard/snapshot/` no M4 da Sprint 8).
- Adicionar Sentry ou serviço equivalente após o primeiro deploy estável.
- Avaliar storage externo para media, como S3 compatível, quando uploads forem
  relevantes em produção.
- Criar rotina de backup automatizado do PostgreSQL.
- Configurar provedor SMTP real em produção para emails transacionais, incluindo
  reset de senha, via `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_TLS`,
  `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` e `DEFAULT_FROM_EMAIL`.

## Qualidade

- Expandir testes de `accounts`, `categories`, `budgets`, `users` e `goals`.
- Cobrir fluxos críticos de CRUD com testes de permissão por usuário.
- Adicionar teste automatizado para settings de produção com variáveis mínimas.
- Adicionar teste para consistência de saldo após criação, edição e remoção de
  transações.

## Documentação Removida do Escopo Atual

Os seguintes tópicos foram movidos para backlog porque não existem no código:

- `TransactionAttachment`.
- Redis, Celery, Sentry, S3 e cache distribuído.
- `crispy_forms`, `crispy_tailwind`, `django_extensions` como dependências
  oficiais do projeto.
- `core.middleware.*` e `core.context_processors.*`.
- API REST para orçamentos, metas, perfis e relatórios avançados.
- Provedor SMTP real para envio de emails transacionais em produção.
