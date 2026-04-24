# Troubleshooting - Finanpy

Este documento contém soluções para problemas comuns que podem ocorrer durante o desenvolvimento, instalação e uso do Finanpy.

## 🚨 Problemas de Instalação

### Python e Dependências

#### Erro: "python: command not found"
```bash
# Problema: Python não instalado ou não no PATH

# Linux/Ubuntu
sudo apt update
sudo apt install python3 python3-pip

# macOS
brew install python3

# Windows
# Baixar de https://python.org e marcar "Add to PATH"

# Verificar instalação
python3 --version
```

#### Erro: "pip: command not found"
```bash
# Linux/Ubuntu
sudo apt install python3-pip

# macOS
curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
python3 get-pip.py

# Windows
python -m ensurepip --upgrade
```

#### Erro: "Permission denied" ao instalar pacotes
```bash
# NÃO use sudo com pip - use virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# ou
venv\Scripts\activate  # Windows

pip install -r requirements.txt
```

#### Erro: "No module named 'django'"
```bash
# Verificar se está no virtual environment
which python  # Deve mostrar caminho do venv

# Se não estiver ativado
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt

# Verificar instalação
python -c "import django; print(django.get_version())"
```

### Virtual Environment

#### Erro ao criar virtual environment
```bash
# Se python3-venv não estiver instalado (Linux)
sudo apt install python3-venv

# Criar novamente
python3 -m venv venv

# Ativar
source venv/bin/activate
```

#### Virtual environment não ativa automaticamente
```bash
# Adicionar ao .bashrc ou .zshrc (opcional)
echo "source ~/projetos/finanpy_v2/venv/bin/activate" >> ~/.bashrc

# Ou usar script personalizado
cat > activate_finanpy.sh << 'EOF'
#!/bin/bash
cd ~/projetos/finanpy_v2
source venv/bin/activate
echo "Finanpy environment activated!"
EOF

chmod +x activate_finanpy.sh
```

## 🗄️ Problemas de Banco de Dados

### Migrações

#### Erro: "No migrations to apply"
```bash
# Forçar criação de migrações
python manage.py makemigrations --empty accounts
python manage.py makemigrations --empty categories
python manage.py makemigrations --empty transactions
python manage.py makemigrations --empty budgets
python manage.py makemigrations --empty profiles

# Aplicar
python manage.py migrate
```

#### Erro: "Table already exists"
```bash
# Fazer fake initial migration
python manage.py migrate --fake-initial

# Ou resetar completamente (CUIDADO: perde dados!)
rm db.sqlite3
rm */migrations/00*.py  # Manter apenas __init__.py
python manage.py makemigrations
python manage.py migrate
```

#### Erro: "Foreign key constraint failed"
```bash
# Ver dependências das migrações
python manage.py showmigrations

# Aplicar em ordem específica
python manage.py migrate users
python manage.py migrate profiles
python manage.py migrate accounts
python manage.py migrate categories
python manage.py migrate transactions
python manage.py migrate budgets
```

#### Erro de integridade referencial
```bash
# Verificar estado do banco
python manage.py shell

>>> from django.db import connection
>>> cursor = connection.cursor()
>>> cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
>>> print(cursor.fetchall())

# Se necessário, dropar constraints temporariamente
>>> cursor.execute("PRAGMA foreign_keys=OFF;")
# ... fazer alterações necessárias ...
>>> cursor.execute("PRAGMA foreign_keys=ON;")
```

### Performance do Banco

#### Queries lentas
```bash
# Habilitar debug no settings.py (apenas desenvolvimento)
DEBUG = True
LOGGING = {
    'loggers': {
        'django.db.backends': {
            'level': 'DEBUG',
            'handlers': ['console'],
        }
    }
}

# Ou usar Django Debug Toolbar
pip install django-debug-toolbar

# Adicionar ao settings.py
INSTALLED_APPS += ['debug_toolbar']
MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
INTERNAL_IPS = ['127.0.0.1']
```

## 🌐 Problemas de Servidor

### Django Development Server

#### Erro: "Port already in use"
```bash
# Encontrar processo na porta 8000
sudo lsof -t -i tcp:8000

# Matar processo
sudo lsof -t -i tcp:8000 | xargs kill -9

# Usar porta diferente
python manage.py runserver 8001
```

#### Erro: "DisallowedHost"
```bash
# Adicionar host ao ALLOWED_HOSTS no settings.py
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0', 'your-domain.com']

# Para desenvolvimento, permitir todos (INSEGURO!)
ALLOWED_HOSTS = ['*']  # Apenas para desenvolvimento!
```

#### Servidor não responde
```bash
# Verificar se está rodando
ps aux | grep manage.py

# Verificar logs
python manage.py runserver --verbosity=2

# Testar conectividade
curl http://localhost:8000/
```

