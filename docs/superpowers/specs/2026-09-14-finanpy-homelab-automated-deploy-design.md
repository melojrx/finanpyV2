# Especificação: Automação de deploy do FinanPy no Homelab

**Data:** 14/09/2026
**Status:** aprovado para planejamento
**Escopo:** concluir o onboarding operacional do FinanPy no Homelab com
promoção automática após `push` em `main`.

## Decisão

O FinanPy adotará o mesmo contrato de promoção já validado pelo UrbanLive:
um runner GitHub Actions dedicado e sem login no Homelab recebe somente o job
de deploy do repositório FinanPy. Esse runner pode executar, via uma única
regra sudoers, o wrapper root-owned específico do FinanPy. O wrapper aceita
apenas o checkout esperado e uma imagem imutável do GHCR por digest completo.

O deploy não fará `git pull`, build local ou uso de tags mutáveis. O checkout
do runner fornece somente os manifestos e controladores versionados; a imagem
já aprovada pelo CI é a única artefato de aplicação promovido ao Swarm.

## Objetivos de sucesso

- Um `push` em `main` executa os testes atuais, publica uma imagem
  `linux/amd64` no GHCR e entrega o digest completo ao job de deploy.
- O job deploy roda apenas no runner com label
  `homelab-finanpy-deploy`, em grupo de concorrência
  `deploy-finanpy-production` e sem cancelamento de promoção em curso.
- O wrapper copia somente `deploy/swarm` e `scripts/homelab` para
  `/srv/finanpy/releases/sha256-<digest>`, com propriedade root e permissões
  restritas, antes de chamar o controlador de stack.
- A promoção executa a migration one-shot, atualiza o web por digest e exige
  health Docker mais readiness Django com `X-Forwarded-Proto: https`.
- Falha em migration ou readiness encerra a promoção sem declarar release
  válida; o Swarm preserva seu rollback de web, sem rollback automático de
  banco ou remoção de volumes.
- Brabus Store e UrbanLive não recebem task, alteração de rede, secret ou
  rollout como efeito de uma promoção do FinanPy.

## Não objetivos

- Compartilhar runner, conta de sistema, diretório de release, wrapper,
  concorrência, secrets ou rede privada com outra aplicação.
- Fazer o corte público, criar hostname de Tunnel, alterar DNS, rotacionar o
  token do Tunnel ou desligar a VPS de contingência neste onboarding.
- Fazer backup externo, adicionar Redis/Celery, alterar o produto ou mudar a
  estratégia de dados já validada no ensaio privado.
- Registrar tokens de runner, segredo Django, senha PostgreSQL, credenciais
  GHCR, dumps ou dados financeiros no Git, Actions summary ou vault.

## Arquitetura

```text
push protegido em main
  -> GitHub-hosted: testes, check --deploy, build e push GHCR linux/amd64
  -> digest sha256 completo como output do job publish
  -> runner-finanpy no Homelab
  -> sudo /usr/local/sbin/deploy-finanpy-release <checkout> <digest>
  -> /srv/finanpy/releases/sha256-<digest>
  -> migration one-shot -> rollout Swarm start-first -> health/readiness
```

| Limite | Contrato |
| --- | --- |
| Conta do runner | `runner-finanpy`, system account sem login e sem grupo `docker` |
| Runner | `/opt/actions-runner-finanpy`, serviço `actions.runner.finanpy.service` |
| Checkout autorizado | `/opt/actions-runner-finanpy/_work/finanpy_v2/finanpy_v2` |
| Sudo | somente o wrapper FinanPy, com o checkout acima e um argumento de digest |
| Wrapper | `/usr/local/sbin/deploy-finanpy-release`, propriedade `root:root`, modo `0755` |
| Releases | `/srv/finanpy/releases/sha256-<64-hex>`, propriedade `root:root`, modo `0750` |
| Runtime | stack `finanpy`, stack de edge `finanpy-edge`, rede privada `finanpy_backend` |
| Concorrência | `finanpy-production` no workflow e `deploy-finanpy-production` no job de deploy |

## Workflow GitHub Actions

O job atual `publish` passa a expor o digest em `outputs.image`. Um job
`deploy` depende de `publish`, roda somente em `push` para `main`, tem
permissão `contents: read` e usa
`runs-on: [self-hosted, homelab-finanpy-deploy]`.

O job faz checkout e chama somente:

```sh
sudo /usr/local/sbin/deploy-finanpy-release \
  "$GITHUB_WORKSPACE" \
  "ghcr.io/melojrx/finanpyv2@${{ needs.publish.outputs.image }}"
```

Ele registra no resumo da execução apenas commit, digest e nome do
controlador. Não inclui variáveis de ambiente, paths de secret ou saída de
PostgreSQL.

## Wrapper e controlador

O wrapper valida, antes de qualquer escrita:

1. o caminho literal do checkout do runner;
2. o digest no formato `ghcr.io/melojrx/finanpyv2@sha256:<64-hex>`;
3. presença dos manifestos, exemplo de ambiente e scripts de controlador;
4. criação do diretório de release sem abrir permissões a outros usuários.

Depois, ele arquiva e extrai apenas os diretórios versionados de deploy,
instala os dois scripts de runtime em `/srv/finanpy/bin` e delega ao
`deploy-stack.sh` já existente. Esse controlador mantém suas validações de
Swarm, rede `edge`, secrets apenas por nome, migration, rollout e readiness.

O wrapper não aceita caminho alternativo, tag de imagem, shell livre ou
opções adicionais. A regra sudoers não pode usar curingas capazes de trocar o
checkout autorizado ou de executar outro binário.

## Operação e falhas

Antes do registro do runner, o Homelab deve receber `systemctl daemon-reload`;
a inspeção atual indicou que ao menos uma unidade existente tem fragmento em
disco mais novo que a versão carregada. Após instalação, o serviço do runner
deve estar `active` e o runner deve aparecer `online` com o label exclusivo.

Em falha de deployment, a evidência operacional é: URL da execução, commit,
digest, estado de `finanpy_migrate` e `finanpy_web`, logs limitados do serviço
afetado e resultado do readiness. A investigação não deve alterar Brabus ou
UrbanLive. Não há rollback automático de banco; se uma migration incompatível
falhar após escrita, a recuperação exige decisão explícita e reconciliação.

## Validação

1. Teste estático do workflow garante output do digest, job dependente,
   runner/concorrência corretos e ausência de SSH, tags `latest` ou comandos
   arbitrários.
2. Teste estático do wrapper garante path literal, validação de digest,
   staging restrito e chamada ao controlador do FinanPy.
3. No Homelab, verificar propriedade/modo do wrapper e sudoers efetivo sem
   exibir segredos; confirmar serviço systemd ativo e runner online.
4. Realizar uma promoção controlada por `workflow_dispatch` ou commit
   documental aprovado, confirmando migration, digest do `finanpy_web`, health
   local e que os serviços Brabus/UrbanLive mantiveram seus IDs de task.
5. A publicação pública permanece um gate posterior: exige zona Cloudflare
   ativa, hostname do Tunnel, HTTPS, login e fluxo autenticado não destrutivo.

## Gates de autorização

Esta especificação autoriza apenas escrever o plano de implementação. A
criação da conta/runner no Homelab, instalação de sudoers e serviço systemd,
mudança do workflow em `main`, execução de uma promoção e configuração
pública do Cloudflare são gates operacionais distintos, realizados somente no
momento aprovado pelo usuário.
