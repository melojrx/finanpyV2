# Especificação: FinanPy no Homelab

**Data:** 14/09/2026  
**Status:** aprovado para planejamento  
**Escopo:** preparar a migração controlada da produção FinanPy da VPS
`srvjosemaria` para o Homelab, usando `finanpy.com.br` como domínio público.

## Decisão

O FinanPy seguirá o padrão validado do UrbanLive e Brabus Store: Docker Swarm
de nó único, imagem Linux/amd64 publicada no GHCR e referenciada por digest,
Cloudflare Tunnel dedicado e Traefik compartilhado na rede `edge`.

O Homelab recebe somente manifestos versionados e uma imagem imutável. Ele não
executa checkout, build, push ou deploy baseado em `latest`. PostgreSQL e mídia
serão migrados por ensaio obrigatório, e a VPS continuará como contingência
após o corte inicial.

## Estado de origem confirmado

| Item | Estado |
|---|---|
| Host | VPS `srvjosemaria`, Ubuntu 24.04 |
| Aplicação | Django 5.2.5, Python 3.13, Gunicorn e DRF |
| Persistência | PostgreSQL 16 e `/srv/finanpy/media` |
| Proxy público | Nginx no host, web em `127.0.0.1:8001` |
| Domínio atual | `www.investiorion.com` |
| Domínio alvo registrado | `finanpy.com.br` |
| Deploy atual | GitHub Actions -> SSH root -> Compose com build local |
| Revisão em produção | `fd5c076` |
| Dados observados | PostgreSQL ~66 MB; mídia ~104 KB |

## Objetivos de sucesso

- Uma revisão aprovada em `main` gera e publica imagem `linux/amd64` no GHCR.
- O deploy seleciona um digest completo e nunca uma tag mutável.
- `https://finanpy.com.br` chega por Cloudflare Tunnel -> Traefik -> Django,
  sem portas HTTP, HTTPS, PostgreSQL ou Gunicorn publicadas pelo host.
- PostgreSQL e mídia são restaurados, com checksums e contagens agregadas
  compatíveis com a origem.
- Migrations são executadas uma vez por release, fora do serviço web.
- Web opera com uma réplica desejada, healthcheck de liveness e rollback de
  imagem para release compatível.
- A validação inclui navegação pública, login e fluxo autenticado não
  destrutivo; uma resposta HTTP verde não basta.
- A VPS permanece intacta como caminho de retorno até aprovação explícita.

## Não objetivos

- Alta disponibilidade, segundo nó, banco replicado, Kubernetes ou backup
  externo automatizado.
- Redis, Celery, Sentry, S3 ou mudanças de produto sem necessidade de deploy.
- Exclusão da VPS após o primeiro corte.
- Publicar secrets, dados financeiros, usuários, e-mails, saldos ou mídia no
  Git, vault, logs ou plano.

## Arquitetura alvo

```text
GitHub Actions
  -> testes + check --deploy + build Linux/amd64
  -> GHCR: ghcr.io/melojrx/finanpyv2@sha256:<digest>
  -> operador autorizado executa scripts/deploy-homelab.sh <digest>

Internet
  -> Cloudflare DNS, TLS e WAF para finanpy.com.br
  -> Tunnel dedicado finanpy-edge_cloudflared
  -> Traefik existente na rede overlay edge
  -> finanpy_web:8000
  -> finanpy_postgres:5432, somente finanpy_backend
```

| Recurso | Contrato |
|---|---|
| `edge` | rede overlay externa já existente; Tunnel, Traefik e `finanpy_web` |
| `finanpy_backend` | overlay interna para web, PostgreSQL e migration |
| `finanpy_web` | uma réplica; redes `edge` e `finanpy_backend`; sem `ports` |
| `finanpy_postgres` | PostgreSQL 16, uma réplica no nó `homelab`, sem `ports` |
| `finanpy_migrate` | job one-shot da mesma imagem antes de atualizar web |
| `finanpy_media` | volume local persistente de uploads |
| `finanpy_postgres_data` | volume local persistente do PostgreSQL |

