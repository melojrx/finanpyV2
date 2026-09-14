# FinanPy Homelab Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrar o FinanPy da VPS para um stack Swarm isolado no Homelab, publicado em `finanpy.com.br`, preservando dados e retorno controlado à VPS.

**Architecture:** GitHub Actions valida e publica imagem `linux/amd64` no GHCR por digest. Um controlador local envia somente manifestos ao Homelab, roda migration one-shot e atualiza o web. Cloudflare Tunnel dedicado encaminha `finanpy.com.br` ao Traefik; PostgreSQL e mídia ficam numa rede interna e volumes locais persistentes.

**Tech Stack:** Python 3.13, Django 5.2.5, Gunicorn, Django REST Framework, PostgreSQL 16, Docker, Docker Swarm, Traefik v3.7, cloudflared, GHCR, GitHub Actions e Uptime Kuma.

## Global Constraints

- Produção pública alvo: `finanpy.com.br` e `www.finanpy.com.br`.
- Desenvolvimento continua local; produção usa `docker stack deploy` no manager `homelab`.
- Imagem sempre por digest completo; nunca `latest` ou build no Homelab.
- Sem `ports` no web, PostgreSQL ou migration; exposição somente por Tunnel e Traefik.
- Secrets são Swarm Secrets em `/run/secrets`, nunca valores no Git, docs ou logs.
- Web opera com uma réplica desejada; a segunda só pode existir transitoriamente em `start-first`.
- Migrations de rollout precisam ser expansivas e compatíveis com a imagem anterior.
- Não criar Tunnel, secrets, backup, DNS ou deploy durante tarefas locais sem autorização operacional específica.

---

## File Structure

| Arquivo | Responsabilidade |
|---|---|
| `core/settings_production.py` | arquivos de secret e domínios configuráveis |
| `core/health_views.py` e `core/urls.py` | liveness e readiness |
| `core/tests.py` | contratos de saúde e produção |
| `docker/entrypoint-web.sh` | inicia somente Gunicorn |
| `docker/entrypoint-migrate.sh` | espera banco, migra e coleta estáticos |
| `Dockerfile` | entrypoint web e imagem imutável |
| `.github/workflows/deploy.yml` | CI bloqueante e publicação GHCR |
| `deploy/swarm/finanpy.yml` | app, banco, volumes, redes e rollout |
| `deploy/swarm/finanpy-edge.yml` | Tunnel dedicado e referência à edge |
| `deploy/swarm/finanpy.env.example` | configuração não secreta documentada |
| `scripts/homelab/load-env.sh` | valida configuração e digest |
| `scripts/homelab/deploy-stack.sh` | migration e atualização remota |
| `scripts/deploy-homelab.sh` | controlador local por SSH/Tailscale |
| `scripts/homelab/verify-rehearsal.sh` | comparação segura do ensaio de dados |

## Required execution setup

