# FinanPy Private Homelab Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (\`- [ ]\`) syntax for tracking.

**Goal:** Restaurar um snapshot recente do FinanPy no volume definitivo do Homelab e subir o stack privado por digest, sem alterar DNS ou publicar o domínio.

**Architecture:** Um manifesto bootstrap inicia apenas PostgreSQL e volumes; um controlador remoto restaura banco e mídia, compara o inventário agregado e só então chama o controlador existente de migration/web. Cloudflared permanece com o token atual até a validação pública; rotação é um gate posterior.

**Tech Stack:** Docker Swarm, PostgreSQL 16, pg_dump/pg_restore, GNU tar, Django, GHCR, cloudflared e shell POSIX.

## Global Constraints

- Executar inline, sem subagentes e sem worktree separado.
- Não imprimir, versionar ou registrar tokens, senhas, e-mails, dados financeiros ou dados pessoais.
- Não alterar DNS, criar hostnames públicos, publicar finanpy.com.br nem parar a VPS.
- Usar imagem GHCR por digest completo; nunca latest ou build no Homelab.
- Reusar o token atual temporariamente; rotação somente após validação pública autorizada.
- Recusar sobrescrever mídia já existente no volume definitivo.
- A VPS continua como origem e contingência; corte exige snapshot final e nova autorização.

---

## File Structure

| Arquivo | Responsabilidade |
|---|---|
| deploy/swarm/finanpy-bootstrap.yml | sobreposição que mantém web e migration em zero durante a restauração |
| scripts/homelab/restore-private-stack.sh | bootstrap, restauração e comparação segura no manager |
| tests/scripts/test-finanpy-swarm-manifest.sh | contrato do bootstrap sem portas |
| tests/scripts/test-restore-private-stack.sh | contrato de recusa de mídia não vazia e verificação pós-restauração |
| docs/deployment.md | runbook do ensaio privado |
| docs/superpowers/plans/2026-09-14-finanpy-homelab-migration.md | estado consolidado dos gates |

## Task 1: Adicionar bootstrap sem web ou migration

**Files:**
- Create: deploy/swarm/finanpy-bootstrap.yml
- Modify: tests/scripts/test-finanpy-swarm-manifest.sh