## Configuração e secrets

Os secrets externos do Swarm são `finanpy_django_secret_key`,
`finanpy_postgres_password` e `finanpy_cloudflared_tunnel_token`. Um secret
SMTP só será criado se o SMTP já configurado precisar ser mantido.

Configuração não secreta fica em `/srv/finanpy/finanpy.env`, com permissão
restrita e fora do Git: domínio, hosts confiáveis, CSRF, banco, workers e
flags de segurança. O código deve aceitar `*_FILE` para ler secrets montados
em `/run/secrets` e deve tornar os domínios de cookie configuráveis. Para o
destino: `ALLOWED_HOSTS=finanpy.com.br,www.finanpy.com.br`,
`CSRF_TRUSTED_ORIGINS=https://finanpy.com.br,https://www.finanpy.com.br` e
`SESSION_COOKIE_DOMAIN=.finanpy.com.br`.

## Imagem, CI e runtime

O Dockerfile multi-stage atual já constrói Tailwind. A mudança separa o
entrypoint de web do entrypoint de migration: web inicia somente Gunicorn;
migration espera PostgreSQL, executa `migrate --noinput` e `collectstatic`.
O volume de mídia é montado nos dois serviços; arquivos estáticos permanecem
na imagem ou em volume explicitamente compartilhado com o web, nunca em um
alias Nginx do host.

O workflow substitui o deploy SSH por testes bloqueantes, verificação de
migrations, `check --deploy` e publicação GHCR. O digest produzido é a única
entrada do controlador de deploy.

## Saúde, rollout e retorno

Será criado `GET /health/liveness/`, independente do banco, e
`GET /health/readiness/`, que verifica PostgreSQL. A liveness alimenta o
`HEALTHCHECK`; readiness é gate do controlador e do monitor.

O serviço web usa `parallelism: 1`, `order: start-first`, monitoramento de
falhas e `failure_action: rollback`. Rollback trata apenas a imagem: uma
migration precisa ser expansiva e compatível com a imagem anterior. O rollback
do corte público é restaurar a rota Cloudflare para a VPS; novas escritas no
Homelab durante uma falha exigem reconciliação explícita.

## Estratégia de dados e corte

1. Produzir dump lógico da VPS, cópia da mídia, hashes, tamanhos e contagens
   agregadas de referência.
2. Restaurar os artefatos em volumes isolados do Homelab e executar migrations.
3. Validar schema, contagens, mídia, login e operação autenticada sem escrita
   financeira antes de expor o domínio.
4. Em janela autorizada, bloquear escrita na VPS, repetir dump e cópia final,
   restaurar o delta e validar o stack privado.
5. Alterar a rota Cloudflare de `finanpy.com.br` somente após todos os gates.
6. Observar logs e monitoramento; retornar para a VPS ao primeiro gate crítico
   falho e conservar ambas as bases para reconciliação.

## Critérios de aceite

1. CI bloqueia publicação quando testes, migrations ou `check --deploy` falham.
2. A imagem de produção tem digest completo verificável e o Homelab não faz
   build nem checkout.
3. O Swarm mostra web, PostgreSQL e Tunnel saudáveis; banco não tem porta ou
   rede pública.
4. Cloudflare entrega HTTPS válido em `finanpy.com.br`.
5. Liveness e readiness retornam 200 no caminho público.
6. Dados e mídia restaurados batem com o inventário agregado de origem.
7. Login e fluxo autenticado essencial foram validados com evidência.
8. Uptime Kuma monitora domínio, readiness e o serviço essencial.
9. O procedimento de retorno à VPS é documentado e executável antes do corte.

## Gates de autorização

Este desenho autoriza somente o planejamento e a implementação local dos
artefatos. Criar Tunnel, registrar secrets, copiar dados, alterar DNS, fazer
deploy no Homelab e executar o corte público requerem confirmação operacional
específica do usuário no momento de cada etapa.
