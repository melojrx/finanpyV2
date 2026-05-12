# Plano Vivo de Produção - FinanPy

Este documento acompanha a execução do plano para alinhar documentação e código,
preparar produção em VPS Ubuntu com Docker Compose e registrar evidências de cada
sprint.

## Status Geral

- [x] Sprint 0 - Planejamento documentado
- [x] Sprint 1 - Settings de produção e dependências mínimas
- [x] Sprint 2 - Docker Compose para VPS Ubuntu
- [x] Sprint 3 - Documentação oficial alinhada ao código
- [x] Sprint 4 - Validação final e evidências
- [x] Sprint 5 - Módulo de Metas Financeiras (goals)
- [x] Sprint 6 - Plano Mensal Global (MonthlyPlan)
- [x] Sprint 7 - Módulo de Planejamento Mensal (Wizard + API)
- [ ] Sprint 8 - Mobile-First Architecture + PWA (M0..M7)

## Sprint 0 - Planejamento Documentado

Objetivo: transformar o plano aprovado em tarefas executáveis e rastreáveis.

- [x] Definir `docs/` como fonte oficial de documentação.
- [x] Criar este `docs/tasks.md` como documento vivo.
- [x] Registrar critérios de aceite técnicos e documentais.

Evidências:

- Documento criado em `docs/tasks.md`.
- Plano estruturado em sprints pequenos para reduzir risco.

## Sprint 1 - Settings de Produção

Objetivo: manter desenvolvimento simples e criar configuração segura para produção.

- [x] Manter `core/settings.py` como configuração de desenvolvimento.
- [x] Reescrever `core/settings_production.py` com variáveis de ambiente.
- [x] Configurar PostgreSQL via variáveis simples.
- [x] Configurar `SECRET_KEY`, `ALLOWED_HOSTS` e `CSRF_TRUSTED_ORIGINS`.
- [x] Configurar cookies seguros, proxy SSL, HSTS e headers de segurança.
- [x] Trocar logging de produção para console.
- [x] Adicionar dependências mínimas: `gunicorn` e `psycopg[binary]`.

Evidências:

- `core/settings_production.py` agora falha cedo se `SECRET_KEY`,
  `ALLOWED_HOSTS` ou `POSTGRES_PASSWORD` estiverem ausentes.
- `requirements.txt` recebeu `gunicorn==23.0.0` e
  `psycopg[binary]==3.2.10`.
- Comando executado com sucesso:
  `venv/bin/python manage.py check --settings=core.settings_production`.
- Comando executado com sucesso:
  `venv/bin/python manage.py check --deploy --settings=core.settings_production`.

## Sprint 2 - Docker Compose para VPS Ubuntu

Objetivo: entregar um deploy simples e reproduzível com Django, PostgreSQL e Nginx.

- [x] Criar `Dockerfile`.
- [x] Criar `.dockerignore`.
- [x] Criar `docker-compose.prod.yml`.
- [x] Criar entrypoint para `migrate`, `collectstatic` e Gunicorn.
- [x] Criar configuração Nginx para proxy, static e media.
- [x] Usar volumes persistentes para banco, static e media.
- [x] Rodar containers com usuário não-root no serviço Django.

Evidências:

- `Dockerfile` criado com `python:3.13-slim`, usuário `app` não-root e
  Gunicorn como comando padrão.
- `docker-compose.prod.yml` criado com serviços `web`, `db` e `nginx`.
- `docker/entrypoint.sh` criado para aguardar PostgreSQL, rodar `migrate` e
  `collectstatic`.
- `docker/nginx.conf` criado para servir `/static/`, `/media/` e fazer proxy
  para o Django.
- `.env.production.example` criado com variáveis necessárias para VPS.
- Comando executado com sucesso:
  `docker compose -f docker-compose.prod.yml --env-file .env.production.example config`.

## Sprint 3 - Documentação Oficial Alinhada

Objetivo: a documentação oficial deve refletir o que existe hoje no código.

- [x] Criar `docs/backlog.md` com itens documentados mas ainda não implementados.
- [x] Criar `docs/deployment.md` com VPS Ubuntu + Docker Compose.
- [x] Atualizar `docs/README.md` removendo links inexistentes.
- [x] Atualizar `docs/architecture.md` com a arquitetura real.
- [x] Atualizar `docs/configuration.md` com variáveis realmente suportadas.
- [x] Atualizar `docs/setup-guide.md` para desenvolvimento local real.
- [x] Atualizar `docs/database-structure.md` com os models existentes.
- [x] Mover recursos futuros para backlog em vez de documentá-los como atuais.

Evidências:

- `docs/backlog.md` criado com recursos futuros e itens removidos do escopo
  oficial atual.
- `docs/deployment.md` criado com instruções de VPS Ubuntu + Docker Compose.
- `docs/README.md`, `docs/architecture.md`, `docs/configuration.md`,
  `docs/setup-guide.md` e `docs/database-structure.md` foram reescritos para
  refletir o código atual.
