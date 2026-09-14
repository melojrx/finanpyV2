# FinanPy Homelab Automated Deploy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan inline, task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Promover automaticamente cada imagem FinanPy aprovada em `main` ao
Docker Swarm do Homelab, por digest imutável e através de um runner isolado.

**Architecture:** O GitHub-hosted runner testa e publica a imagem
`linux/amd64`; o output do build é o digest SHA-256 completo. Um runner
dedicado no Homelab executa somente um wrapper root-owned, que valida checkout
e digest, materializa arquivos de release em `/srv/finanpy` e chama o
controlador Swarm existente para migration, rollout e readiness.

**Tech Stack:** GitHub Actions, GitHub Actions self-hosted runner, GHCR,
POSIX shell, systemd, sudoers, Docker Swarm, Django 5.2, PostgreSQL 16,
Traefik e cloudflared.

## Global Constraints

- A branch de trabalho é `codex/finanpy-homelab-automated-deploy`, derivada de `main`; executar inline e sem worktree ou subagentes.
- Publicar somente `ghcr.io/melojrx/finanpyv2@sha256:<64-hex>`; nunca tag mutável, build ou checkout no Homelab.
- O runner é `runner-finanpy`, sem login e sem grupo `docker`; não compartilhar runner, diretório, wrapper, sudoers ou concorrência com Brabus/UrbanLive.
- O único checkout aceito pelo wrapper é `/opt/actions-runner-finanpy/_work/finanpy_v2/finanpy_v2`.
- O único comando sudo liberado ao runner é `/usr/local/sbin/deploy-finanpy-release` com o checkout literal e o digest validado.
- Manter `/srv/finanpy/finanpy.env`, secrets Swarm, tokens de runner, credenciais GHCR, dumps e dados financeiros fora do Git, logs, workflow summary e vault.
- Preservar os volumes `finanpy_finanpy_postgres_data`, `finanpy_finanpy_staticfiles` e `finanpy_finanpy_media`; não executar rollback automático de banco.
- Este plano não autoriza hostname público no Tunnel, DNS, rotação do token Cloudflare nem desligamento da VPS.
- Healthchecks Django internos precisam de `X-Forwarded-Proto: https`; Traefik, quando configurado no corte público, deve receber o mesmo header no healthcheck.

---

## File Structure

| Arquivo | Responsabilidade |
| --- | --- |
| `.github/workflows/deploy.yml` | Expõe digest do publish e adiciona promoção no runner FinanPy. |
| `deploy/homelab/deploy-finanpy-release` | Fonte versionada do wrapper root-owned que valida e promove um release. |
| `deploy/homelab/actions.runner.finanpy.service` | Unidade systemd do runner dedicado. |
| `deploy/homelab/runner-finanpy.sudoers` | Privilégio mínimo do runner para o wrapper literal. |
| `tests/scripts/test-github-workflow.sh` | Contrato estático de CI, publicação e promoção por digest. |
| `tests/scripts/test-finanpy-release-wrapper.sh` | Contrato estático do wrapper, unidade e sudoers. |
| `docs/deployment.md` | Operação do deploy automatizado e diagnóstico sem segredos. |
| `.../Obsidian Vault/02-Projetos/FinanPy/04-Migracao-VPS-para-Homelab.md` | Evidência de onboarding e gates ainda pendentes. |

## Required execution setup

- Conferir antes de cada task: `git status --short --branch` e preservar
  mudanças que não pertençam a este plano.
- Para testes Python, usar o ambiente existente `.venv`; não tocar em banco de
  produção ou em arquivos de secret.
- Para operações remotas, usar `ssh -o BatchMode=yes melojr@100.93.170.120`.
  Inspecionar secrets apenas pelo nome (`docker secret inspect <nome>`), nunca
  pelo valor.
- Para registrar o runner, obter token efêmero pelo fluxo oficial do GitHub no
  momento do gate remoto; nunca inserir esse token em arquivo, histórico ou
  comando versionado.

### Task 1: Definir e testar o contrato da promoção por GitHub Actions

**Files:**
- Modify: `.github/workflows/deploy.yml:67-114`
- Modify: `tests/scripts/test-github-workflow.sh:1-15`

**Interfaces:**
- Produces: `jobs.publish.outputs.image`, contendo somente o digest de 64 hex
  retornado por `steps.image.outputs.digest`.