### SSL/HTTPS

#### Certificado SSL inválido
```bash
# Para desenvolvimento local
python manage.py runserver --insecure

# Gerar certificado self-signed para testes
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes
```

## 💻 Problemas Frontend

### TailwindCSS

#### Estilos não carregam
```html
<!-- Verificar se CDN está correto -->
<script src="https://cdn.tailwindcss.com"></script>

<!-- Verificar se não há bloqueador de ads -->
<!-- Testar URL diretamente no navegador -->
```

#### Classes customizadas não funcionam
```css
/* Verificar ordem dos arquivos CSS */
<link href="https://cdn.tailwindcss.com/..." rel="stylesheet">
<link href="{% static 'css/base.css' %}" rel="stylesheet">

/* Usar !important se necessário (último recurso) */
.custom-class {
    background-color: #1f2937 !important;
}
```

### JavaScript

#### Erros de JavaScript no console
```javascript
// Verificar se jQuery/Alpine.js está carregado
console.log(typeof $); // jQuery
console.log(typeof Alpine); // Alpine.js

// Debug de eventos
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded');
    // seu código aqui
});

// Verificar CSP
// Se houver erro de Content Security Policy, adicionar no settings.py:
CSP_SCRIPT_SRC = ["'self'", "'unsafe-inline'", "https://cdn.tailwindcss.com"]
```

#### AJAX não funciona
```javascript
// Verificar CSRF token
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Usar em requisições
fetch('/api/endpoint/', {
    method: 'POST',
    headers: {
        'X-CSRFToken': getCookie('csrftoken'),
        'Content-Type': 'application/json',
    },
    body: JSON.stringify(data)
})
```

## 🔐 Problemas de Autenticação

### Login não funciona

#### Erro: "CSRF token missing"
```html
<!-- Verificar se tem csrf_token no form -->
<form method="post">
    {% csrf_token %}
    <!-- campos do form -->
</form>

<!-- Verificar middleware -->
# settings.py
MIDDLEWARE = [
    'django.middleware.csrf.CsrfViewMiddleware',  # Deve estar presente
    # outros middlewares...
]
```

#### Erro: "User matching query does not exist"
```python
# Verificar se usuário existe
python manage.py shell

>>> from django.contrib.auth import get_user_model
>>> User = get_user_model()
>>> User.objects.all()

# Criar superusuário se necessário
python manage.py createsuperuser
```

#### Sessão expira muito rápido
```python
# settings.py - Aumentar tempo de sessão
SESSION_COOKIE_AGE = 86400  # 24 horas em segundos
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_SAVE_EVERY_REQUEST = True
```

### Permissions

#### Erro: "Permission denied"
```python
# Verificar permissions do usuário
python manage.py shell

>>> from django.contrib.auth import get_user_model
>>> User = get_user_model()
>>> user = User.objects.get(username='seu_usuario')
>>> user.is_active
True
>>> user.is_staff
True  # Para acessar admin
```

## 📧 Problemas de Email

### Email não envia

#### Configuração SMTP
```python
# settings.py - Testar configurações
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'  # Para debug

# Para Gmail
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'seu_email@gmail.com'
EMAIL_HOST_PASSWORD = 'sua_senha_de_app'  # Não a senha normal!
```

#### Testar envio de email
```python
python manage.py shell

>>> from django.core.mail import send_mail
>>> send_mail(
...     'Teste',
...     'Mensagem de teste',
...     'from@example.com',
...     ['to@example.com'],
... )
```

## 🗂️ Problemas de Arquivos Estáticos

### CSS/JS não carregam

#### Configuração de static files
```python
# settings.py
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Coletar arquivos estáticos
python manage.py collectstatic --noinput
```

#### Permissões de arquivo
```bash
# Linux/macOS - Verificar permissões
ls -la static/
chmod -R 755 static/
chmod -R 644 static/css/*
chmod -R 644 static/js/*
```

### Upload de arquivos

#### Erro: "File upload permission denied"
```python
# settings.py
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Criar diretório
mkdir -p media/uploads

# Permissões (Linux/macOS)
chmod -R 755 media/
```

#### Arquivo muito grande
```python
# settings.py - Aumentar limite
FILE_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10MB
```

## ⚡ Problemas de Performance

### Página carrega lenta

#### Debug de queries N+1
```python
# Instalar django-debug-toolbar
pip install django-debug-toolbar

# Adicionar ao settings.py
if DEBUG:
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
    INTERNAL_IPS = ['127.0.0.1']

# Otimizar queries
# Em vez de:
for transaction in transactions:
    print(transaction.account.name)  # Query para cada iteração

# Use:
transactions = Transaction.objects.select_related('account', 'category')
```