- `docs/troubleshooting.md`, `docs/frontend-guidelines.md` e
  `docs/static-media-configuration.md` tiveram referências antigas corrigidas.
- Busca executada para remover referências oficiais a docs inexistentes,
  dependências não instaladas e rotas antigas.

## Sprint 4 - Validação Final

Objetivo: comprovar que o projeto continua funcional e que produção está verificável.

- [x] Executar `venv/bin/python manage.py check`.
- [x] Executar `venv/bin/python manage.py test`.
- [x] Executar `venv/bin/python manage.py makemigrations --check --dry-run`.
- [x] Executar `venv/bin/python manage.py check --deploy --settings=core.settings_production` com variáveis de produção.
- [x] Validar configuração Docker Compose.
- [x] Registrar limitações e próximos passos.

Evidências:

- `venv/bin/python manage.py check`: passou sem issues.
- `venv/bin/python manage.py makemigrations --check --dry-run`: `No changes detected`.
- `venv/bin/python manage.py check --deploy --settings=core.settings_production`: passou sem issues com variáveis mínimas de produção.
- `venv/bin/python manage.py test`: 32 testes executados com sucesso.
- `docker compose -f docker-compose.prod.yml --env-file .env.production.example config --quiet`: passou.
- Smoke test Docker executado com projeto isolado `finanpy_codex_smoke`:
  build concluído, containers `db`, `web` e `nginx` subiram, migrations rodaram,
  `collectstatic` copiou 130 arquivos e Gunicorn iniciou 3 workers.
- `curl -I -H 'Host: example.com' http://127.0.0.1:8088/`: retornou `HTTP/1.1 200 OK`.
- Containers e volumes do smoke test foram removidos com `docker compose ... down -v`.

Limitações conhecidas:

- O deploy base expõe Nginx em HTTP. Para produção final, configure HTTPS antes
  de manter `SECURE_SSL_REDIRECT=true` e HSTS.
- O app `goals` foi implementado no Sprint 5.
- A cobertura de testes ainda precisa ser expandida nos apps com poucos testes.

---

## Sprint 5 - Módulo de Metas Financeiras

Objetivo: implementar o app `goals` completo, permitindo ao usuário criar metas
financeiras, registrar aportes e acompanhar o progresso de cada uma.

### Contexto e Decisões de Design

**O que é uma meta financeira neste sistema?**

Uma meta representa um objetivo de poupança com valor-alvo e data limite
opcional. O usuário avança nela registrando aportes manuais. Exemplos:
reserva de emergência, viagem, compra de um bem.

**Por que dois models (Goal + GoalContribution)?**

Manter um histórico de aportes permite ao usuário visualizar sua evolução no
tempo e excluir aportes errados sem perder consistência. O saldo atual
(`current_amount`) é calculado pela soma dos aportes e armazenado via signal
para leituras rápidas — mesma estratégia já usada em `Budget`.

**O que não entra neste sprint?**

- Vínculo automático com transações ou contas bancárias.
- Notificações ou alertas por e-mail.
- Relatórios avançados de metas.

Esses itens permanecem no backlog e podem ser adicionados depois sem quebrar
o que será entregue aqui.

---

### Passo 1 — Models (`goals/models.py`)

Criar dois models seguindo os padrões já estabelecidos no projeto.

**Goal**

| Campo | Tipo | Observação |
|---|---|---|
| `user` | FK → User | isolamento por usuário |
| `name` | CharField(100) | nome da meta |
| `description` | TextField, opcional | detalhes livres |
| `target_amount` | DecimalField(12,2) | valor a atingir |
| `current_amount` | DecimalField(12,2), default 0 | atualizado via signal |
| `deadline` | DateField, opcional | prazo da meta |
| `icon` | CharField(10), choices | emoji de identificação |
| `color` | CharField(7), choices | cor hex para UI |
| `status` | CharField, choices | ACTIVE / COMPLETED / CANCELLED |
| `created_at` | DateTimeField(auto_now_add) | auditoria |
| `updated_at` | DateTimeField(auto_now) | auditoria |

Regras de negócio no `clean()`:
- `target_amount` deve ser positivo.
- `deadline`, se informado, deve ser uma data futura no momento da criação.
- `current_amount` não deve ser editado diretamente pelo usuário (campo interno).

Propriedades úteis:
- `progress_pct` → porcentagem atingida (0–100, nunca ultrapassa 100).
- `remaining_amount` → quanto falta.
- `is_completed` → True quando `current_amount >= target_amount`.

**GoalContribution**

| Campo | Tipo | Observação |
|---|---|---|
| `goal` | FK → Goal | CASCADE |
| `user` | FK → User | consistência e isolamento |
| `amount` | DecimalField(12,2) | valor do aporte, positivo |
| `date` | DateField | data do aporte |
| `notes` | TextField, opcional | observação livre |
| `created_at` | DateTimeField(auto_now_add) | auditoria |