- Consumes: o job `deploy` usa
  `ghcr.io/melojrx/finanpyv2@${{ needs.publish.outputs.image }}`.
- Produces: job `deploy` em `[self-hosted, homelab-finanpy-deploy]`, grupo
  `deploy-finanpy-production`, dependente de `publish`.

- [ ] **Step 1: Estender o teste estático primeiro**

Substitua o conteúdo de `tests/scripts/test-github-workflow.sh` por:

```sh
#!/bin/sh
set -eu

workflow=.github/workflows/deploy.yml

grep -Fq 'docker/build-push-action' "$workflow"
grep -Fq 'makemigrations --check --dry-run' "$workflow"
grep -Fq 'python manage.py test' "$workflow"
grep -Fq 'python manage.py check --deploy' "$workflow"
grep -Fq 'type=sha,format=long,prefix=sha-' "$workflow"
grep -Fq 'mkdir -p logs' "$workflow"
grep -Fq 'npm run build' "$workflow"
grep -Fq 'outputs:' "$workflow"
grep -Fq 'image: ${{ steps.image.outputs.digest }}' "$workflow"
grep -Fq 'needs: publish' "$workflow"
grep -Fq 'runs-on: [self-hosted, homelab-finanpy-deploy]' "$workflow"
grep -Fq 'group: deploy-finanpy-production' "$workflow"
grep -Fq 'sudo /usr/local/sbin/deploy-finanpy-release' "$workflow"
grep -Fq 'ghcr.io/melojrx/finanpyv2@${{ needs.publish.outputs.image }}' "$workflow"
! grep -Fq 'appleboy/ssh-action' "$workflow"
! grep -Eq 'finanpyv2:latest|type=raw,value=latest' "$workflow"
! grep -Fq 'ssh ' "$workflow"
```

- [ ] **Step 2: Executar e confirmar o estado vermelho**

Run: `sh tests/scripts/test-github-workflow.sh`

Expected: exit diferente de zero, porque o workflow ainda não tem output do
job `publish` nem job `deploy`.

- [ ] **Step 3: Adicionar output e job de deploy mínimo**

Em `.github/workflows/deploy.yml`, acrescente ao job `publish`, imediatamente
após `timeout-minutes`, e adicione o job abaixo depois dele:

```yaml
    outputs:
      image: ${{ steps.image.outputs.digest }}
```

```yaml
  deploy:
    name: Deploy to Homelab
    needs: publish
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    runs-on: [self-hosted, homelab-finanpy-deploy]
    timeout-minutes: 15
    concurrency:
      group: deploy-finanpy-production
      cancel-in-progress: false
    permissions:
      contents: read
    steps:
      - name: Checkout deployment controller
        uses: actions/checkout@v4

      - name: Promote immutable image
        run: |
          sudo /usr/local/sbin/deploy-finanpy-release \
            "$GITHUB_WORKSPACE" \
            "ghcr.io/melojrx/finanpyv2@${{ needs.publish.outputs.image }}"

      - name: Record release
        run: |
          {
            printf '%s\n' '### Homelab deployment'
            printf '%s\n' "- Commit: $GITHUB_SHA"
            printf '%s\n' "- Image: ghcr.io/melojrx/finanpyv2@${{ needs.publish.outputs.image }}"
            printf '%s\n' '- Controller: deploy-finanpy-release'
          } >> "$GITHUB_STEP_SUMMARY"
```

Mantenha `permissions: packages: write` no nível atual do workflow: o job
`publish` ainda depende dela para autenticar no GHCR. Não acrescente SSH,
tokens ou variáveis de secret.

- [ ] **Step 4: Executar o contrato estático**

Run: `sh tests/scripts/test-github-workflow.sh`

Expected: exit 0.

- [ ] **Step 5: Commit da fronteira CI**

```bash
git add .github/workflows/deploy.yml tests/scripts/test-github-workflow.sh
git commit -m "ci: promote FinanPy digests on Homelab runner"
```

### Task 2: Versionar o wrapper, serviço e privilégio mínimo do runner

**Files:**
- Create: `deploy/homelab/deploy-finanpy-release`
- Create: `deploy/homelab/actions.runner.finanpy.service`
- Create: `deploy/homelab/runner-finanpy.sudoers`
- Create: `tests/scripts/test-finanpy-release-wrapper.sh`

