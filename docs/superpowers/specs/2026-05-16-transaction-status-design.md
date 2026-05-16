# Transaction Status — Design Spec

**Data:** 2026-05-16
**Jira:** FIN-14 (a criar)
**Status:** Aprovado para implementação

## Resumo

Adicionar campo `status` ao model `Transaction` para suportar transações
pendentes (previstas) e efetivadas (realizadas). Apenas transações efetivadas
impactam saldo da conta. Transações podem ser canceladas sem exclusão.

## Motivação

Atualmente toda transação impacta saldo imediatamente e não aceita datas
futuras. Usuário não consegue planejar despesas/receitas futuras nem controlar
quando o impacto financeiro realmente acontece.

## Status e Transições

```
PENDING ──→ CONFIRMED
   │              │
   └──→ CANCELLED ←──┘
```

| Status | Impacta saldo | Descrição |
|--------|:---:|---|
| PENDING | Não | Prevista/agendada. Aparece no saldo previsto. |
| CONFIRMED | Sim | Realizada. Impacta saldo real da conta. |
| CANCELLED | Não | Cancelada. Histórico preservado, sem impacto. |

Transições válidas:
- PENDING → CONFIRMED (efetivar)
- PENDING → CANCELLED (cancelar)
- CONFIRMED → CANCELLED (estornar/cancelar efetivada)

Transições inválidas:
- CANCELLED → qualquer (status terminal)
- CONFIRMED → PENDING (não faz sentido reverter efetivação pra pendente)

## Model Changes

### Novos campos em `Transaction`

```python
STATUS_CHOICES = [
    ('PENDING', 'Pendente'),
    ('CONFIRMED', 'Efetivada'),
    ('CANCELLED', 'Cancelada'),
]

status = models.CharField(
    max_length=10,
    choices=STATUS_CHOICES,
    default='PENDING',
    db_index=True,
)

auto_confirm = models.BooleanField(
    default=False,
    help_text='Se True, efetiva automaticamente na data via cron',
)

confirmed_at = models.DateTimeField(
    null=True,
    blank=True,
    help_text='Timestamp de quando foi efetivada',
)
```

### Índices adicionais

```python
models.Index(fields=['user', 'status']),
models.Index(fields=['status', 'transaction_date', 'auto_confirm']),
```

### Validação (clean)

- Remover bloqueio de data futura (permitir qualquer data)
- Adicionar validação de transição de status
- `auto_confirm` só faz sentido quando `status == PENDING`

## Signals — Lógica de Saldo

### Regra fundamental

**Saldo só é afetado por transações com `status == CONFIRMED`.**

### post_save (criação)

- Se `created` e `status == CONFIRMED`: aplica delta no saldo
- Se `created` e `status == PENDING`: não faz nada no saldo

### pre_save (atualização)

Captura valores antigos. No post_save:

- **PENDING → CONFIRMED**: aplica delta (efetivação)
- **CONFIRMED → CANCELLED**: reverte delta (estorno)
- **Mudança de amount/type/account em CONFIRMED**: reverte antigo, aplica novo
- **Mudança em PENDING**: não afeta saldo
- **PENDING → CANCELLED**: não afeta saldo

### post_delete

- Se `status == CONFIRMED`: reverte delta
- Se `status != CONFIRMED`: não faz nada

## Migration Strategy

### Data migration

```python
# Todas as transações existentes recebem status=CONFIRMED
# Saldos permanecem intactos — nenhum recálculo necessário
Transaction.objects.all().update(
    status='CONFIRMED',
    confirmed_at=F('created_at'),
)
```

### Rollback safety

- Campo tem default, migration é reversível
- Remover campo não afeta saldo (já calculado)

## Form Changes

### TransactionForm

- Adicionar campo `status` (select com PENDING/CONFIRMED)
- Default: PENDING (mudança de comportamento — usuário escolhe)
- Adicionar campo `auto_confirm` (checkbox, visível quando PENDING)
- Remover `max` date restriction do widget `transaction_date`
- Remover validação de data futura em `clean_transaction_date()`

### TransactionFilterForm

- Adicionar filtro por `status` (multi-select ou select)
- Default: mostrar PENDING + CONFIRMED (ocultar CANCELLED)

## Views

### Novas actions