Regra: `amount` deve ser positivo; `goal.user` deve ser igual a `user`.

Checklist:
- [x] Criar `Goal` com campos, Meta class, `__str__`, `clean()` e propriedades.
- [x] Criar `GoalContribution` com campos, Meta class, `__str__` e `clean()`.
- [x] Adicionar indexes em `Goal` (user, status) e `GoalContribution` (goal, date).

---

### Passo 2 — Signal (`goals/signals.py` + `goals/apps.py`)

Seguir o mesmo padrão de `transactions/signals.py`.

O signal recalcula `Goal.current_amount` toda vez que um `GoalContribution`
é criado ou excluído:

```python
# Lógica simplificada
@receiver(post_save, sender=GoalContribution)
@receiver(post_delete, sender=GoalContribution)
def update_goal_amount(sender, instance, **kwargs):
    goal = instance.goal
    total = goal.contributions.aggregate(total=Sum('amount'))['total'] or 0
    goal.current_amount = total
    # Atualiza status para COMPLETED se atingiu o alvo
    if total >= goal.target_amount:
        goal.status = 'COMPLETED'
    elif goal.status == 'COMPLETED':
        goal.status = 'ACTIVE'
    goal.save(update_fields=['current_amount', 'status', 'updated_at'])
```

Registrar o signal em `goals/apps.py` no método `ready()`.

Checklist:
- [x] Criar `goals/signals.py` com handlers para `post_save` e `post_delete`.
- [x] Atualizar `goals/apps.py` para importar signals no `ready()`.

---

### Passo 3 — Formulários (`goals/forms.py`)

**GoalForm** — para criar e editar metas:
- Campos visíveis: `name`, `description`, `target_amount`, `deadline`, `icon`, `color`.
- `current_amount` e `status` não aparecem no formulário de criação.
- Widgets com as classes CSS do projeto (`.form-input`).

**GoalContributionForm** — para registrar aportes:
- Campos visíveis: `amount`, `date`, `notes`.
- `date` com valor padrão `today`.
- `goal` e `user` injetados na view, não expostos no form.

Checklist:
- [x] Criar `GoalForm` com validação e widgets adequados.
- [x] Criar `GoalContributionForm` com validação e widgets adequados.

---

### Passo 4 — Views (`goals/views.py`)

Usar Class-Based Views com `LoginRequiredMixin`, idêntico a `budgets/views.py`.
Todos os querysets filtram por `request.user`.

| View | Classe base | URL | Propósito |
|---|---|---|---|
| `GoalListView` | ListView | `/goals/` | lista de metas do usuário |
| `GoalCreateView` | CreateView | `/goals/create/` | formulário de nova meta |
| `GoalDetailView` | DetailView | `/goals/<pk>/` | detalhes + histórico de aportes |
| `GoalUpdateView` | UpdateView | `/goals/<pk>/edit/` | editar meta |
| `GoalDeleteView` | DeleteView | `/goals/<pk>/delete/` | confirmar exclusão |
| `GoalContributionCreateView` | CreateView | `/goals/<pk>/contribute/` | registrar aporte |
| `GoalContributionDeleteView` | DeleteView | `/goals/<goal_pk>/contributions/<pk>/delete/` | remover aporte |

Regras:
- `get_queryset()` sempre filtra por `request.user`.
- `GoalDetailView` carrega as últimas contribuições via `prefetch_related`.
- `GoalContributionCreateView` injeta `goal` e `user` no `form_valid()`.
- Na exclusão de meta, o CASCADE do banco remove as contribuições automaticamente.

Checklist:
- [x] Implementar as 7 views listadas acima.
- [x] Garantir isolamento por usuário em todos os querysets.

---

### Passo 5 — URLs (`goals/urls.py` + `core/urls.py`)

```python
# goals/urls.py
app_name = 'goals'

urlpatterns = [
    path('', GoalListView.as_view(), name='list'),
    path('create/', GoalCreateView.as_view(), name='create'),
    path('<int:pk>/', GoalDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', GoalUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', GoalDeleteView.as_view(), name='delete'),
    path('<int:pk>/contribute/', GoalContributionCreateView.as_view(), name='contribute'),
    path('<int:goal_pk>/contributions/<int:pk>/delete/',
         GoalContributionDeleteView.as_view(), name='contribution-delete'),
]
```

Registrar em `core/urls.py`:
```python
path('goals/', include('goals.urls')),
```

Checklist:
- [x] Criar `goals/urls.py` com as 7 rotas.
- [x] Adicionar `goals/` em `core/urls.py`.

---

### Passo 6 — Templates (`templates/goals/`)

Seguir a estrutura já usada em `templates/budgets/` e `templates/transactions/`.

| Arquivo | Propósito |
|---|---|
| `goal_list.html` | grade de cards com progresso de cada meta |
| `goal_form.html` | formulário de criação e edição |
| `goal_detail.html` | card da meta + tabela de aportes + botão de novo aporte |
| `goal_confirm_delete.html` | confirmação de exclusão |