**Interfaces:**
- Consumes: `deploy-finanpy-release <checkout> <digest>`.
- Produces: `/srv/finanpy/releases/sha256-<digest>` com apenas
  `deploy/swarm` e `scripts/homelab` e chama
  `/srv/finanpy/bin/deploy-stack.sh <release-directory> <digest>`.
- Consumes: a regra sudoers invoca exatamente o wrapper e o checkout literal.

- [ ] **Step 1: Escrever o teste estático em estado vermelho**

Crie `tests/scripts/test-finanpy-release-wrapper.sh`:

```sh
#!/bin/sh
set -eu

wrapper=deploy/homelab/deploy-finanpy-release
unit=deploy/homelab/actions.runner.finanpy.service
sudoers=deploy/homelab/runner-finanpy.sudoers

test -x "$wrapper"
test -f "$unit"
test -f "$sudoers"
grep -Fq "FINANPY_ROOT='/srv/finanpy'" "$wrapper"
grep -Fq '/opt/actions-runner-finanpy/_work/finanpy_v2/finanpy_v2' "$wrapper"
grep -Fq 'validate_finanpy_image "$image"' "$wrapper"
grep -Fq 'tar -C "$checkout" -cf - deploy/swarm scripts/homelab' "$wrapper"
grep -Fq 'exec "$FINANPY_ROOT/bin/deploy-stack.sh" "$release_directory" "$image"' "$wrapper"
grep -Fq 'User=runner-finanpy' "$unit"
grep -Fq 'WorkingDirectory=/opt/actions-runner-finanpy' "$unit"
grep -Fq 'PrivateTmp=true' "$unit"
grep -Fxq 'runner-finanpy ALL=(root) NOPASSWD: /usr/local/sbin/deploy-finanpy-release /opt/actions-runner-finanpy/_work/finanpy_v2/finanpy_v2 *' "$sudoers"
! grep -Eq '(^|[^[:alnum:]_])docker([^[:alnum:]_]|$)' "$sudoers"
```

Run: `sh tests/scripts/test-finanpy-release-wrapper.sh`

Expected: exit diferente de zero, porque os três arquivos ainda não existem.

- [ ] **Step 2: Criar o wrapper validado**

Crie `deploy/homelab/deploy-finanpy-release` com modo executável:

```sh
#!/bin/sh
set -eu

FINANPY_ROOT='/srv/finanpy'
EXPECTED_CHECKOUT='/opt/actions-runner-finanpy/_work/finanpy_v2/finanpy_v2'

checkout=${1:?Usage: deploy-finanpy-release <checkout> <image-digest>}
image=${2:?Usage: deploy-finanpy-release <checkout> <image-digest>}

[ "$#" -eq 2 ] || {
  printf '%s\n' 'Usage: deploy-finanpy-release <checkout> <image-digest>' >&2
  exit 1
}
case "$checkout" in
  "$EXPECTED_CHECKOUT") ;;
  *) printf '%s\n' 'Invalid FinanPy checkout path.' >&2; exit 1 ;;
esac

. "$checkout/scripts/homelab/load-env.sh"
validate_finanpy_image "$image" || {
  printf '%s\n' 'Invalid FinanPy image digest.' >&2
  exit 1
}

for file in \
  deploy/swarm/finanpy.yml \
  deploy/swarm/finanpy-edge.yml \
  deploy/swarm/finanpy.env.example \
  scripts/homelab/load-env.sh \
  scripts/homelab/deploy-stack.sh; do
  test -f "$checkout/$file" || {
    printf 'Required release file is missing: %s\n' "$file" >&2
    exit 1
  }
done

digest=${image#ghcr.io/melojrx/finanpyv2@sha256:}
release_directory="$FINANPY_ROOT/releases/sha256-$digest"
install -d -m 0750 -o root -g root "$release_directory"
tar -C "$checkout" -cf - deploy/swarm scripts/homelab | tar -xf - -C "$release_directory"
install -m 0755 "$release_directory/scripts/homelab/load-env.sh" "$FINANPY_ROOT/bin/load-env.sh"
install -m 0755 "$release_directory/scripts/homelab/deploy-stack.sh" "$FINANPY_ROOT/bin/deploy-stack.sh"
exec "$FINANPY_ROOT/bin/deploy-stack.sh" "$release_directory" "$image"
```

- [ ] **Step 3: Criar a unidade e sudoers**

Crie `deploy/homelab/actions.runner.finanpy.service`:

