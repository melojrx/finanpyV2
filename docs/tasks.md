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

## Backlog de Produção Pós-MVP

O backlog oficial e rastreável do produto está em `docs/backlog.md`, alinhado
ao projeto Jira `FIN`. Esta seção fica apenas como resumo operacional dos itens
pós-MVP que apareceram durante as sprints deste documento; não substitui o mapa
Jira.

Itens abaixo não bloqueiam o primeiro deploy em VPS:

- [x] Implementar app `goals` — ver Sprint 5.
- [ ] Migrar Tailwind CDN para build local.
- [ ] Implementar anexos/comprovantes de transação.
- [x] Adicionar avatar de perfil com upload validado.
- [ ] Implementar preferências avançadas de usuário (tema, moeda padrão, dashboard).
- [ ] Configurar provedor SMTP real em produção para emails transacionais
  (`EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`,
  `DEFAULT_FROM_EMAIL`), validando envio de reset de senha.
- [ ] Adicionar Redis/cache quando houver necessidade medida.
- [ ] Adicionar Sentry/monitoramento após deploy base.
- [ ] Expandir testes de `accounts`, `categories`, `budgets`, `users` e `goals`.