Diretrizes visuais (conforme `docs/frontend-guidelines.md`):
- Cards com `bg-gray-800`, bordas arredondadas, sombra sutil.
- Barra de progresso: `bg-gray-700` como fundo, cor da meta como preenchimento.
- Porcentagem exibida dentro ou ao lado da barra.
- Cor semântica: verde quando completa, azul quando ativa, cinza quando cancelada.
- Botão de aporte em destaque no detalhe da meta.

Checklist:
- [x] Criar `goal_list.html` com cards e barras de progresso.
- [x] Criar `goal_form.html` com seletor de ícone e cor.
- [x] Criar `goal_detail.html` com histórico de aportes e botão de contribuição.
- [x] Criar `goal_confirm_delete.html`.

---

### Passo 7 — Admin (`goals/admin.py`)

Registrar `Goal` e `GoalContribution` no admin com inline de contribuições
dentro de cada meta, seguindo o padrão dos outros apps.

Checklist:
- [x] Registrar `Goal` no admin com `GoalContributionInline`.
- [x] Registrar `GoalContribution` no admin individualmente.

---

### Passo 8 — Integração no Dashboard

Adicionar um bloco "Minhas Metas" no dashboard (`templates/dashboard/dashboard.html`)
com as 3 metas ativas de maior progresso. Nenhuma lógica nova na view é necessária
além de adicionar a query a `DashboardView.get_context_data()`.

```python
# Em DashboardView.get_context_data()
from goals.models import Goal
active_goals = (
    Goal.objects.filter(user=user, status='ACTIVE')
    .order_by('-current_amount')[:3]
)
context['active_goals'] = active_goals
```

Checklist:
- [x] Adicionar query de metas ativas em `DashboardView`.
- [x] Adicionar bloco de metas no template do dashboard.

---

### Passo 9 — Migração e Verificação

```bash
python manage.py makemigrations goals
python manage.py migrate
python manage.py check
```

Checklist:
- [x] Gerar migration de `goals`.
- [x] Aplicar migration sem erros.
- [x] `manage.py check` sem warnings.

---

### Passo 10 — Testes (`goals/tests.py`)

Cobrir os cenários críticos com `TestCase` do Django, mesmo padrão dos outros apps.

Cenários mínimos:
- Criar meta com dados válidos.
- Rejeitar meta sem nome ou com `target_amount <= 0`.
- Criar aporte e verificar que `current_amount` é atualizado via signal.
- Excluir aporte e verificar recálculo do `current_amount`.
- Meta muda para `COMPLETED` ao atingir o alvo.
- Usuário B não acessa meta do usuário A (isolamento).

Checklist:
- [x] Implementar testes dos models (`Goal`, `GoalContribution`).
- [x] Implementar testes do signal de recálculo.
- [x] Implementar teste de isolamento por usuário nas views.
- [x] `python manage.py test goals` sem falhas.

---

### Critérios de Aceite do Sprint 5

- [x] Usuário consegue criar, editar e excluir uma meta financeira.
- [x] Usuário consegue registrar e remover aportes para uma meta.
- [x] `current_amount` reflete exatamente a soma dos aportes após cada operação.
- [x] Meta muda automaticamente para `COMPLETED` ao atingir o alvo.
- [x] Dashboard exibe até 3 metas ativas com barra de progresso.
- [x] Nenhum usuário acessa dados de outro usuário.
- [x] `manage.py check` e `manage.py test` passam sem erros.

### Evidências Sprint 5

- App `goals` implementado com models `Goal` e `GoalContribution`,
  signal `update_goal_amount_*` em `goals/signals.py`, formulários,
  7 CBVs, URLs com namespace `goals`, admin e 5 templates.
- Migração `goals/migrations/0001_initial.py` aplicada sem erros.
- `venv/bin/python manage.py check`: 0 issues.
- `venv/bin/python manage.py test`: 51 testes (32 existentes + 19 novos
  do app `goals`) passaram.
- Navbar atualizada em `templates/base.html` para apontar Metas para
  `goals:list`.
- `DashboardView` em `users/views.py` agora carrega `active_goals`
  (top 3 ativas por `current_amount`) e o bloco "Metas Financeiras" do
  dashboard renderiza dados reais com cores e ícones por meta.

---

## Sprint 6 — Plano Mensal Global (MonthlyPlan)

Objetivo: implementar o planejamento financeiro mensal consolidado por usuário,
permitindo definir renda prevista, teto de despesas e reservas, com acompanhamento
em tempo real via transações.

### Contexto e Decisões de Design

**O que é o Plano Mensal?**

Uma visão consolidada do mês que combina dados planejados (inseridos pelo
usuário) com dados realizados (calculados automaticamente a partir das
`Transaction`). Um registro por usuário/mês, com validação cruzada que garante
que despesas + reservas não ultrapassem a renda prevista.

