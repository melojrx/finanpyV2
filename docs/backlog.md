# Backlog Futuro - FinanPy

Este backlog reúne itens que apareceram em documentos anteriores ou no produto
imaginado, mas que ainda não estão implementados no código atual. Eles não
bloqueiam o deploy inicial em VPS.

## Produto

- Adicionar anexos/comprovantes em transações.
- Adicionar preferências avançadas no perfil do usuário, como tema, moeda padrão
  e preferências de dashboard.
- Adicionar relatórios financeiros mais completos além do dashboard atual.
- Adicionar vínculo opcional entre aportes de metas, transações e contas.
- Adicionar API REST para orçamentos, metas, perfis e relatórios avançados.

## Infraestrutura

- Migrar TailwindCSS CDN para build local quando houver necessidade de otimizar
  performance, CSP ou customização profunda.
- Adicionar Redis/cache somente após identificar gargalo real.
- Adicionar Sentry ou serviço equivalente após o primeiro deploy estável.
- Avaliar storage externo para media, como S3 compatível, quando uploads forem
  relevantes em produção.
- Criar rotina de backup automatizado do PostgreSQL.

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