```ini
[Unit]
Description=GitHub Actions runner for FinanPy Homelab deploys
After=network-online.target docker.service
Wants=network-online.target

[Service]
User=runner-finanpy
WorkingDirectory=/opt/actions-runner-finanpy
ExecStart=/opt/actions-runner-finanpy/run.sh
Restart=always
RestartSec=5
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

Crie `deploy/homelab/runner-finanpy.sudoers`:

```sudoers
runner-finanpy ALL=(root) NOPASSWD: /usr/local/sbin/deploy-finanpy-release /opt/actions-runner-finanpy/_work/finanpy_v2/finanpy_v2 *
```

- [ ] **Step 4: Verificar shell, permissões de fonte e contrato**

Run:

```bash
chmod 0755 deploy/homelab/deploy-finanpy-release
sh -n deploy/homelab/deploy-finanpy-release
sh tests/scripts/test-finanpy-release-wrapper.sh
```

Expected: todos os comandos retornam exit 0. O teste confirma a fronteira
estática; a sintaxe sudoers só será validada no host pelo `visudo -cf` da Task
3.

- [ ] **Step 5: Commit dos artefatos de plataforma**

```bash
git add deploy/homelab tests/scripts/test-finanpy-release-wrapper.sh
git commit -m "feat: add isolated FinanPy deployment runner contract"
```

### Task 3: Provisionar o runner dedicado no Homelab

**Files:**
- Source: `deploy/homelab/deploy-finanpy-release`
- Source: `deploy/homelab/actions.runner.finanpy.service`
- Source: `deploy/homelab/runner-finanpy.sudoers`
- Remote create: `/usr/local/sbin/deploy-finanpy-release`
- Remote create: `/etc/systemd/system/actions.runner.finanpy.service`
- Remote create: `/etc/sudoers.d/runner-finanpy`

**Interfaces:**
- Consumes: token efêmero obtido no GitHub para o repositório
  `melojrx/finanpy_v2`, label `homelab-finanpy-deploy`.
- Produces: serviço ativo e um runner online sem acesso direto ao Docker.

- [ ] **Step 1: Conferir estado remoto sem alterar nada**

Run:

```bash
ssh -o BatchMode=yes melojr@100.93.170.120 \
  'id runner-finanpy 2>/dev/null || true; sudo systemctl is-active docker; sudo docker info --format "{{.Swarm.LocalNodeState}}"; sudo docker service ls --format "{{.Name}} {{.ID}}"'
```

Expected: Docker ativo, Swarm `active`, e a lista de serviços Brabus/UrbanLive
anotada como baseline. Não criar usuário se ele já existir com atributos
incompatíveis; nesse caso, interromper e revisar antes de modificar identidade
de conta.

- [ ] **Step 2: Instalar os arquivos privilegiados e validar antes de ativar**

Run:

```bash
scp deploy/homelab/deploy-finanpy-release \
  deploy/homelab/actions.runner.finanpy.service \
  deploy/homelab/runner-finanpy.sudoers \
  melojr@100.93.170.120:/tmp/
ssh -o BatchMode=yes melojr@100.93.170.120 \
  'sudo install -o root -g root -m 0755 /tmp/deploy-finanpy-release /usr/local/sbin/deploy-finanpy-release && sudo install -o root -g root -m 0644 /tmp/actions.runner.finanpy.service /etc/systemd/system/actions.runner.finanpy.service && sudo install -o root -g root -m 0440 /tmp/runner-finanpy.sudoers /etc/sudoers.d/runner-finanpy && sudo visudo -cf /etc/sudoers.d/runner-finanpy && sudo systemctl daemon-reload'
```

Expected: `parsed: /etc/sudoers.d/runner-finanpy` e exit 0. Não copiar
`/srv/finanpy/finanpy.env`, secrets ou backups.

- [ ] **Step 3: Criar a conta, instalar runner e registrar por token efêmero**

No Homelab, criar a conta e diretório somente se a inspeção confirmou que não
existiam:

```bash
ssh -o BatchMode=yes melojr@100.93.170.120 \
  'sudo useradd --system --create-home --home-dir /opt/actions-runner-finanpy --shell /usr/sbin/nologin runner-finanpy && sudo install -d -o runner-finanpy -g runner-finanpy -m 0750 /opt/actions-runner-finanpy /srv/finanpy/bin /srv/finanpy/releases'