**Por que um model separado em vez de estender `Budget`?**

`Budget` é orçamento por categoria; `MonthlyPlan` é orçamento global do mês.
São conceitos distintos com granularidades diferentes. Manter separado evita
poluir o model de categorias com campos de consolidado mensal.

**Reservas genéricas (dívidas, metas, investimentos)**

Os campos `reserva_dividas`, `reserva_metas` e `reserva_investimentos` são
preparados para os módulos FIN-7, FIN-9 e FIN-10, mas já funcionam como
reservas genéricas no cálculo de sobra planejada.

---

### Passo 1 — Model (`budgets/models.py`)

Criar `MonthlyPlan` com campos planejados e propriedades calculadas do lado
realizado.

| Campo | Tipo | Observação |
|---|---|---|
| `user` | FK → User | isolamento por usuário |
| `year` | PositiveSmallIntegerField | ano do plano |
| `month` | PositiveSmallIntegerField | mês do plano (1–12) |
| `renda_prevista` | DecimalField(12,2) | receitas esperadas |
| `teto_despesas` | DecimalField(12,2) | limite máximo de gastos |
| `reserva_dividas` | DecimalField(12,2), default 0 | preparado FIN-7 |
| `reserva_metas` | DecimalField(12,2), default 0 | preparado FIN-9 |
| `reserva_investimentos` | DecimalField(12,2), default 0 | preparado FIN-10 |
| `notes` | TextField, opcional | observações livres |
| `created_at` | DateTimeField(auto_now_add) | auditoria |
| `updated_at` | DateTimeField(auto_now) | auditoria |

Regras de negócio no `clean()`:
- `month` entre 1 e 12; `year` entre 2000 e 2100.
- `teto_despesas + reservas ≤ renda_prevista`.

Propriedades calculadas (lado realizado, via `Transaction`):
- `renda_realizada` → soma de INCOME no período.
- `despesas_realizadas` → soma de EXPENSE no período.
- `saldo_disponivel` → renda_realizada − despesas_realizadas.
- `percentual_consumido` → despesas / teto × 100.
- `limite_diario_recomendado` → (teto − despesas) / dias_restantes.
- `status` → 'ok' / 'atencao' / 'critico' baseado no percentual consumido.

Checklist:
- [x] Criar `MonthlyPlan` com campos, Meta class, `__str__`, `clean()` e propriedades.
- [x] Adicionar `UniqueConstraint` em `(user, year, month)`.
- [x] Adicionar `CheckConstraint` para mês e ano válidos.
- [x] Adicionar index em `(user, year, month)`.

---

### Passo 2 — Formulário (`budgets/forms.py`)

**MonthlyPlanForm** — para criar e atualizar o plano:
- Campos visíveis: `renda_prevista`, `teto_despesas`, `reserva_dividas`,
  `reserva_metas`, `reserva_investimentos`, `notes`.
- `year` e `month` injetados pela view (via URL), não expostos no form.
- Validação cruzada: teto + reservas ≤ renda prevista.

Checklist:
- [x] Criar `MonthlyPlanForm` com widgets e validação adequados.

---

### Passo 3 — Views (`budgets/views.py`)

| View | Classe base | URL | Propósito |
|---|---|---|---|
| `MonthlyPlanView` | View (GET/POST) | `/budgets/plano/` e `/budgets/plano/<year>/<month>/` | upsert do plano mensal |
| `MonthlyPlanListView` | ListView | `/budgets/planos/` | histórico de planos |

Regras:
- `LoginRequiredMixin` em ambas.
- `MonthlyPlanView` resolve o período (ano/mês) da URL ou usa o mês atual.
- GET preenche o form com plano existente (se houver).
- POST cria ou atualiza o plano para o usuário logado.
- Contexto inclui navegação entre meses, orçamentos por categoria e KPIs.

Checklist:
- [x] Implementar `MonthlyPlanView` com GET/POST e contexto rico.
- [x] Implementar `MonthlyPlanListView` com paginação.
- [x] Garantir isolamento por usuário em todos os querysets.

---

### Passo 4 — URLs (`budgets/urls.py`)

```python
path('plano/', views.MonthlyPlanView.as_view(), name='monthly_plan'),
path('plano/<int:year>/<int:month>/', views.MonthlyPlanView.as_view(), name='monthly_plan_for'),
path('planos/', views.MonthlyPlanListView.as_view(), name='monthly_plan_list'),
```

Checklist:
- [x] Adicionar 3 rotas de plano mensal em `budgets/urls.py`.

---

### Passo 5 — Templates (`templates/budgets/`)

| Arquivo | Propósito |
|---|---|
| `monthly_plan.html` | Formulário + KPI cards (status, renda, despesas, sobra, limite diário, reservas) + orçamentos por categoria |
| `monthly_plan_list.html` | Tabela de histórico paginado com renda, teto e sobra |