**Interfaces:** \`docker stack deploy -c finanpy.yml -c finanpy-bootstrap.yml finanpy\` cria \`finanpy_postgres=1/1\`, \`finanpy_web=0/0\` e \`finanpy_migrate=0/0\`.

- [ ] **Step 1: Escrever o teste vermelho**

Adicionar ao final de tests/scripts/test-finanpy-swarm-manifest.sh:

~~~
bootstrap=deploy/swarm/finanpy-bootstrap.yml
test -f "$bootstrap"
grep -Fq 'web:' "$bootstrap"
grep -Fq 'migrate:' "$bootstrap"
grep -Fq 'replicas: 0' "$bootstrap"
! grep -Eq '^\s+ports:' "$bootstrap"
~~~

- [ ] **Step 2: Verificar a falha**

Run: \`sh tests/scripts/test-finanpy-swarm-manifest.sh\`  
Expected: exit 1, pois o manifesto bootstrap não existe.

- [ ] **Step 3: Criar a sobreposição mínima**

Criar deploy/swarm/finanpy-bootstrap.yml:

~~~
version: "3.8"

services:
  migrate:
    deploy:
      replicas: 0
  web:
    deploy:
      replicas: 0
~~~

- [ ] **Step 4: Verificar a composição**

Run:

~~~
sh tests/scripts/test-finanpy-swarm-manifest.sh
set -a
. deploy/swarm/finanpy.env.example
set +a
docker stack config -c deploy/swarm/finanpy.yml -c deploy/swarm/finanpy-bootstrap.yml >/dev/null
~~~

Expected: exit 0 e nenhuma porta adicionada.

- [ ] **Step 5: Commit**

~~~
git add deploy/swarm/finanpy-bootstrap.yml tests/scripts/test-finanpy-swarm-manifest.sh
git commit -m "feat: add private restore bootstrap stack"
~~~

## Task 2: Criar controlador de restauração privada

**Files:**
- Create: scripts/homelab/restore-private-stack.sh
- Create: tests/scripts/test-restore-private-stack.sh

**Interfaces:** \`restore-private-stack.sh "$RELEASE_DIRECTORY" "$BACKUP_DIRECTORY" "$FINANPY_IMAGE"\` exige \`database.dump\`, \`media.tar.gz\` e \`source.inventory\`; recusa mídia existente e chama deploy-stack.sh somente depois de verify-rehearsal.sh.

- [ ] **Step 1: Escrever o teste vermelho**

Criar tests/scripts/test-restore-private-stack.sh:

~~~
#!/bin/sh
set -eu

script=scripts/homelab/restore-private-stack.sh
test -x "$script"
grep -Fq 'Media volume is not empty.' "$script"
grep -Fq 'pg_restore -U' "$script"
grep -Fq 'verify-rehearsal.sh' "$script"
grep -Fq 'finanpy-bootstrap.yml' "$script"
! grep -Eiq '(token|password|secret).*printf' "$script"
~~~

- [ ] **Step 2: Verificar a falha**

Run: \`sh tests/scripts/test-restore-private-stack.sh\`  
Expected: exit 1, pois o controlador não existe.

- [ ] **Step 3: Implementar o controlador**

Criar scripts/homelab/restore-private-stack.sh:

~~~
#!/bin/sh
set -eu

SCRIPT_DIRECTORY=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
FINANPY_ROOT='/srv/finanpy'
CONFIGURATION_FILE="$FINANPY_ROOT/finanpy.env"
POSTGRES_SERVICE='finanpy_postgres'
MEDIA_VOLUME='finanpy_finanpy_media'

. "$SCRIPT_DIRECTORY/load-env.sh"

[ "$#" -eq 3 ] || { echo 'Usage: restore-private-stack.sh RELEASE_DIRECTORY BACKUP_DIRECTORY FINANPY_IMAGE' >&2; exit 1; }
release_directory=$1
backup_directory=$2
FINANPY_IMAGE=$3
validate_finanpy_image "$FINANPY_IMAGE" || { echo 'Invalid image digest.' >&2; exit 1; }
case "$release_directory" in "$FINANPY_ROOT"/releases/*) ;; *) echo 'Invalid release directory.' >&2; exit 1 ;; esac
case "$backup_directory" in "$FINANPY_ROOT"/backups/*) ;; *) echo 'Invalid backup directory.' >&2; exit 1 ;; esac

load_env_file "$CONFIGURATION_FILE"
export FINANPY_IMAGE
for file in database.dump media.tar.gz source.inventory; do
  [ -r "$backup_directory/$file" ] || { echo "Missing backup file: $file" >&2; exit 1; }
done

stack_file="$release_directory/deploy/swarm/finanpy.yml"
bootstrap_file="$release_directory/deploy/swarm/finanpy-bootstrap.yml"
[ -r "$stack_file" ] && [ -r "$bootstrap_file" ] || { echo 'Bootstrap manifests are not readable.' >&2; exit 1; }
[ "$(docker info --format '{{.Swarm.LocalNodeState}}')" = active ] || { echo 'Docker Swarm is not active.' >&2; exit 1; }
docker network inspect edge >/dev/null 2>&1 || { echo 'Required network is missing: edge' >&2; exit 1; }
for secret in finanpy_django_secret_key finanpy_postgres_password finanpy_cloudflared_tunnel_token; do
  docker secret inspect "$secret" >/dev/null 2>&1 || { echo "Required secret is missing: $secret" >&2; exit 1; }
done

docker stack deploy --with-registry-auth --resolve-image always -c "$stack_file" -c "$bootstrap_file" finanpy
attempt=1
while [ "$attempt" -le 60 ]; do
  container_id=$(docker ps --filter "label=com.docker.swarm.service.name=$POSTGRES_SERVICE" --filter status=running --format '{{.ID}}' | sed -n '1p')
  if [ -n "$container_id" ] && [ "$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$container_id")" = healthy ]; then break; fi
  sleep 2
  attempt=$((attempt + 1))
done
[ "$attempt" -le 60 ] || { docker service ps --no-trunc "$POSTGRES_SERVICE" >&2; exit 1; }

media_path=$(docker volume inspect "$MEDIA_VOLUME" --format '{{.Mountpoint}}')
[ -z "$(find "$media_path" -mindepth 1 -print -quit)" ] || { echo 'Media volume is not empty.' >&2; exit 1; }
docker exec -i "$container_id" pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner --no-privileges < "$backup_directory/database.dump"
tar -xzf "$backup_directory/media.tar.gz" -C "$media_path"

docker exec "$container_id" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "select 'users=' || count(*) from auth_user union all select 'accounts=' || count(*) from accounts_account union all select 'categories=' || count(*) from categories_category union all select 'transactions=' || count(*) from transactions_transaction union all select 'budgets=' || count(*) from budgets_budget union all select 'monthly_plans=' || count(*) from budgets_monthlyplan union all select 'goals=' || count(*) from goals_goal union all select 'profiles=' || count(*) from profiles_profile union all select 'tags=' || count(*) from tags_tag order by 1" > "$backup_directory/target.inventory"

source_media="$backup_directory/source-media"
install -d -m 0700 "$source_media"
tar -xzf "$backup_directory/media.tar.gz" -C "$source_media"
"$release_directory/scripts/homelab/verify-rehearsal.sh" "$backup_directory/source.inventory" "$backup_directory/target.inventory" "$source_media" "$media_path"
"$release_directory/scripts/homelab/deploy-stack.sh" "$release_directory" "$FINANPY_IMAGE"
~~~

- [ ] **Step 4: Verificar o contrato**

Run:

~~~
sh tests/scripts/test-restore-private-stack.sh
sh -n scripts/homelab/restore-private-stack.sh
~~~

Expected: exit 0; não há valores de secrets em saída.

- [ ] **Step 5: Commit**

~~~
git add scripts/homelab/restore-private-stack.sh tests/scripts/test-restore-private-stack.sh
git commit -m "feat: add private FinanPy restore controller"
~~~

## Task 3: Documentar e verificar o release local

**Files:**
- Modify: docs/deployment.md
- Modify: docs/superpowers/plans/2026-09-14-finanpy-homelab-migration.md

**Interfaces:** o runbook exige backup em \`/srv/finanpy/backups/$BACKUP_ID\` e não autoriza DNS ou corte.

- [ ] **Step 1: Documentar o limite operacional**

Adicionar a docs/deployment.md:

~~~
## Ensaio privado no Homelab

O ensaio usa scripts/homelab/restore-private-stack.sh no manager Swarm. O backup
deve conter database.dump, media.tar.gz e source.inventory em
/srv/finanpy/backups/$BACKUP_ID. O controlador recusa mídia existente, compara
inventário/mídia antes de iniciar web e não cria nem altera DNS.
~~~

Atualizar Task 5 no plano de migração: token existe; deploy privado depende do controlador de restauração.

- [ ] **Step 2: Executar toda a verificação local**

Run:

~~~
.venv/bin/python manage.py test --verbosity 1
for test_script in tests/scripts/test-*.sh; do sh "$test_script"; done
sh -n scripts/deploy-homelab.sh scripts/homelab/load-env.sh scripts/homelab/deploy-stack.sh scripts/homelab/restore-private-stack.sh scripts/homelab/verify-rehearsal.sh
set -a
. deploy/swarm/finanpy.env.example
set +a
docker stack config -c deploy/swarm/finanpy.yml -c deploy/swarm/finanpy-bootstrap.yml >/dev/null
docker build --quiet --tag finanpy:private-deploy-verify .
~~~

Expected: 333 testes Django, todos os contratos shell e build Docker passam.

- [ ] **Step 3: Commit**

~~~
git add docs/deployment.md docs/superpowers/plans/2026-09-14-finanpy-homelab-migration.md
git commit -m "docs: add private Homelab restore procedure"
~~~

## Task 4: Executar o deploy privado autorizado

**Files:**
- Create remotely: /srv/finanpy/finanpy.env
- Create remotely: /srv/finanpy/backups/$BACKUP_ID/{database.dump,media.tar.gz,source.inventory}

**Interfaces:** o controlador recebe um release staged por digest e backup transferido VPS → Homelab por SSH, sem persistir o dump na máquina local.

- [ ] **Step 1: Publicar a revisão e obter o digest**

Run:

~~~
RUN_ID=$(gh run list --workflow deploy.yml --limit 1 --json databaseId --jq '.[0].databaseId')
gh run watch "$RUN_ID" --exit-status
FINANPY_IMAGE=$(gh run view "$RUN_ID" --log | sed -nE 's/.*(ghcr.io\/melojrx\/finanpyv2@sha256:[a-f0-9]{64}).*/\1/p' | tail -1)
printf '%s\n' "$FINANPY_IMAGE" | grep -Eq '^ghcr.io/melojrx/finanpyv2@sha256:[a-f0-9]{64}$'
BACKUP_ID=$(date -u +%Y%m%dT%H%M%SZ)
export FINANPY_IMAGE BACKUP_ID
~~~

Expected: run successful e digest completo.

- [ ] **Step 2: Criar a configuração não secreta**

Criar /srv/finanpy/finanpy.env com valores estáticos e os parâmetros SMTP não
secretos da VPS. O pipe não mostra valores na saída e não inclui password,
token ou FINANPY_IMAGE.

Run:

~~~
{
  printf '%s\n' \
    'POSTGRES_DB=finanpy' \
    'POSTGRES_USER=finanpy' \
    'ALLOWED_HOSTS=finanpy.com.br,www.finanpy.com.br,127.0.0.1,localhost' \
    'CSRF_TRUSTED_ORIGINS=https://finanpy.com.br,https://www.finanpy.com.br' \
    'SESSION_COOKIE_DOMAIN=.finanpy.com.br' \
    'CSRF_COOKIE_DOMAIN=.finanpy.com.br' \
    'SECURE_SSL_REDIRECT=true' \
    'SECURE_HSTS_SECONDS=31536000' \
    'SESSION_COOKIE_SECURE=true' \
    'CSRF_COOKIE_SECURE=true' \
    'LOG_LEVEL=INFO'
  ssh neo-vps "awk -F= '/^(EMAIL_BACKEND|EMAIL_HOST|EMAIL_PORT|EMAIL_USE_TLS|DEFAULT_FROM_EMAIL)=/{print}' /srv/apps/finanpy/.env.production"
} | ssh melojr@100.93.170.120 "sudo install -d -m 0750 -o root -g root /srv/finanpy && sudo tee /srv/finanpy/finanpy.env >/dev/null && sudo chmod 0640 /srv/finanpy/finanpy.env && sudo chown root:root /srv/finanpy/finanpy.env"
ssh melojr@100.93.170.120 "sudo stat -c '%a %U:%G %n' /srv/finanpy/finanpy.env"
~~~

Expected: \`640 root:root /srv/finanpy/finanpy.env\`.

- [ ] **Step 3: Gerar e transferir snapshot recente**

Na VPS, gerar pg_dump custom, media.tar.gz, source.inventory e SHA-256 em
/srv/finanpy-migration/$BACKUP_ID. Transferir por pipes SSH para
/srv/finanpy/backups/$BACKUP_ID e comparar hashes sem imprimir dados.

Expected: hashes de banco, mídia e inventário iguais na origem e no Homelab.

- [ ] **Step 4: Staging e restauração**

Run:

~~~
scripts/deploy-homelab.sh --stage-only "$FINANPY_IMAGE"
DIGEST=${FINANPY_IMAGE#ghcr.io/melojrx/finanpyv2@sha256:}
RELEASE_DIRECTORY=/srv/finanpy/releases/sha256-$DIGEST
BACKUP_DIRECTORY=/srv/finanpy/backups/$BACKUP_ID
ssh melojr@100.93.170.120 "sudo $RELEASE_DIRECTORY/scripts/homelab/restore-private-stack.sh $RELEASE_DIRECTORY $BACKUP_DIRECTORY $FINANPY_IMAGE"
~~~

Expected: inventário/mídia conferem; postgres=1/1, web=1/1 e migrate=0/0.

- [ ] **Step 5: Validar internamente sem DNS**

Run:

~~~
ssh melojr@100.93.170.120 "sudo docker service ls --format '{{.Name}} {{.Replicas}}' | grep '^finanpy'"
ssh melojr@100.93.170.120 "sudo docker service logs --tail 50 finanpy_web"
~~~

Validar liveness/readiness por container e login pelo Traefik na rede edge com
Host: finanpy.com.br. Não executar escrita financeira.

Expected: health 200, login sem CSRF e VPS funcional.

- [ ] **Step 6: Registrar evidência sem corte**

Registrar no vault data, digest, hashes, agregados, serviços e healthchecks.
Manter Task 6 pendente: DNS/corte e rotação exigem nova autorização.

## Plan self-review

- Task 1 impede web e migration antes da restauração.
- Task 2 recusa sobrescrever uploads e verifica dados antes de iniciar web.
- Task 3 cobre documentação, testes e build.
- Task 4 não cria DNS, hostname público, revogação de token ou desativação da VPS.