#### Memory usage alto
```bash
# Monitorar uso de memória
pip install memory_profiler

# Adicionar ao código
@profile
def my_function():
    # código aqui
    pass

# Executar
python -m memory_profiler manage.py runserver
```

## 🧪 Problemas de Testes

### Testes não executam

#### Banco de dados de teste
```bash
# Erro de permissions no SQLite
chmod 664 db.sqlite3
chmod 775 .  # diretório do projeto

# Usar banco em memória para testes
# settings.py ou settings/test.py
if 'test' in sys.argv:
    DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:'
    }
```

#### Fixtures não carregam
```bash
# Verificar formato do arquivo
python manage.py dumpdata --indent=2 app.Model > fixtures/test_data.json

# Carregar fixtures
python manage.py loaddata fixtures/test_data.json

# Em testes
class MyTestCase(TestCase):
    fixtures = ['test_data.json']
```

## 🔧 Ferramentas de Debug

### Django Shell
```bash
# O projeto oficial usa apenas o shell padrão do Django.
python manage.py shell

>>> from django.contrib.auth import get_user_model
>>> User = get_user_model()
>>> User.objects.all()
```

### Logging personalizado
```python
# settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {name} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'debug.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'finanpy': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

# Uso no código
import logging
logger = logging.getLogger('finanpy')

def my_view(request):
    logger.debug(f"Processing request for user {request.user}")
    # resto do código...
```

## 🆘 Comandos de Emergência

### Reset completo do ambiente
```bash
#!/bin/bash
# reset_environment.sh

echo "🚨 ATENÇÃO: Isso vai apagar todos os dados!"
read -p "Tem certeza? (y/N): " confirm

if [[ $confirm == [yY] ]]; then
    echo "Fazendo backup..."
    cp db.sqlite3 db_backup_$(date +%Y%m%d_%H%M%S).sqlite3 2>/dev/null || true
    
    echo "Removendo banco de dados..."
    rm -f db.sqlite3
    
    echo "Removendo migrações..."
    find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
    find . -path "*/migrations/*.pyc" -delete
    
    echo "Removendo cache Python..."
    find . -name "*.pyc" -delete
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    
    echo "Criando novas migrações..."
    python manage.py makemigrations
    
    echo "Aplicando migrações..."
    python manage.py migrate
    
    echo "Criando superusuário..."
    python manage.py createsuperuser --noinput --username admin --email admin@example.com || true
    
    echo "✅ Ambiente resetado com sucesso!"
else
    echo "Operação cancelada."
fi
```

### Script de verificação de saúde
```bash
#!/bin/bash
# health_check.sh

echo "🔍 Verificando saúde do sistema Finanpy..."

# Verificar Python
echo "Python:" $(python --version 2>&1)

# Verificar virtual environment
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo "✅ Virtual environment ativo: $VIRTUAL_ENV"
else
    echo "❌ Virtual environment não ativo"
fi

# Verificar Django
python -c "import django; print('✅ Django:', django.get_version())" 2>/dev/null || echo "❌ Django não instalado"

# Verificar banco de dados
python manage.py check --database default && echo "✅ Banco conectado" || echo "❌ Problema no banco"

# Verificar migrações
python manage.py showmigrations --plan | grep -q "\[ \]" && echo "❌ Migrações pendentes" || echo "✅ Migrações aplicadas"

# Verificar arquivos estáticos
[[ -d "static" ]] && echo "✅ Diretório static existe" || echo "❌ Diretório static não encontrado"

# Verificar servidor
timeout 5s python manage.py runserver --noreload 2>/dev/null && echo "✅ Servidor inicia OK" || echo "❌ Problema no servidor"

echo "✅ Verificação concluída!"
```

## 📚 Recursos de Ajuda

### Documentação oficial
- [Django Documentation](https://docs.djangoproject.com/)
- [TailwindCSS Documentation](https://tailwindcss.com/docs)
- [Python Documentation](https://docs.python.org/3/)

### Comunidades
- [Django Forum](https://forum.djangoproject.com/)
- [Stack Overflow - Django](https://stackoverflow.com/questions/tagged/django)
- [Reddit - r/django](https://reddit.com/r/django)

### Ferramentas úteis
- [Django Debug Toolbar](https://django-debug-toolbar.readthedocs.io/)
- [Django Extensions](https://django-extensions.readthedocs.io/)
- [SQLite Browser](https://sqlitebrowser.org/)

---

Se nenhuma das soluções acima resolver seu problema:

1. ✅ Verifique os logs do Django em `debug.log`
2. ✅ Execute o script de verificação de saúde
3. ✅ Consulte a documentação oficial
4. ✅ Procure soluções nas comunidades
5. ✅ Como último recurso, use o reset completo do ambiente