Diretrizes visuais:
- Cards com `bg-dark-800/70`, bordas arredondadas, borda sutil.
- Barra de progresso de consumo com cores semânticas (verde/amarelo/vermelho).
- Navegação entre meses anterior/próximo/mês atual.

Checklist:
- [x] Criar `monthly_plan.html` com formulário e KPIs.
- [x] Criar `monthly_plan_list.html` com histórico paginado.

---

### Passo 6 — Admin (`budgets/admin.py`)

Registrar `MonthlyPlan` no admin com listagem por usuário, ano e mês.

Checklist:
- [x] Registrar `MonthlyPlanAdmin` com `list_display`, `list_filter` e `search_fields`.

---

### Passo 7 — Migração e Verificação

```bash
python manage.py makemigrations budgets
python manage.py migrate
python manage.py check
```

Checklist:
- [x] Gerar migration `budgets/migrations/0003_monthly_plan.py`.
- [x] Aplicar migration sem erros.
- [x] `manage.py check` sem warnings.

---

### Passo 8 — Testes (`budgets/tests.py`)

Cobrir cenários críticos com `TestCase`, mesmo padrão dos outros apps.

Cenários mínimos:
- Criar plano com dados válidos.
- Rejeitar plano duplicado (mesmo usuário/ano/mês).
- Rejeitar reservas que excedem renda prevista.
- Rejeitar mês/ano inválidos.
- Verificar cálculo de sobra planejada.
- Verificar soma de renda realizada a partir de transações INCOME.
- Verificar soma de despesas realizadas a partir de transações EXPENSE.
- Verificar exclusão de transações fora do período.
- Verificar isolamento por usuário nas transações.
- Verificar status 'ok'/'atencao'/'critico' baseado no consumo.
- Verificar limite diário recomendado.
- View GET retorna 200 e template correto.
- View POST cria plano novo.
- View POST atualiza plano existente.
- View POST rejeita dados inválidos.
- ListView mostra apenas planos do usuário logado.

Checklist:
- [x] Implementar testes de model (`MonthlyPlanModelTests`).
- [x] Implementar testes de view (`MonthlyPlanViewTests`).
- [x] `python manage.py test budgets` sem falhas.

---

### Critérios de Aceite do Sprint 6

- [x] Usuário consegue criar e editar um plano mensal global.
- [x] Validação impede que despesas + reservas excedam a renda prevista.
- [x] Apenas um plano por usuário/mês é permitido.
- [x] KPIs realizados (renda, despesas, saldo) refletem transações do período.
- [x] Status de saúde ('ok'/'atencao'/'critico') é calculado corretamente.
- [x] Limite diário recomendado se ajusta conforme o mês avança.
- [x] Nenhum usuário acessa dados de outro usuário.
- [x] `manage.py check` e `manage.py test` passam sem erros.

### Evidências Sprint 6

- Model `MonthlyPlan` adicionado em `budgets/models.py` (~340 linhas) com
  validações, constraints, indexes e propriedades calculadas.
- Formulário `MonthlyPlanForm` em `budgets/forms.py` com validação cruzada.
- Views `MonthlyPlanView` (upsert) e `MonthlyPlanListView` em `budgets/views.py`.
- 3 rotas adicionadas em `budgets/urls.py`.
- Admin `MonthlyPlanAdmin` registrado em `budgets/admin.py`.
- Templates `monthly_plan.html` e `monthly_plan_list.html` criados.
- Migration `budgets/migrations/0003_monthly_plan.py` gerada e aplicada.
- Testes: ~46 novos testes cobrindo model, validações, propriedades calculadas
  e views (isolamento, GET, POST create/update, rejeição de inválidos).

---

### Critérios de Aceite do Sprint 7

- [x] Usuário cria planejamento mensal completo via wizard em 3 passos.
- [x] "Copiar mês anterior" pré-preenche distribuição com valores do mês anterior.
- [x] Valor da categoria mãe calculado automaticamente como soma das filhas (JS).
- [x] Usuário pode lançar despesa diretamente na categoria mãe.
- [x] Acompanhamento exibe gasto real vs planejado por categoria em tempo real.
- [x] Alertas disparados quando gasto atinge threshold configurado.
- [x] API REST cobre criação, edição, ativação, cópia e consulta de planos e itens.
- [x] Todos os endpoints da API filtram por usuário autenticado (404 para outros).
- [x] `manage.py check` e `manage.py test` passam sem erros.

### Evidências Sprint 7

- Model `MonthlyPlanItem` criado em `budgets/models.py` com FK para `MonthlyPlan`
  e `Category`, propriedades `spent_amount`, `percentage_used`, `remaining_amount`,
  `is_over_budget`, `status_color`, `progress_bar_color`.
- `MonthlyPlan` evoluído com campos `savings_goal` e `status` (DRAFT/ACTIVE/CLOSED),
  constantes de status, propriedade `teto_calculado` e `health_status` (renomeado
  de `status` para evitar conflito com o campo DB).
