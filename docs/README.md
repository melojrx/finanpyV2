# Documentação do FinanPy

Esta pasta é a fonte oficial de documentação do projeto. Os documentos devem
descrever o que existe no código atual. Recursos planejados ficam em
`backlog.md`.

## Guias Atuais

- [Setup local](./setup-guide.md)
- [Arquitetura](./architecture.md)
- [Configuração](./configuration.md)
- [Deploy em VPS Ubuntu](./deployment.md)
- [Estrutura do banco](./database-structure.md)
- [Backlog futuro](./backlog.md)
- [Plano vivo de produção](./tasks.md)
- [Padrões de código](./coding-standards.md)
- [Frontend guidelines](./frontend-guidelines.md)
- [Static e media](./static-media-configuration.md)
- [TailwindCSS](./tailwindcss-setup.md)
- [Troubleshooting](./troubleshooting.md)

## Estado Atual do Produto

O FinanPy é uma aplicação Django para gestão financeira pessoal. Hoje o sistema
conta com:

- Autenticação com usuário customizado baseado em email.
- Perfil de usuário criado automaticamente.
- CRUD de contas financeiras.
- CRUD de categorias com hierarquia.
- CRUD de transações com receitas, despesas e recorrência marcada.
- Atualização automática de saldo por signals de transação.
- Orçamentos por categoria de despesa com cálculo de valor gasto e alertas.
- Metas financeiras com histórico de aportes.
- Perfil com telefone, data de nascimento, bio e avatar.
- Dashboard e templates server-rendered com Django Templates e TailwindCSS CDN.
- API REST autenticada por token para contas, categorias, transações e resumos.

## Stack Atual

- Python e Django.
- SQLite para desenvolvimento local.
- PostgreSQL para produção via Docker Compose.
- Gunicorn como servidor WSGI em produção.
- Nginx como proxy reverso e servidor de static/media.
- TailwindCSS via CDN.
- Django REST Framework para a API atual.

## Fora do Escopo Atual

Os itens abaixo são backlog, não funcionalidades atuais:

- Redis, Celery, Sentry ou S3.
- Upload de comprovantes de transação.
- Preferências avançadas no perfil.
- API REST para orçamentos, metas e demais recursos não expostos hoje.
- Build local de TailwindCSS.

Consulte [backlog.md](./backlog.md) para detalhes.