- Criar ambiente isolado: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`.
- Nunca usar o banco de produção como banco de teste local.
- Antes de qualquer ação remota, registrar `git status --short`, commit, digest e
  estado dos serviços existentes no Homelab.

## Blocking gates before rehearsal

- Pipeline GHCR publicada e digest candidato disponível.
- Segredos existem no Swarm por nome, sem leitura dos valores.
- Backup de PostgreSQL e mídia possui hash, tamanho e restauração comprovada.
- Configuração `finanpy.com.br` foi validada em stack privada antes do DNS.

## Execution status

- [x] Task 1 — settings compatíveis com Swarm Secrets e domínio configurável
      (`ac856d2`).
- [x] Task 2 — health endpoints e entrypoints web/migration separados
      (`6a2ec64`).
- [x] Task 3 — CI bloqueante e publicação GHCR por SHA/digest (`87d3878`).
- [x] Task 4 — manifests Swarm, edge dedicado e controlador de release
      (`6e36d24`).
- [x] Verificador local de ensaio de inventário/mídia implementado.
- [ ] Task 5 — provisionamento Homelab e cópia/restauração de dados; dados
      restaurados e verificados; stack privado ainda depende de imagem GHCR e
      token do Tunnel.
- [ ] Task 6 — corte DNS/Tunnel; requer aprovação nova após ensaio aprovado.

## Gate 5 — evidência do ensaio privado (14/09/2026)

- Homelab: Swarm ativo; segredos `finanpy_django_secret_key` e
  `finanpy_postgres_password` criados somente por nome; nenhum valor foi
  registrado.
- Backup de origem: `20260914T125619Z`, produzido na VPS com `pg_dump` custom e
  mídia protegida.
- Hashes de transferência conferidos: banco
  `d4eb3efec9ebaeb8612ea377df95af7d4327ae857b23dcc92bed2720b3fd6fbe`, mídia
  `0db0d74a3749b6c0a3aaa175ffe1870a1d1afbaa34a70ec70e2812f3bec64641` e
  inventário `8c5c10a426521d898f72240c1f8e19476a773c1fa82c595fddcdaf256fc04a98`.
- Restauração PostgreSQL isolada concluída; os agregados conferem: 6 usuários,
  2 contas, 57 categorias, 707 transações, 1 orçamento, 2 planos mensais,
  0 metas, 6 perfis e 8 tags.
- Mídia conferida por manifesto SHA-256
  `4665428758c006bf2fde2891d9e1a75cbaf1790375caf9cec363477d2eabc8a8` e
  total de 93.245 bytes.
- Recursos temporários do ensaio foram removidos; backup e inventários permanecem
  protegidos no Homelab para o próximo gate.
- Gate pendente: publicar imagem candidata no GHCR por digest completo e
  provisionar o token do Tunnel dedicado antes de validar o stack privado.

### Task 1: Tornar settings compatível com Swarm Secrets e domínio novo

**Files:**
- Modify: `core/settings_production.py:15-105`
- Modify: `core/tests.py`
- Create: `.env.production.example`

**Interfaces:** `env_secret("SECRET_KEY", required=True)` lê
`SECRET_KEY_FILE` antes de `SECRET_KEY`; `SESSION_COOKIE_DOMAIN` e
`CSRF_COOKIE_DOMAIN` vêm do ambiente e podem ser `.finanpy.com.br`.

- [ ] **Step 1: Escrever testes de contrato**

```python
def test_secret_file_has_priority_over_literal_value(self):
    with TemporaryDirectory() as directory:
        secret_file = Path(directory) / "secret"
        secret_file.write_text("from-file\n", encoding="utf-8")
        with patch.dict(os.environ, {"SETTING": "literal", "SETTING_FILE": str(secret_file)}, clear=True):
            self.assertEqual(env_secret("SETTING"), "from-file")
```

- [ ] **Step 2: Executar o estado vermelho**

Run: `.venv/bin/python manage.py test core.tests -v 2`  
Expected: FAIL porque `env_secret` ainda não existe.

- [ ] **Step 3: Implementar leitura de arquivo e settings configuráveis**

```python
def env_secret(name, default=None, required=False):
    file_name = os.getenv(f"{name}_FILE")
    value = Path(file_name).read_text(encoding="utf-8").strip() if file_name else os.getenv(name, default)
    if required and not value:
        raise ImproperlyConfigured(f"Missing required environment variable: {name}")
    return value