- `BudgetAlert` evoluído com FK nullable `plan_item` → `MonthlyPlanItem`.
- Migrations `0004_sprint7_monthly_plan_item.py` e `0005_add_status_to_monthlyplan.py`
  geradas e aplicadas sem erros.
- Formulários `MonthlyPlanHeaderForm` e `MonthlyPlanItemForm` + `MonthlyPlanItemFormSet`
  adicionados em `budgets/forms.py`.
- 6 views do wizard implementadas em `budgets/views.py`:
  `PlanningEntryView`, `PlanningHeaderView`, `PlanningDistributeView`,
  `PlanningReviewView`, `PlanningDashboardView`, `PlanningCopyView`.
- Views de CRUD avulso de `Budget` removidas.
- 6 rotas do wizard + 3 rotas de alertas em `budgets/urls.py`.
- 5 templates criados em `templates/budgets/`:
  `planning_entry.html`, `planning_header.html`, `planning_distribute.html`,
  `planning_review.html`, `planning_dashboard.html`.
- Templates obsoletos de Budget avulso mantidos no repositório (histórico).
- API REST: `MonthlyPlanViewSet` e `MonthlyPlanItemViewSet` com serializers
  `MonthlyPlanSerializer`, `MonthlyPlanItemSerializer`, `MonthlyPlanSummarySerializer`
  registrados no router DRF em `api/urls.py`.
- Actions de API: `activate`, `copy_from_previous`, `summary`.
- Admin atualizado: `MonthlyPlanItemInline`, `MonthlyPlanItemAdmin`,
  `BudgetAlertAdmin` com `plan_item`.
- Testes: 175 testes passando (98 em `budgets`, incluindo 37 novos do Sprint 7
  cobrindo `MonthlyPlanItemModelTests`, `PlanningWizardViewTests`,
  `MonthlyPlanAPITests`).
- `manage.py check`: 0 issues.
- `manage.py test`: 175 testes, 0 falhas.

---

## Sprint 8 - Mobile-First Architecture + PWA

Objetivo: refatorar o frontend para mobile-first, transformar o sistema em PWA
instalável com offline-write, e expor endpoints novos para o agente Hermes.

**Documento aprovado:** `docs/mobile-architecture.md` (espelho da nota Obsidian
`02-Projetos/FinanPy/2026-05-11-mobile-first-architecture.md`).

**Decisões aprovadas:**

- Build de CSS: `django-tailwind` (substitui CDN — resolve INF-001).
- Escopo PWA: completo, com offline-write via Background Sync.
- Navegação mobile: bottom-nav 5 slots + FAB central elevado.

**Estimativa total:** ~19 dias úteis (M0 a M7).

**Pré-flight (concluído nesta sessão):**

- [x] Sincronizar `docs/mobile-architecture.md` com a versão Obsidian aprovada.
- [x] Criar branch `feature/mobile-first-architecture` a partir de `main`.
- [x] Remover templates obsoletos `transaction_list_backup.html` e
  `transaction_list_enhanced.html` (sem referências no código).
- [x] Atualizar `.gitignore` para `theme/node_modules/` e
  `theme/static/css/dist/`.
- [x] Adicionar `django-tailwind[reload]` ao `requirements.txt`.
- [x] Criar estrutura `templates/components/` e `static/images/icons/`.
- [ ] Capturar baseline Lighthouse mobile (manual — DevTools, mobile preset,
  4G slow throttling) e registrar em `docs/mobile-architecture.md` §4.

### M0 — Fundação (2 dias)

- [ ] `pip install -r requirements.txt` (puxa `django-tailwind[reload]`).
- [ ] `python manage.py tailwind init theme` (cria app `theme/`).
- [ ] Adicionar `tailwind`, `theme`, `django_browser_reload` em
  `INSTALLED_APPS`.
- [ ] `python manage.py tailwind install`.
- [ ] Migrar configuração custom de `templates/base.html:14-135` para
  `theme/static_src/tailwind.config.js`.
- [ ] Habilitar plugins `@tailwindcss/forms`, `@tailwindcss/typography` e
  plugin custom `safe-area`.
- [ ] Criar `static/css/tokens.css` com design tokens
  (safe-areas, h-vars, surfaces, motion).
- [ ] Remover `<script src="https://cdn.tailwindcss.com">` do `base.html` e
  trocar pelo `{% tailwind_css %}`.
- [ ] Atualizar `docker/entrypoint.sh` e `Dockerfile` para rodar
  `python manage.py tailwind build` antes de `collectstatic`.

### M1 — Shell PWA (3 dias)

- [ ] Criar `static/manifest.webmanifest` (com `share_target` e
  `protocol_handlers`).
- [ ] Criar `static/sw.js` com Workbox (estratégias por rota; ver §2.5 do doc).
- [ ] Criar `static/offline.html`.
- [ ] Gerar ícones maskable: `icon-192.png`, `icon-512.png`,
  `apple-touch-icon.png` (180x180), `favicon.svg`, `shortcut-add.png` (96x96).
