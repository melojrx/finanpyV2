# Deploy em VPS Ubuntu com Docker Compose

Este guia descreve o deploy de produção atual do FinanPy usando Docker Compose,
PostgreSQL, Gunicorn e Nginx no host. O objetivo é ser simples, reproduzível e
adequado para uma VPS Ubuntu sem adicionar Redis, Celery, S3 ou Sentry antes da
hora.

## Ambiente Atual

Situação auditada em 2026-07-19:

- VPS: `root@38.52.128.62`.
- Hostname: `srvjosemaria`.
- Diretório da aplicação: `/srv/apps/finanpy`.
- Branch em produção: `main`.
- URL pública temporária: `https://www.investiorion.com/`.
- Domínio futuro previsto: `https://finanpy.com.br/`.
- Compose ativo: `/srv/apps/finanpy/docker-compose.vps.yml`.
- Containers esperados:
  - `finanpy-web-1`: Django/Gunicorn, publicado somente em
    `127.0.0.1:8001`.
  - `finanpy-db-1`: PostgreSQL 16.
- Nginx ativo é o do host, não um container deste stack.
- Configuração Nginx do host:
  - `/etc/nginx/sites-available/finanpy`.
  - `/etc/nginx/sites-enabled/finanpy`.
  - TLS via Certbot em `/etc/letsencrypt/live/investiorion.com/`.
  - `/static/` servido por alias de `/srv/finanpy/staticfiles/`.
  - `/media/` servido por alias de `/srv/finanpy/media/`.
  - tráfego da aplicação proxied para `http://127.0.0.1:8001`.

Validações HTTP confirmadas:

- `https://www.investiorion.com/` retorna `200`.
- `https://www.investiorion.com/login/` retorna `200`.
- `https://www.investiorion.com/admin/` redireciona para login do admin.
- `https://www.investiorion.com/manifest.webmanifest` retorna `200`.
- `https://www.investiorion.com/sw.js` retorna `200`.

Ao migrar para `finanpy.com.br`, atualizar pelo menos:

- DNS para a VPS.
- Nginx `server_name` e certificados.
- `ALLOWED_HOSTS`.
- `CSRF_TRUSTED_ORIGINS`.
- `SESSION_COOKIE_DOMAIN` e `CSRF_COOKIE_DOMAIN` em
  `core.settings_production`, hoje fixados para `.investiorion.com`.

## Arquivos de Deploy

- `Dockerfile`: imagem Django baseada em `python:3.13-slim`, com usuário
  não-root.
- `docker-compose.prod.yml`: serviços `web`, `db` e `nginx`.
- `docker-compose.vps.yml`: stack usado na VPS atual, com `web` e `db`; o Nginx
  roda no host.
- `docker/entrypoint.sh`: aguarda PostgreSQL, roda migrações e coleta estáticos.
- `docker/nginx.conf`: alternativa containerizada para servir `/static/`,
  `/media/` e proxy para o Django. Não é o Nginx ativo da VPS atual.
- `.github/workflows/deploy.yml`: deploy automático por SSH quando há push em
  `main` com mudanças fora de docs.
- `/srv/apps/finanpy/deploy.sh` na VPS: script operacional chamado pelo workflow.
- `.env.production.example`: exemplo de variáveis necessárias.

## Pré-requisitos na VPS

Instale Docker e o plugin Compose no Ubuntu:

```bash
sudo apt update
sudo apt install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
  sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

## Configuração

Crie o arquivo de ambiente:

```bash
cp .env.production.example .env.production
```

Edite os valores:

- `SECRET_KEY`: gere uma chave longa e única.
- `ALLOWED_HOSTS`: domínio e/ou IP da VPS.
- `CSRF_TRUSTED_ORIGINS`: origens HTTPS do domínio.
- `POSTGRES_PASSWORD`: senha forte do banco.
- `SECURE_SSL_REDIRECT`: mantenha `true` quando houver HTTPS.

Para gerar uma `SECRET_KEY`:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

## Fluxo de Deploy Atual

O fluxo normal é:

1. Push para `main`.
2. GitHub Actions executa `.github/workflows/deploy.yml`.
3. O workflow acessa a VPS por SSH como `root`.
4. Executa `/srv/apps/finanpy/deploy.sh`.
5. O script faz `git fetch origin main` e `git reset --hard origin/main`.
6. Rebuilda o serviço `web` com `docker-compose.vps.yml`.
7. Recria `finanpy-web-1`.
8. O entrypoint do container roda migrations e `collectstatic`.
9. O script valida `http://127.0.0.1:8001/`.

O workflow ignora mudanças puramente documentais (`docs/**`, `**.md` e
`.gitignore`). Para redeploy manual sem mudança de código, use o
`workflow_dispatch` com `force=true`.

## Subir Produção Manualmente

```bash
cd /srv/apps/finanpy
docker compose -f docker-compose.vps.yml --env-file .env.production up -d --build
```

Ver logs:

```bash
docker compose -f docker-compose.vps.yml --env-file .env.production logs -f web
```

Criar superusuário:

```bash
docker compose -f docker-compose.vps.yml --env-file .env.production exec web python manage.py createsuperuser
```

## HTTPS

Na VPS atual, HTTPS termina no Nginx do host com certificado Let's Encrypt para
`investiorion.com`. O container Django recebe o cabeçalho
`X-Forwarded-Proto: https` e `SECURE_SSL_REDIRECT=true` permanece habilitado.

Para um teste temporário por IP sem TLS, use:

```env
SECURE_SSL_REDIRECT=false
SECURE_HSTS_SECONDS=0
```

Não deixe essa configuração como produção final.

## Operação Básica

Aplicar migrations manualmente, se necessário:

```bash
docker compose -f docker-compose.vps.yml --env-file .env.production exec web python manage.py migrate
```

Coletar static manualmente:

```bash
docker compose -f docker-compose.vps.yml --env-file .env.production exec web python manage.py collectstatic --noinput
```

Parar:

```bash
docker compose -f docker-compose.vps.yml --env-file .env.production down
```

Backup simples do PostgreSQL:

```bash
docker compose -f docker-compose.vps.yml --env-file .env.production exec db \
  sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' > backup_finanpy.sql
```

## Checklist de Produção

- [ ] `.env.production` criado e fora do Git.
- [ ] `SECRET_KEY` forte configurada.
- [ ] `ALLOWED_HOSTS` contém domínio/IP correto.
- [ ] `CSRF_TRUSTED_ORIGINS` contém as URLs HTTPS.
- [ ] `POSTGRES_PASSWORD` forte configurada.
- [ ] HTTPS configurado antes de habilitar HSTS definitivo.
- [ ] `docker compose -f docker-compose.vps.yml ... up -d --build` executado.
- [ ] Superusuário criado.
- [ ] Static e media servidos pelo Nginx do host.
