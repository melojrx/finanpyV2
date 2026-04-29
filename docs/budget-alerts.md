# Alertas de Orçamento (`BudgetAlert`)

Sistema de notificações automáticas para acompanhar o consumo de orçamentos.

## Como funciona

Sempre que uma transação (despesa) é criada, atualizada ou excluída, o signal
em [`budgets/signals.py`](../budgets/signals.py) recalcula o `spent_amount` dos
orçamentos afetados e avalia se algum limiar de uso foi ultrapassado:

| Limiar | Significado    | Cor sugerida |
|--------|----------------|--------------|
| 70%    | Atenção        | yellow       |
| 90%    | Crítico        | orange       |
| 100%   | Limite excedido| red          |

Para cada (orçamento, limiar) é criado **no máximo um** `BudgetAlert` —
garantido pela constraint `unique(budget, threshold)`. Isso evita ruído quando
o gasto oscila em torno do mesmo limiar.

## Modelo

```python
class BudgetAlert(models.Model):
    budget = FK(Budget)
    user = FK(User)                          # denormalizado p/ queries rápidas
    threshold = PositiveSmallInteger         # 70, 90 ou 100
    spent_at_trigger = Decimal               # snapshot
    percentage_at_trigger = Decimal          # snapshot
    triggered_at = DateTime(auto_now_add)
    acknowledged_at = DateTime(null=True)    # marca de "lido"
```

Snapshots permitem que o histórico mostre o contexto exato do disparo, mesmo
que o orçamento mude depois.

## Endpoints

| URL                                  | Método | Função                          |
|--------------------------------------|--------|---------------------------------|
| `/budgets/alerts/`                   | GET    | Lista alertas do usuário        |
| `/budgets/alerts/<pk>/ack/`          | POST   | Marca um alerta como lido       |
| `/budgets/alerts/ack-all/`           | POST   | Marca todos como lidos          |

Todas as views exigem autenticação e filtram por `request.user`.

## UI

- **Badge na navbar:** contador de alertas não lidos, alimentado pelo
  context processor `budgets.context_processors.budget_alerts`.
- **Página de alertas:** template [`templates/budgets/alert_list.html`](../templates/budgets/alert_list.html).

## O que está fora de escopo nesta versão

- Notificações por e-mail / push externo.
- Limiares customizáveis por usuário (hoje fixos em 70/90/100).
- Reativação de alerta após queda + nova subida (intencional: evita spam).

Esses itens podem voltar ao backlog se o uso real demonstrar necessidade.

## Estendendo

Para alterar os limiares, edite `BudgetAlert.DEFAULT_THRESHOLDS` em
[`budgets/models.py`](../budgets/models.py). Para usar limiares por usuário,
o caminho recomendado é adicionar um campo `notification_thresholds` no
`Profile` e ler do perfil dentro de `_evaluate_alerts()`.
