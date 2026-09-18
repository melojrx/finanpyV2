# Patrimônio, Reservas, Transferências e Valores a Receber — Especificação de Design

> Status: Aprovado para planejamento
> Criado: 2026-09-18
> Autor: Junior Melo + Codex

## 1. Objetivo

Permitir que o FinanPy represente o patrimônio sem distorcer o resultado
operacional mensal. A primeira versão cobre uma reserva remunerada, transferências
entre contas e valores emprestados a terceiros, preservando `Transaction` para
receitas e despesas reais.

O caso de referência é o Cofre Mercado Pago: uma reserva de emergência remunerada
que integra o patrimônio líquido, mas não é saldo operacional disponível até que
ocorra um resgate.

## 2. Decisões de produto

| Decisão | Escolha |
|---|---|
| Cofre Mercado Pago | `Account.account_type='savings'`, exibido como “Reserva remunerada” |
| `investment` | Mantido para ativos futuros com comportamento próprio; sem CDI, cotação, IR ou posições nesta fase |
| Caixa disponível | Soma de contas `checking` ativas; saldos negativos subtraem |
| Reservas | Soma de contas `savings` e `investment` ativas |
| Valores a receber | Soma dos saldos pendentes de empréstimos `ACTIVE` |
| Patrimônio líquido | Caixa disponível + Reservas + Valores a receber |
| Receita/despesa | Apenas `Transaction(INCOME|EXPENSE)` confirmada; transferências, empréstimos e liquidações ficam fora |
| Rendimento da reserva | Ajuste manual auditável do saldo; não cria receita operacional |
| Dados pessoais iniciais | Cadastrados depois do release por API/MCP idempotente, nunca por migration de dados |

Os tipos legados `cash` e `credit_card` não mudam nesta entrega. O snapshot
deve expor seus saldos separadamente em `unclassified_account_balance`, para não
ocultá-los do patrimônio enquanto não houver uma política de classificação
aprovada. O campo não participa de `available_cash`; `net_worth` o inclui. Isso
preserva a regra “somente corrente é caixa disponível” e a regra de que saldos
negativos reduzem patrimônio.

## 3. Domínio e invariantes

### 3.1 Transferência

`FundTransfer` permanece o registro interno e passa a ser exposto como o recurso
REST `transfers`.

Uma transferência:

- pertence a um único usuário e relaciona duas contas ativas do mesmo usuário;
- tem origem e destino distintos, valor positivo e data;
- reduz a origem e aumenta o destino na mesma transação de banco;
- não cria `Transaction`, categoria, receita ou despesa;
- é imutável após criação; correções são feitas por transferência inversa;
- aceita `client_id` obrigatório no MCP e opcional na API, com unicidade por
  usuário e rejeição de reutilização com payload diferente.

Campos novos em `FundTransfer`: `client_id`, `destination_context` e
`fee_transaction`. O último só é criado quando houver `fee > 0` e
`fee_category`; uma taxa é uma despesa real e precisa ser uma `Transaction`
`EXPENSE` confirmada e vinculada à transferência. Sem categoria, a API rejeita
a taxa; não existe taxa silenciosamente fora dos relatórios.

### 3.2 Ajuste de saldo

Novo modelo `AccountBalanceAdjustment`:

| Campo | Regra |
|---|---|
| `account`, `user` | Conta `savings` ou `investment` do mesmo usuário |
| `previous_balance` | Capturado no servidor, imutável |
| `new_balance` | Valor absoluto informado pelo cliente |
| `delta` | `new_balance - previous_balance`, calculado no servidor |
| `adjustment_date`, `reason` | Obrigatórios |
| `client_id` | Único por usuário; repetição idêntica retorna o mesmo ajuste |
| `created_at` | Auditoria |

O ajuste bloqueia a conta com `select_for_update`, grava o histórico e atualiza
o saldo na mesma transação. `Account.balance` deixa de ser editável pela API
depois do cadastro inicial; a criação aceita `opening_balance` write-only.

### 3.3 Valores a receber

Novo app `receivables` com dois registros imutáveis de negócio:

- `LoanReceivable`: ativo originado pela saída de dinheiro;
- `LoanSettlement`: cada devolução total ou parcial.

`LoanReceivable` contém `counterparty`, `original_amount`, `outstanding_amount`,
`origin_account`, `loan_date`, `description`, `expected_return_date`, `status`,
`client_id`, timestamps e `written_off_at`/`write_off_reason` quando aplicável.

Estados válidos:

```text
ACTIVE -- settlement parcial --> ACTIVE
ACTIVE -- outstanding = 0 --> SETTLED
ACTIVE -- write-off explícito --> WRITTEN_OFF
```

Ao criar o empréstimo, o serviço bloqueia a conta de origem, reduz seu saldo e
cria o ativo. Ao liquidar, bloqueia empréstimo e conta destino, reduz o saldo
pendente e credita a conta. Nenhuma das duas operações cria `Transaction`.
`WRITTEN_OFF` remove o ativo do patrimônio, não altera uma conta de dinheiro e
exige motivo auditável.

## 4. Contratos REST

Todas as rotas abaixo usam a autenticação DRF por token já existente.

### Contas e ajustes

```text
POST  /api/v1/accounts/                         # aceita opening_balance na criação
PATCH /api/v1/accounts/{id}/                    # nome, tipo, moeda e ativo; nunca balance
POST  /api/v1/accounts/{id}/adjustments/
GET   /api/v1/accounts/{id}/adjustments/
```