```

Baixe o pacote oficial do runner para `linux-x64` no diretório remoto. No
mesmo terminal interativo em que o token foi gerado, leia-o sem eco, registre
o runner e descarte a variável imediatamente:

```bash
read -rs FINANPY_RUNNER_TOKEN
printf '\n'
sudo -u runner-finanpy /opt/actions-runner-finanpy/config.sh \
  --unattended \
  --url https://github.com/melojrx/finanpy_v2 \
  --token "$FINANPY_RUNNER_TOKEN" \
  --name homelab-finanpy-deploy \
  --labels self-hosted,Linux,X64,homelab-finanpy-deploy \
  --work _work \
  --replace
unset FINANPY_RUNNER_TOKEN
```

O token existe somente durante esse terminal e não é salvo em arquivo,
histórico, commit ou chat.

- [ ] **Step 4: Habilitar e validar isolamento**

Run:

```bash
ssh -o BatchMode=yes melojr@100.93.170.120 \
  'sudo systemctl enable --now actions.runner.finanpy.service && sudo systemctl is-active actions.runner.finanpy.service && sudo stat -c "%U:%G %a %n" /usr/local/sbin/deploy-finanpy-release /etc/sudoers.d/runner-finanpy && sudo -l -U runner-finanpy'
```

Expected: serviço `active`; wrapper `root:root 755`; sudoers `root:root 440`;
`sudo -l` lista apenas `deploy-finanpy-release` com o checkout FinanPy. A UI
GitHub deve mostrar `homelab-finanpy-deploy` online antes da próxima task.

- [ ] **Step 5: Registrar a infraestrutura sem segredos**

Atualize o vault FinanPy com nome do runner, serviço, wrapper, diretório e
limite sudoers; não inclua token de registro, conteúdo de secrets nem
credenciais. Faça commit apenas do vault:

```bash
git add '/home/jrmelo/Documentos/Obsidian Vault/02-Projetos/FinanPy/04-Migracao-VPS-para-Homelab.md'
git commit -m "docs: record FinanPy Homelab runner onboarding"
```

### Task 4: Validar uma promoção automatizada e o isolamento de stacks

**Files:**
- Modify: `docs/deployment.md:1-31`
- Modify: `/home/jrmelo/Documentos/Obsidian Vault/02-Projetos/FinanPy/04-Migracao-VPS-para-Homelab.md`

**Interfaces:**
- Consumes: workflow de `main`, runner online e stack privada FinanPy já
  validada.
- Produces: evidência de commit, run URL, digest, migration concluída,
  `finanpy_web` saudável e baseline inalterada de Brabus/UrbanLive.

- [ ] **Step 1: Registrar baseline antes da promoção**

Run:

```bash
ssh -o BatchMode=yes melojr@100.93.170.120 \
  'sudo docker service ls --format "{{.Name}} {{.Image}} {{.Replicas}}" | sort; sudo docker service ps --no-trunc finanpy_web; sudo docker service ps --no-trunc finanpy_migrate'
```

Expected: salvar a saída operacionalmente fora do Git. Ela deve identificar
as imagens e tasks atuais de `brabustore_*`, `urbanlive_*` e `finanpy_*`, sem
inspecionar secrets ou banco.

- [ ] **Step 2: Disparar uma única promoção pelo fluxo autorizado**

Use um commit já aprovado em `main` ou `workflow_dispatch` que percorra os
jobs `test`, `publish` e `deploy`; não invoque manualmente o wrapper em
paralelo. Acompanhe o último run dessa branch:

```bash
run_id=$(gh run list --repo melojrx/finanpy_v2 --branch main --limit 1 --json databaseId --jq '.[0].databaseId')
test -n "$run_id"
gh run view "$run_id" --repo melojrx/finanpy_v2 --json status,conclusion,url,jobs
```

Expected: `test`, `publish` e `deploy` com conclusão `success`; o resumo do
deploy mostra somente commit, digest e controlador.

- [ ] **Step 3: Validar serviços e digest promovido**

```bash
ssh -o BatchMode=yes melojr@100.93.170.120 \
  'sudo docker service ls --format "{{.Name}} {{.Image}} {{.Replicas}}" | sort; sudo docker service inspect finanpy_web --format "{{.Spec.TaskTemplate.ContainerSpec.Image}}"; sudo docker service ps --no-trunc finanpy_migrate; sudo docker service ps --no-trunc finanpy_web'
