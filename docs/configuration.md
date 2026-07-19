# Configuração

O projeto usa duas configurações Django oficiais:

- `core.settings`: desenvolvimento local com SQLite e `DEBUG=True`.
- `core.settings_production`: produção com variáveis de ambiente,
  PostgreSQL, cookies seguros e logs no console.

## Desenvolvimento Local

O desenvolvimento local não exige `.env`.

Configuração padrão:

- Banco: `db.sqlite3`.
- Static source: `static/`.
- Static coletado: `staticfiles/`.
- Media: `media/`.
- Email: console backend.
- CSS: `django-tailwind` via app `theme`.

Comandos principais:

```bash
./scripts/dj migrate
./scripts/dj runserver
./scripts/dj test
```

Use `./scripts/dj` neste checkout para limpar variáveis de ambiente do shell que
podem quebrar o Python local (`PYTHONHOME`, `PYTHONPATH`, `LD_LIBRARY_PATH`).

## Produção

Use `DJANGO_SETTINGS_MODULE=core.settings_production`.

Na VPS atual, a aplicação roda em `/srv/apps/finanpy` usando
`docker-compose.vps.yml`. O domínio público temporário é
`https://www.investiorion.com/`; a migração futura será para
`https://finanpy.com.br/`.

Variáveis obrigatórias:

| Variável | Descrição |
| --- | --- |
| `SECRET_KEY` | Chave secreta longa e única do Django. |
| `ALLOWED_HOSTS` | Lista separada por vírgula com domínio/IP permitidos. |
| `POSTGRES_PASSWORD` | Senha do banco PostgreSQL. |

Variáveis de banco:

| Variável | Padrão |
| --- | --- |
| `POSTGRES_DB` | `finanpy` |
| `POSTGRES_USER` | `finanpy` |
| `POSTGRES_HOST` | `db` |
| `POSTGRES_PORT` | `5432` |
| `DB_CONN_MAX_AGE` | `600` |

Variáveis HTTP/segurança:

| Variável | Padrão |
| --- | --- |
| `CSRF_TRUSTED_ORIGINS` | vazio |
| `SECURE_SSL_REDIRECT` | `true` |
| `SECURE_HSTS_SECONDS` | `31536000` |
| `SECURE_HSTS_INCLUDE_SUBDOMAINS` | `true` |
| `SECURE_HSTS_PRELOAD` | `true` |
| `SESSION_COOKIE_SECURE` | `true` |
| `CSRF_COOKIE_SECURE` | `true` |
| `SESSION_COOKIE_AGE` | `3600` |

Observação: em `core.settings_production`, `SESSION_COOKIE_DOMAIN` e
`CSRF_COOKIE_DOMAIN` estão fixados em `.investiorion.com`. Ao migrar para
`finanpy.com.br`, esses valores devem ser atualizados junto com Nginx,
certificados, `ALLOWED_HOSTS` e `CSRF_TRUSTED_ORIGINS`.

Variáveis de email:

| Variável | Padrão |
| --- | --- |
| `EMAIL_BACKEND` | `django.core.mail.backends.smtp.EmailBackend` |
| `EMAIL_HOST` | `localhost` |
| `EMAIL_PORT` | `587` |
| `EMAIL_USE_TLS` | `true` |
| `EMAIL_HOST_USER` | vazio |
| `EMAIL_HOST_PASSWORD` | vazio |
| `DEFAULT_FROM_EMAIL` | `FinanPy <noreply@finanpy.local>` |
| `SERVER_EMAIL` | valor de `DEFAULT_FROM_EMAIL` |

Logging:

| Variável | Padrão |
| --- | --- |
| `LOG_LEVEL` | `INFO` |

Em produção, logs vão para stdout/stderr para serem coletados por Docker ou
systemd.

## Arquivos de Ambiente

Use `.env.production.example` como base:

```bash
cp .env.production.example .env.production
```

O arquivo real `.env.production` não deve ser versionado.

## Validação

Validar settings de desenvolvimento:

```bash
./scripts/dj check
```

Validar settings de produção:

```bash
env \
  SECRET_KEY='uma-chave-longa-e-segura-com-mais-de-50-caracteres' \
  ALLOWED_HOSTS='localhost,127.0.0.1' \
  POSTGRES_PASSWORD='senha-local-de-validacao' \
  CSRF_TRUSTED_ORIGINS='https://localhost,https://127.0.0.1' \
  ./scripts/dj check --deploy --settings=core.settings_production
```

## Decisões Deliberadas

- Redis não faz parte do deploy inicial.
- Celery não faz parte do deploy inicial.
- Sentry não faz parte do deploy inicial.
- S3/storage externo não faz parte do deploy inicial.
- TailwindCSS é compilado localmente via `django-tailwind`; o runtime de
  produção recebe o CSS já gerado pelo stage Node do `Dockerfile`.