SESSION_COOKIE_DOMAIN = env("SESSION_COOKIE_DOMAIN", "") or None
CSRF_COOKIE_DOMAIN = env("CSRF_COOKIE_DOMAIN", "") or None
```

Use `env_secret` para `SECRET_KEY`, `POSTGRES_PASSWORD` e
`EMAIL_HOST_PASSWORD`. Preserve o comportamento atual quando `*_FILE` não
existir.

- [ ] **Step 4: Criar exemplo seguro e verificar**

```dotenv
SECRET_KEY_FILE=/run/secrets/finanpy_django_secret_key
POSTGRES_PASSWORD_FILE=/run/secrets/finanpy_postgres_password
ALLOWED_HOSTS=finanpy.com.br,www.finanpy.com.br
CSRF_TRUSTED_ORIGINS=https://finanpy.com.br,https://www.finanpy.com.br
SESSION_COOKIE_DOMAIN=.finanpy.com.br
CSRF_COOKIE_DOMAIN=.finanpy.com.br
```

Run: `.venv/bin/python manage.py test core.tests -v 2 && .venv/bin/python manage.py check --deploy`  
Expected: testes passam; `check --deploy` não relata erro.

- [ ] **Step 5: Commit**

```bash
git add core/settings_production.py core/tests.py .env.production.example
git commit -m "feat: support Swarm secrets in production settings"
```

### Task 2: Separar health, web runtime e migration one-shot

**Files:**
- Create: `core/health_views.py`
- Modify: `core/urls.py`
- Modify: `core/tests.py`
- Create: `docker/entrypoint-web.sh`
- Create: `docker/entrypoint-migrate.sh`
- Modify: `Dockerfile:55-61`

**Interfaces:** `GET /health/liveness/` retorna 200 sem banco; `GET
/health/readiness/` retorna 200 somente quando `connections["default"]` está
disponível. Só `entrypoint-migrate.sh` executa migrations e collectstatic.

- [ ] **Step 1: Escrever testes de saúde**

```python
def test_liveness_does_not_require_database(self):
    with patch("django.db.connections.__getitem__", side_effect=AssertionError):
        response = self.client.get("/health/liveness/")
    self.assertEqual(response.status_code, 200)
    self.assertEqual(response.json(), {"alive": True})