```

Expected: `finanpy_web=1/1`, `finanpy_postgres=1/1`,
`finanpy_migrate=0/0`, e a imagem de `finanpy_web` exatamente
igual à imagem publicada no resumo do workflow.

- [ ] **Step 4: Executar gates de saúde sem exposição pública**

Run:

```bash
ssh -o BatchMode=yes melojr@100.93.170.120 \
  'container=$(sudo docker ps --filter label=com.docker.swarm.service.name=finanpy_web --filter status=running --format "{{.ID}}" | sed -n "1p"); test -n "$container"; sudo docker inspect --format "{{.State.Health.Status}}" "$container"; sudo docker exec "$container" python -c "import urllib.request; request=urllib.request.Request(\"http://127.0.0.1:8000/health/readiness/\", headers={\"X-Forwarded-Proto\": \"https\"}); urllib.request.urlopen(request, timeout=5)"'
```

Expected: health Docker `healthy` e readiness exit 0. Não criar hostname
Cloudflare, nem tratar a ausência de URL pública como falha deste gate.

- [ ] **Step 5: Confirmar isolamento e registrar o resultado**

Compare a lista de serviços da Step 3 com a baseline da Step 1. Brabus e
UrbanLive devem manter a mesma imagem e nenhuma task nova. Atualize
`docs/deployment.md` com o fluxo operacional abaixo e o vault apenas com o
resultado agregado:

```markdown
## Deploy automatizado no Homelab

Um push em `main` executa testes, publica um digest GHCR e promove-o pelo
runner `homelab-finanpy-deploy`. Acompanhe o run pelo GitHub Actions; não rode
o wrapper manualmente em paralelo. Em falha, registre run, commit, digest,
estado de `finanpy_migrate` e `finanpy_web`, então inspecione os logs do
serviço afetado. O controlador não reverte banco nem remove volumes.
```

```bash
git add docs/deployment.md '/home/jrmelo/Documentos/Obsidian Vault/02-Projetos/FinanPy/04-Migracao-VPS-para-Homelab.md'
git commit -m "docs: record FinanPy automated deployment validation"
```

### Task 5: Executar a verificação final da mudança

**Files:**
- Verify: `.github/workflows/deploy.yml`
- Verify: `deploy/homelab/deploy-finanpy-release`
- Verify: `deploy/homelab/actions.runner.finanpy.service`
- Verify: `deploy/homelab/runner-finanpy.sudoers`
- Verify: `tests/scripts/test-github-workflow.sh`
- Verify: `tests/scripts/test-finanpy-release-wrapper.sh`
- Verify: `docs/deployment.md`

**Interfaces:** confirma os contratos locais antes de merge e o estado remoto
da automação antes do futuro corte público.

- [ ] **Step 1: Executar verificações locais completas**

Run:

```bash
sh tests/scripts/test-github-workflow.sh
sh tests/scripts/test-finanpy-release-wrapper.sh
sh tests/scripts/test-finanpy-swarm-manifest.sh
sh tests/scripts/test-restore-private-stack.sh
.venv/bin/python manage.py test --verbosity 1
docker build -t finanpy:automation-check .
git diff --check main...HEAD
```

Expected: todos retornam exit 0; a suíte Django mantém 333 testes passando;
a imagem constrói para a plataforma local; `git diff --check` não aponta
whitespace.

- [ ] **Step 2: Verificar revisão e sincronismo remoto**

Run:

```bash
git status --short --branch
git log --oneline main..HEAD
gh run list --repo melojrx/finanpy_v2 --branch main --limit 5
ssh -o BatchMode=yes melojr@100.93.170.120 \
  'sudo systemctl is-active actions.runner.finanpy.service; sudo docker service ls --format "{{.Name}} {{.Image}} {{.Replicas}}" | sort'
```

Expected: branch sem arquivos inesperados, commits desta automação visíveis,
último run de deploy aprovado e runner `active`. Não fazer merge, corte
Cloudflare ou rotação de token nesta task de verificação.

## Plan self-review

- Cobertura da especificação: Task 1 cobre CI/digest/concorrência; Task 2
  cobre fonte do wrapper, unit e sudoers; Task 3 cria o runner isolado; Task 4
  verifica promoção, saúde e não interferência; Task 5 fecha verificações.
- Segurança: todos os comandos de secret são por nome; token de runner é
  efêmero e não é persistido; nenhum passo abre portas, cria hostname público
  ou altera DNS.
- Consistência: o checkout, nome do runner, wrapper, release root e grupos de
  concorrência são os mesmos em todas as tasks.
