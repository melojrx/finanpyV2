# Setup Local

Este guia prepara o ambiente de desenvolvimento local do FinanPy.

## Pré-requisitos

- Python compatível com Django 5.2.
- Git.
- SQLite, já usado pelo Django localmente.

O ambiente atual do projeto usa um diretório `venv/`. Se preferir `.venv/`,
ajuste os comandos localmente.

## Instalação

Clone o repositório e entre na pasta:

```bash
git clone <url-do-repositorio>
cd finanpy_v2
```

Crie e ative o ambiente virtual:

```bash
python -m venv venv
source venv/bin/activate
```

Instale dependências:

```bash
pip install -r requirements.txt
```

Aplique migrações:

```bash
python manage.py migrate
```

Crie um superusuário:

```bash
python manage.py createsuperuser
```

Execute o servidor:

```bash
python manage.py runserver
```

Acesse:

```text
http://127.0.0.1:8000/
```

## Comandos de Desenvolvimento

Verificar configuração:

```bash
python manage.py check
```

Verificar migrações pendentes:

```bash
python manage.py makemigrations --check --dry-run
```

Executar testes:

```bash
python manage.py test
```

Popular categorias padrão:

```bash
python manage.py seed_categories
```

Coletar static localmente, quando necessário:

```bash
python manage.py collectstatic
```

## Estrutura Principal

```text
finanpy_v2/
├── accounts/       # Contas financeiras
├── budgets/        # Orçamentos
├── categories/     # Categorias
├── core/           # Settings e URLs do projeto
├── docs/           # Documentação oficial
├── goals/          # Metas financeiras e aportes
├── profiles/       # Perfis de usuário
├── static/         # CSS, JS, imagens e fontes
├── templates/      # Templates Django
├── transactions/   # Transações financeiras
├── users/          # Usuário customizado e autenticação
├── Dockerfile
├── docker-compose.prod.yml
├── manage.py
└── requirements.txt
```

## Observações

- O desenvolvimento local usa SQLite.
- Produção usa PostgreSQL via Docker Compose.
- TailwindCSS está via CDN no template base.
- CSS estático deve ser CSS de navegador; não há build Tailwind local hoje.
- Recursos não implementados ficam documentados em `docs/backlog.md`.