Payload de ajuste:

```json
{
  "new_balance": "13812.40",
  "adjustment_date": "2026-09-18",
  "reason": "Rendimento do Cofre Mercado Pago",
  "client_id": "cofre-rendimento-20260918"
}
```

### Transferências

```text
POST /api/v1/transfers/
GET  /api/v1/transfers/?account=&date_from=&date_to=
```

```json
{
  "source_account": 1,
  "target_account": 2,
  "amount": "49.90",
  "transfer_date": "2026-09-18",
  "description": "Resgate parcial do Cofre",
  "destination_context": "Pagamento ChatGPT Plus",
  "client_id": "cofre-mercadopago-20260918-4990"
}
```

`POST /api/v1/accounts/transfer/` continua disponível como alias de
compatibilidade durante esta versão, aceitando os nomes antigos
`from_account`/`to_account`.

### Valores a receber

```text
POST /api/v1/loans-receivable/
GET  /api/v1/loans-receivable/?status=ACTIVE
POST /api/v1/loans-receivable/{id}/settle/
POST /api/v1/loans-receivable/{id}/write-off/
```

```json
{
  "counterparty": "Sabrina",
  "amount": "600.00",
  "origin_account": 2,
  "loan_date": "2026-09-18",
  "description": "Investimento Brabus Performance Store",
  "expected_return_date": null,
  "client_id": "sabrina-brabus-20260918-600"
}
```

Liquidação parcial:

```json
{
  "amount": "200.00",
  "target_account": 2,
  "settlement_date": "2026-10-10",
  "description": "Devolução parcial",
  "client_id": "sabrina-parcial-20261010-200"
}
```

## 5. Dashboard e relatórios

`GET /api/v1/dashboard/snapshot/` mantém `totals` para compatibilidade e ganha:

```json
{
  "patrimony": {
    "available_cash": "0.00",
    "reserves": "13749.75",
    "receivables": "600.00",
    "unclassified_account_balance": "0.00",
    "net_worth": "14349.75"
  }
}
```

O dashboard web apresenta os mesmos blocos. Relatórios mensais, orçamentos,
gráficos de receitas/despesas e `savings_pct` continuam baseados somente em
`Transaction` confirmada. A futura métrica “variação das reservas” é
explicitamente fora de escopo.

## 6. MCP

As tools preservam o contrato `{ok, endpoint, params, payload}`, o token atual e
o `User-Agent: Hermes/FinanPyMCP 1.1`.

| Tool | Endpoint |
|---|---|
| `finanpy_create_account` | `POST accounts/` |
| `finanpy_update_account` | `PATCH accounts/{id}/` |
| `finanpy_adjust_account_balance` | `POST accounts/{id}/adjustments/` |
| `finanpy_create_transfer` | `POST transfers/` |
| `finanpy_list_transfers` | `GET transfers/` |
| `finanpy_create_loan_receivable` | `POST loans-receivable/` |
| `finanpy_list_loans_receivable` | `GET loans-receivable/` |
| `finanpy_settle_loan_receivable` | `POST loans-receivable/{id}/settle/` |
| `finanpy_write_off_loan_receivable` | `POST loans-receivable/{id}/write-off/` |
| `finanpy_update_transaction` | `PATCH transactions/{id}/` |
| `finanpy_delete_transaction` | `DELETE transactions/{id}/` |
| `finanpy_dashboard_snapshot` | `GET dashboard/snapshot/` |

O write-off é uma adição deliberada à lista original: sem ele, o estado
`WRITTEN_OFF` não teria operação segura e auditável.

## 7. Migração e cadastro inicial

As migrations devem ser apenas de esquema, sem dados de Junior Melo. Depois do
deploy e da validação de autenticação, o operador executa chamadas MCP/API com
`client_id` explícito para:

1. criar “Cofre Mercado Pago” como `savings`, `opening_balance=13749.75`;
2. criar o resgate Cofre → Conta Mercado Pago de R$ 49,90 em 2026-09-18;
3. criar o empréstimo de R$ 600,00 à Sabrina, originado da Conta Mercado Pago.

Antes de cada chamada, a operação deve listar as contas e procurar pelo
`client_id` correspondente. Isso evita duplicação e exige confirmação humana
dos IDs das contas e dos saldos reais.

## 8. Fora de escopo

- sincronização Mercado Pago/Open Finance;
- produto de investimento, CDI, cotação, imposto, posição ou cálculo de juros;
- rendimento automático e relatório de rentabilidade;
- juros automáticos de empréstimo;
- reclassificação automática de histórico;
- política final de classificação de `cash` e `credit_card`.

## 9. Critérios de aceite

1. Uma conta `savings` “Cofre Mercado Pago” com R$ 13.749,75 aparece em
   Reservas e não em Caixa disponível.
2. O resgate de R$ 49,90 deixa a Conta Mercado Pago em R$ 0,00 e não altera
   receita ou despesa de setembro.
3. O empréstimo de R$ 600,00 aparece em Valores a Receber e não é despesa.
4. Liquidação parcial e total devolvem saldo à conta sem criar receita.
5. Um ajuste da reserva conserva saldo anterior, novo saldo, delta, data e
   motivo no histórico auditável.
6. Repetir uma escrita patrimonial com o mesmo `client_id` retorna o mesmo
   recurso sem aplicar saldo duas vezes; payload diferente retorna conflito.
7. Todas as tools especificadas funcionam com o token atual e o User-Agent
   Hermes existente.