```python
class TransactionConfirmView(LoginRequiredMixin, View):
    """POST: efetiva transação pendente."""
    # Valida: status == PENDING, pertence ao user
    # Seta status = CONFIRMED, confirmed_at = now()
    # Signal cuida do saldo

class TransactionCancelView(LoginRequiredMixin, View):
    """POST: cancela transação."""
    # Valida: status in (PENDING, CONFIRMED), pertence ao user
    # Seta status = CANCELLED
    # Se era CONFIRMED, signal reverte saldo

class TransactionBulkConfirmView(LoginRequiredMixin, View):
    """POST: efetiva múltiplas transações pendentes."""
    # Recebe lista de IDs via POST
    # Valida ownership + status == PENDING
    # Efetiva em batch
```

### URLs

```python
path('<int:pk>/confirm/', TransactionConfirmView.as_view(), name='confirm'),
path('<int:pk>/cancel/', TransactionCancelView.as_view(), name='cancel'),
path('bulk-confirm/', TransactionBulkConfirmView.as_view(), name='bulk_confirm'),
```

### TransactionListView

- Adicionar tabs/filtro: Pendentes | Efetivadas | Todas
- Summary stats separados por status

## Dashboard

### Dois saldos por conta

- **Saldo real**: soma de CONFIRMED
- **Saldo previsto**: saldo real + PENDING (receitas - despesas pendentes)

### Indicadores

- Contagem de pendentes próximas (próximos 7 dias)
- Alerta visual se pendentes atrasadas (data < hoje e ainda PENDING)

## Management Command

```python
# transactions/management/commands/confirm_pending_transactions.py

class Command(BaseCommand):
    help = 'Efetiva transações pendentes com auto_confirm=True e data <= hoje'

    def handle(self, *args, **options):
        pending = Transaction.objects.filter(
            status='PENDING',
            auto_confirm=True,
            transaction_date__lte=date.today(),
        )
        count = 0
        for txn in pending:
            txn.status = 'CONFIRMED'
            txn.confirmed_at = timezone.now()
            txn.save()  # trigger signal
            count += 1
        self.stdout.write(f'{count} transações efetivadas.')
```

Executar via cron: `0 6 * * * python manage.py confirm_pending_transactions`

## UI/UX

### Badges de status

| Status | Cor | Ícone |
|--------|-----|-------|
| PENDING | Amarelo (warning) | clock |
| CONFIRMED | Verde (success) | check |
| CANCELLED | Cinza (muted) | x-mark |

### Ações na listagem

- Transação PENDING: botões "Efetivar" e "Cancelar"
- Transação CONFIRMED: botão "Cancelar" (com confirmação)
- Transação CANCELLED: somente visualização

### Mobile

- Swipe-right em PENDING → Efetivar
- Swipe-left em PENDING/CONFIRMED → Cancelar (com confirm dialog)

### Formulário de criação

- Campo status como segmented control (Pendente | Efetivada)
- Checkbox "Efetivar automaticamente na data" (aparece quando Pendente)
- Campo data sem restrição de máximo

## Testes

### Unit tests

- Criação com cada status → verificar impacto (ou não) no saldo
- Transição PENDING→CONFIRMED → saldo atualizado
- Transição CONFIRMED→CANCELLED → saldo revertido
- Transição inválida CANCELLED→CONFIRMED → erro
- auto_confirm command efetiva corretas e ignora incorretas
- Isolamento por usuário nas actions

### Integration tests

- Fluxo completo: criar pendente → efetivar → verificar saldo
- Bulk confirm com mix de status
- Dashboard mostra dois saldos corretamente

## Impacto em Features Existentes

| Feature | Impacto | Ação |
|---------|---------|------|
| Budget tracking | Deve considerar só CONFIRMED | Filtrar por status |
| Monthly summary | Deve considerar só CONFIRMED | Filtrar por status |
| Reports/charts | Deve considerar só CONFIRMED | Filtrar por status |
| API endpoints | Adicionar campo status na serialização | Atualizar serializers |
| Export (XLSX) | Incluir coluna status | Atualizar export |

## Fora de Escopo (futuro)

- Notificações push de pendentes vencendo
- Efetivação automática via webhook bancário (Open Finance)
- Split de transação pendente em parcelas
- Recorrência automática gerando pendentes (FIN-6)