- [ ] Refatorar `templates/base.html`: `viewport-fit=cover`, `theme-color`,
  registro do SW, link para manifest, top-bar minimalista.
- [ ] Criar componentes: `_bottom_nav.html`, `_top_bar.html`, `_drawer.html`,
  `_fab.html`, `_toast.html` (com safe-area), `_empty_state.html`,
  `_skeleton.html`, `_bottom_sheet.html`, `_swipe_card.html`.

### M2 — Lista de Transações (2 dias)

- [x] Apagar `transaction_list_backup.html` e `transaction_list_enhanced.html`.
  *(feito no pré-flight)*
- [ ] Substituir tabela `hidden lg:block` por lista de cards swipeáveis
  (delete/edit) usando `_swipe_card.html`.
- [ ] Mover filtros para bottom-sheet (`_bottom_sheet.html`).
- [ ] Implementar pull-to-refresh.

### M3 — Form rápido + bottom-sheet (2 dias)

- [ ] Refatorar `transaction_form.html` em bottom-sheet.
- [ ] Aplicar `inputmode="decimal"`, máscara de moeda BR, `enterkeyhint`,
  `autocomplete` semântico.
- [ ] Autocomplete de categoria com fuzzy match.
- [ ] Sticky CTA inferior.

### M4 — Dashboard mobile (2 dias)

- [ ] Snap-scroll horizontal de stat cards.
- [ ] Charts em swiper (Receitas / Despesas / Saldo) com lazy-load do
  Chart.js.
- [ ] Implementar endpoint `GET /api/v1/dashboard/snapshot/` (1 request agrega
  saldo, mês, últimas 5 tx, alertas, top 3 budgets).
- [ ] Refatorar `dashboard.html` para consumir `/snapshot/`.

### M5 — Background Sync + Hermes (3 dias)

- [ ] SW: queue Workbox `finanpy-tx-queue` para POST de transações offline.
- [ ] Endpoint `POST /api/v1/transactions/quick/` (resolve categoria por
  similaridade).
- [ ] Endpoint `POST /api/v1/transactions/from-receipt/` (multipart → Google
  Vision → draft).
- [ ] Endpoint `GET /api/v1/sync/since/?ts=<iso>` (delta).
- [ ] Endpoint `GET /api/v1/handler/?q=<deeplink>` para `web+finanpy://`.
- [ ] Implementar `share_target` no manifest (já no M1) + view de recebimento.

### M6 — Demais telas (3 dias)

- [ ] `accounts/account_list.html`: cards verticais com saldo grande, badge
  de tipo.
- [ ] `categories/category_list.html`: lista hierárquica com indentação +
  chevrons.
- [ ] `budgets/planning_*.html`: wizard vertical, progress bar topo, sticky
  CTA.
- [ ] `budgets/budget_detail.html` e `goals/goal_detail.html`: cards mobile +
  tabela ≥md.

### M7 — Polimento (2 dias)

- [ ] Lighthouse PWA ≥ 90, Performance ≥ 85, A11y ≥ 95.
- [ ] axe-core no CI.
- [ ] Testes E2E mobile com Playwright (login, FAB→nova tx, offline→sync,
  install PWA, share_target).
- [ ] Bundle analysis (CSS ≤ 30 KB gzip, JS inicial ≤ 80 KB gzip).
- [ ] Atualizar documentação espelho: `architecture.md`,
  `frontend-guidelines.md`, `tailwindcss-setup.md` (substituir),
  `JAVASCRIPT_FEATURES.md`, `B1-API-REST-SPEC.md`, `setup-guide.md`,
  `deployment.md`.

---

## Backlog de Produção Pós-MVP

O backlog oficial e rastreável do produto está em `docs/backlog.md`, alinhado
ao projeto Jira `FIN`. Esta seção fica apenas como resumo operacional dos itens
pós-MVP que apareceram durante as sprints deste documento; não substitui o mapa
Jira.

Itens abaixo não bloqueiam o primeiro deploy em VPS:

- [x] Implementar app `goals` — ver Sprint 5.
- [ ] Migrar Tailwind CDN para build local. *(coberto pelo M0 da Sprint 8)*
- [ ] Implementar anexos/comprovantes de transação.
- [x] Adicionar avatar de perfil com upload validado.
- [ ] Implementar preferências avançadas de usuário (tema, moeda padrão, dashboard).
- [ ] Configurar provedor SMTP real em produção para emails transacionais
  (`EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`,
  `DEFAULT_FROM_EMAIL`), validando envio de reset de senha.
- [ ] Adicionar Redis/cache quando houver necessidade medida.
- [ ] Adicionar Sentry/monitoramento após deploy base.
- [ ] Expandir testes de `accounts`, `categories`, `budgets`, `users` e `goals`.
