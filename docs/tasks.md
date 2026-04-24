# Plano Vivo de Produção - FinanPy

Este documento acompanha a execução do plano para alinhar documentação e código,
preparar produção em VPS Ubuntu com Docker Compose e registrar evidências de cada
sprint.

## Status Geral

- [x] Sprint 0 - Planejamento documentado
- [x] Sprint 1 - Settings de produção e dependências mínimas
- [x] Sprint 2 - Docker Compose para VPS Ubuntu
- [x] Sprint 3 - Documentação oficial alinhada ao código
- [x] Sprint 4 - Validação final e evidências

## Sprint 0 - Planejamento Documentado

Objetivo: transformar o plano aprovado em tarefas executáveis e rastreáveis.

- [x] Definir `docs/` como fonte oficial de documentação.
- [x] Criar este `docs/tasks.md` como documento vivo.
- [x] Registrar critérios de aceite técnicos e documentais.

Evidências:

- Documento criado em `docs/tasks.md`.
- Plano estruturado em sprints pequenos para reduzir risco.

## Sprint 1 - Settings de Produção

Objetivo: manter desenvolvimento simples e criar configuração segura para produção.

- [x] Manter `core/settings.py` como configuração de desenvolvimento.
- [x] Reescrever `core/settings_production.py` com variáveis de ambiente.
- [x] Configurar PostgreSQL via variáveis simples.
- [x] Configurar `SECRET_KEY`, `ALLOWED_HOSTS` e `CSRF_TRUSTED_ORIGINS`.
- [x] Configurar cookies seguros, proxy SSL, HSTS e headers de segurança.
- [x] Trocar logging de produção para console.
- [x] Adicionar dependências mínimas: `gunicorn` e `psycopg[binary]`.

Evidências:

- `core/settings_production.py` agora falha cedo se `SECRET_KEY`,
  `ALLOWED_HOSTS` ou `POSTGRES_PASSWORD` estiverem ausentes.
- `requirements.txt` recebeu `gunicorn==23.0.0` e
  `psycopg[binary]==3.2.10`.
- Comando executado com sucesso:
  `venv/bin/python manage.py check --settings=core.settings_production`.
- Comando executado com sucesso:
  `venv/bin/python manage.py check --deploy --settings=core.settings_production`.

## Sprint 2 - Docker Compose para VPS Ubuntu

Objetivo: entregar um deploy simples e reproduzível com Django, PostgreSQL e Nginx.

- [x] Criar `Dockerfile`.
- [x] Criar `.dockerignore`.
- [x] Criar `docker-compose.prod.yml`.
- [x] Criar entrypoint para `migrate`, `collectstatic` e Gunicorn.
- [x] Criar configuração Nginx para proxy, static e media.
- [x] Usar volumes persistentes para banco, static e media.
- [x] Rodar containers com usuário não-root no serviço Django.

Evidências:

- `Dockerfile` criado com `python:3.13-slim`, usuário `app` não-root e
  Gunicorn como comando padrão.
- `docker-compose.prod.yml` criado com serviços `web`, `db` e `nginx`.
- `docker/entrypoint.sh` criado para aguardar PostgreSQL, rodar `migrate` e
  `collectstatic`.
- `docker/nginx.conf` criado para servir `/static/`, `/media/` e fazer proxy
  para o Django.
- `.env.production.example` criado com variáveis necessárias para VPS.
- Comando executado com sucesso:
  `docker compose -f docker-compose.prod.yml --env-file .env.production.example config`.

## Sprint 3 - Documentação Oficial Alinhada

Objetivo: a documentação oficial deve refletir o que existe hoje no código.

- [x] Criar `docs/backlog.md` com itens documentados mas ainda não implementados.
- [x] Criar `docs/deployment.md` com VPS Ubuntu + Docker Compose.
- [x] Atualizar `docs/README.md` removendo links inexistentes.
- [x] Atualizar `docs/architecture.md` com a arquitetura real.
- [x] Atualizar `docs/configuration.md` com variáveis realmente suportadas.
- [x] Atualizar `docs/setup-guide.md` para desenvolvimento local real.
- [x] Atualizar `docs/database-structure.md` com os models existentes.
- [x] Mover recursos futuros para backlog em vez de documentá-los como atuais.

Evidências:

- `docs/backlog.md` criado com recursos futuros e itens removidos do escopo
  oficial atual.
- `docs/deployment.md` criado com instruções de VPS Ubuntu + Docker Compose.
- `docs/README.md`, `docs/architecture.md`, `docs/configuration.md`,
  `docs/setup-guide.md` e `docs/database-structure.md` foram reescritos para
  refletir o código atual.
- `docs/troubleshooting.md`, `docs/frontend-guidelines.md` e
  `docs/static-media-configuration.md` tiveram referências antigas corrigidas.
- Busca executada para remover referências oficiais a docs inexistentes,
  dependências não instaladas e rotas antigas.

## Sprint 4 - Validação Final

Objetivo: comprovar que o projeto continua funcional e que produção está verificável.

- [x] Executar `venv/bin/python manage.py check`.
- [x] Executar `venv/bin/python manage.py test`.
- [x] Executar `venv/bin/python manage.py makemigrations --check --dry-run`.
- [x] Executar `venv/bin/python manage.py check --deploy --settings=core.settings_production` com variáveis de produção.
- [x] Validar configuração Docker Compose.
- [x] Registrar limitações e próximos passos.

Evidências:

- `venv/bin/python manage.py check`: passou sem issues.
- `venv/bin/python manage.py makemigrations --check --dry-run`: `No changes detected`.
- `venv/bin/python manage.py check --deploy --settings=core.settings_production`: passou sem issues com variáveis mínimas de produção.
- `venv/bin/python manage.py test`: 32 testes executados com sucesso.
- `docker compose -f docker-compose.prod.yml --env-file .env.production.example config --quiet`: passou.
- Smoke test Docker executado com projeto isolado `finanpy_codex_smoke`:
  build concluído, containers `db`, `web` e `nginx` subiram, migrations rodaram,
  `collectstatic` copiou 130 arquivos e Gunicorn iniciou 3 workers.
- `curl -I -H 'Host: example.com' http://127.0.0.1:8088/`: retornou `HTTP/1.1 200 OK`.
- Containers e volumes do smoke test foram removidos com `docker compose ... down -v`.

Limitações conhecidas:

- O deploy base expõe Nginx em HTTP. Para produção final, configure HTTPS antes
  de manter `SECURE_SSL_REDIRECT=true` e HSTS.
- O app `goals` segue como backlog.
- A cobertura de testes ainda precisa ser expandida nos apps com poucos testes.

## Backlog de Produção Pós-MVP

Itens abaixo não bloqueiam o primeiro deploy em VPS:

- [ ] Implementar app `goals`.
- [ ] Migrar Tailwind CDN para build local.
- [ ] Implementar anexos/comprovantes de transação.
- [ ] Implementar preferências avançadas de usuário e avatar.
- [ ] Adicionar Redis/cache quando houver necessidade medida.
- [ ] Adicionar Sentry/monitoramento após deploy base.
- [ ] Expandir testes de `accounts`, `categories`, `budgets`, `users` e `goals`.
