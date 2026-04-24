# Deploy em VPS Ubuntu com Docker Compose

Este guia descreve o deploy de produção atual do FinanPy usando Docker Compose,
PostgreSQL, Gunicorn e Nginx. O objetivo é ser simples, reproduzível e adequado
para uma VPS Ubuntu sem adicionar Redis, Celery, S3 ou Sentry antes da hora.

## Arquivos de Deploy

- `Dockerfile`: imagem Django baseada em `python:3.13-slim`, com usuário
  não-root.
- `docker-compose.prod.yml`: serviços `web`, `db` e `nginx`.
- `docker/entrypoint.sh`: aguarda PostgreSQL, roda migrações e coleta estáticos.
- `docker/nginx.conf`: serve `/static/`, `/media/` e faz proxy para o Django.
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

## Subir Produção

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
```

Ver logs:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production logs -f web
```

Criar superusuário:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production exec web python manage.py createsuperuser
```

## HTTPS

O Compose atual expõe Nginx em HTTP na porta `80`. Para produção real, coloque
HTTPS na frente antes de manter `SECURE_SSL_REDIRECT=true`. Opções simples:

- Usar um proxy externo com TLS, como Cloudflare ou proxy reverso da VPS.
- Expandir o Nginx local com certificados Let's Encrypt em uma etapa futura.

Para um teste temporário por IP sem TLS, use:

```env
SECURE_SSL_REDIRECT=false
SECURE_HSTS_SECONDS=0
```

Não deixe essa configuração como produção final.

## Operação Básica

Aplicar migrations manualmente, se necessário:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production exec web python manage.py migrate
```

Coletar static manualmente:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production exec web python manage.py collectstatic --noinput
```

Parar:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production down
```

Backup simples do PostgreSQL:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production exec db \
  sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' > backup_finanpy.sql
```

## Checklist de Produção

- [ ] `.env.production` criado e fora do Git.
- [ ] `SECRET_KEY` forte configurada.
- [ ] `ALLOWED_HOSTS` contém domínio/IP correto.
- [ ] `CSRF_TRUSTED_ORIGINS` contém as URLs HTTPS.
- [ ] `POSTGRES_PASSWORD` forte configurada.
- [ ] HTTPS configurado antes de habilitar HSTS definitivo.
- [ ] `docker compose ... up -d --build` executado.
- [ ] Superusuário criado.
- [ ] Static e media servidos pelo Nginx.