```

- [ ] **Step 2: Confirmar falha antes da implementação**

Run: `.venv/bin/python manage.py test core.tests -v 2`  
Expected: FAIL por rota ausente.

- [ ] **Step 3: Implementar views e entrypoints**

```sh
# docker/entrypoint-web.sh
#!/bin/sh
set -eu
exec gunicorn core.wsgi:application --bind 0.0.0.0:8000 --workers "${GUNICORN_WORKERS:-2}" --timeout 60
```

```sh
# docker/entrypoint-migrate.sh
#!/bin/sh
set -eu
python manage.py migrate --noinput
python manage.py collectstatic --noinput
```

`entrypoint-migrate.sh` deve incluir espera limitada por PostgreSQL antes do
primeiro comando; `entrypoint-web.sh` não pode chamar `migrate` ou
`collectstatic`.

- [ ] **Step 4: Verificar runtime**

Run: `docker build -t finanpy:test . && docker run --rm finanpy:test /usr/local/bin/entrypoint-web.sh --help`  
Expected: imagem constrói; o entrypoint não tenta conexão com banco.

- [ ] **Step 5: Commit**

```bash
git add core docker Dockerfile
git commit -m "feat: isolate FinanPy migration and health checks"
```

### Task 3: Trocar CI de deploy VPS por gate GHCR imutável

**Files:**
- Modify: `.github/workflows/deploy.yml`
- Create: `tests/scripts/test-github-workflow.sh`

**Interfaces:** pull request roda testes, `makemigrations --check --dry-run` e
`check --deploy`; push em `main` publica `ghcr.io/melojrx/finanpyv2` e expõe o
digest. O workflow não contém SSH ou deploy remoto.

- [ ] **Step 1: Escrever teste estático de workflow**

```sh
#!/bin/sh
set -eu
workflow=.github/workflows/deploy.yml
grep -Fq 'docker/build-push-action' "$workflow"
grep -Fq 'makemigrations --check --dry-run' "$workflow"
grep -Fq 'python manage.py test' "$workflow"
grep -Fq 'python manage.py check --deploy' "$workflow"
! grep -Fq 'appleboy/ssh-action' "$workflow"
! grep -Fq 'latest' "$workflow"
```

- [ ] **Step 2: Confirmar falha e implementar workflow**

Run: `sh tests/scripts/test-github-workflow.sh`  
Expected: FAIL no workflow VPS atual.

O workflow novo usa `actions/checkout`, `actions/setup-python`, instala
`requirements.txt`, executa os gates, autentica `ghcr.io` com `GITHUB_TOKEN` e
publica somente após aprovação com tag SHA e digest de saída. Preserve gatilho
manual para publicar a mesma revisão, sem SSH.

- [ ] **Step 3: Verificar e commit**

Run: `sh tests/scripts/test-github-workflow.sh`  
Expected: exit 0.

```bash
git add .github/workflows/deploy.yml tests/scripts/test-github-workflow.sh
git commit -m "ci: publish tested FinanPy images to GHCR"
```

### Task 4: Adicionar manifests Swarm isolados e controlador por digest

**Files:**
- Create: `deploy/swarm/finanpy.yml`
- Create: `deploy/swarm/finanpy-edge.yml`
- Create: `deploy/swarm/finanpy.env.example`
- Create: `scripts/homelab/load-env.sh`
- Create: `scripts/homelab/deploy-stack.sh`
- Create: `scripts/deploy-homelab.sh`
- Create: `tests/scripts/test-finanpy-swarm-manifest.sh`

**Interfaces:** `scripts/deploy-homelab.sh [--stage-only]
ghcr.io/melojrx/finanpyv2@sha256:<64-hex>` aceita somente digest; stack cria
`finanpy_backend`, volumes persistentes e serviços sem portas públicas.

- [ ] **Step 1: Escrever teste de manifesto**

```sh
#!/bin/sh
set -eu
manifest=deploy/swarm/finanpy.yml
! grep -Eq '^\s+ports:' "$manifest"
grep -Fq 'finanpy_backend:' "$manifest"
grep -Fq 'finanpy_postgres_data:' "$manifest"
grep -Fq 'finanpy_media:' "$manifest"
grep -Fq 'failure_action: rollback' "$manifest"
grep -Fq 'finanpy_django_secret_key' "$manifest"
```

- [ ] **Step 2: Implementar contrato Swarm**

`finanpy.yml` declara `web`, `postgres` e `migrate`; `postgres` e `migrate`
ficam somente em `finanpy_backend`; `web` recebe labels Traefik para
`Host(\`finanpy.com.br\`) || Host(\`www.finanpy.com.br\`)`, uma réplica e
healthcheck de liveness. O serviço `migrate` inicia com zero réplicas e é
executado pelo controlador antes do rollout.

`finanpy-edge.yml` declara apenas Cloudflared com token por secret, ligado à
`edge` existente. Não criar um segundo Traefik. O arquivo de ambiente contém
somente valores não secretos e a referência da imagem é injetada pelo
controlador.

- [ ] **Step 3: Implementar o controlador seguro**

O controlador segue o padrão UrbanLive: valida regex do digest, cria
`/srv/finanpy/releases/sha256-<digest>`, transfere somente `deploy/swarm` e
`scripts/homelab`, instala scripts em `/srv/finanpy/bin` e chama
`docker stack deploy --with-registry-auth`. O script remoto verifica Swarm,
redes e secrets por nome, roda a migration uma vez e exige readiness antes de
declarar sucesso.

- [ ] **Step 4: Verificar e commit**

Run: `sh tests/scripts/test-finanpy-swarm-manifest.sh && docker stack config -c deploy/swarm/finanpy.yml`  
Expected: exit 0 e configuração sem `ports`.

```bash
git add deploy scripts tests/scripts
git commit -m "feat: add FinanPy immutable Swarm deployment"
```

### Task 5: Provisionar Homelab e ensaiar restauração sob autorização separada

**Files:**
- Create: `scripts/homelab/verify-rehearsal.sh`
- Modify: `docs/deployment.md`
- Modify: `/home/jrmelo/Documentos/Obsidian Vault/02-Projetos/FinanPy/04-Migracao-VPS-para-Homelab.md`

**Interfaces:** o verificador recebe caminhos de dump, mídia e inventário
agregado; não recebe ou imprime dados financeiros. Saída inclui somente hashes,
tamanhos, contagens e status dos serviços.

- [ ] **Step 1: Obter aprovação operacional explícita**

Confirmar em mensagem separada: criação do Tunnel, secrets, diretórios em
`/srv/finanpy`, cópia de dados da VPS e deploy privado. Sem esta confirmação,
não executar SSH que altere estado.

- [ ] **Step 2: Criar pré-requisitos e verificar somente nomes**

Criar rede `finanpy_backend`, secrets previstos, diretórios operacionais e
Tunnel dedicado. Confirmar com `docker network ls`, `docker secret ls` e
`docker service ls`, sem inspecionar valores.

- [ ] **Step 3: Produzir e restaurar ensaio de dados**

Na VPS, gerar dump consistente e cópia de mídia em local temporário protegido;
registrar SHA-256, bytes e contagens agregadas. Restaurar em volumes FinanPy
no Homelab isolados da rota pública; rodar migration e comparar o inventário.

- [ ] **Step 4: Validar stack privado**

Executar release com digest explícito, checar `finanpy_web=1/1`,
`finanpy_postgres=1/1`, liveness/readiness e login autenticado não destrutivo.
O ensaio falha se qualquer contagem, mídia ou health divergir.

- [ ] **Step 5: Documentar evidência e commit**

Registrar somente resultados agregados e o digest nos documentos. Não
versionar backups, `.env`, tokens ou saída de banco.

### Task 6: Corte público somente com aprovação nova

**Files:**
- Modify: `/home/jrmelo/Documentos/Obsidian Vault/02-Projetos/FinanPy/00-FinanPy.md`
- Modify: `/home/jrmelo/Documentos/Obsidian Vault/02-Projetos/FinanPy/04-Migracao-VPS-para-Homelab.md`

- [ ] **Step 1: Confirmar gates e janela de manutenção**

Exigir aprovação explícita para congelar escrita, executar cópia final e mudar
Cloudflare. Confirmar digest, backup restaurado, VPS saudável e caminho de
retorno antes de tocar DNS.

- [ ] **Step 2: Sincronizar dados finais e validar privadamente**

Bloquear escrita na origem pelo procedimento aprovado, gerar dump/mídia final,
restaurar e repetir validação de dados, login e readiness.

- [ ] **Step 3: Roteamento e observação**

Associar `finanpy.com.br` e `www.finanpy.com.br` ao Tunnel FinanPy no
Cloudflare. Validar HTTPS, headers de proxy, cookies, CSRF, navegação, login e
uma operação autenticada segura. Adicionar monitor no Uptime Kuma.

- [ ] **Step 4: Reversão se um gate falhar**

Retornar rota Cloudflare para VPS, preservar logs e inventários de ambas as
bases. Não descartar dados do Homelab; abrir reconciliação antes de novo corte.

- [ ] **Step 5: Atualizar vault com evidência**

Anotar data, commit, digest, contagens agregadas, resultados de health e
decisão de manter ou retornar a VPS. Nunca adicionar credenciais ou dados
financeiros.

## Plan self-review

- O plano cobre settings, saúde, runtime, CI, Swarm, dados, corte e rollback.
- Nenhuma tarefa autoriza implicitamente mudança de DNS, secrets, VPS ou
  Homelab; as duas últimas exigem autorização operacional separada.
- A imagem por digest, migration one-shot, dados privados e VPS de contingência
  são consistentes com a especificação.
