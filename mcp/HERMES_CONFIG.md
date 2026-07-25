# Hermes Configuration for MCP FinanPy

## Decisão de autenticação

O MCP usa o **token DRF do usuário pessoal** (`jrmeloafrf`), não de um
usuário dedicado. Motivo: o DRF filtra todos os dados por `request.user`
— um usuário separado (ex.: `hermes`) teria banco vazio e não enxergaria
contas, transações, metas etc. do usuário real.

> **Não usar** `setup_hermes_user.sh` para gerar o token. Usar o token
> do usuário pessoal conforme instruções abaixo.

## Neo (principal)

Bloco atual no `config.yaml` do Neo principal (`/home/hermes-admin/.hermes/config.yaml`):

```yaml
mcp_servers:
  finanpy:
    command: /opt/finanpy-mcp/.venv/bin/python
    args:
      - /opt/finanpy-mcp/run_mcp.py
    timeout: 60
    connect_timeout: 30
    env:
      FINANPY_API_BASE_URL: https://investiorion.com/api/v1/
      FINANPY_API_TOKEN: <token-do-usuario-jrmeloafrf>
    enabled: true
```

**Nota de topologia:** usar `https://investiorion.com/api/v1/` (via Nginx)
e não `http://127.0.0.1:8001/api/v1/` (loopback). O Django em produção tem
`SECURE_SSL_REDIRECT=True` — chamadas HTTP diretas ao container recebem
301 redirect para HTTPS sem servidor respondendo.

## agente-braba

**NÃO** adicionar `mcp_servers.finanpy` ao profile do agente-braba.
Este profile é usado para outras tarefas (Brabus store, etc.) e não deve
acessar o FinanPy.

## Obter/rotacionar o token do usuário pessoal

```bash
# Obter token existente (ou criar se não existir)
docker exec -it finanpy-web-1 python manage.py shell -c "
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
U = get_user_model()
u = U.objects.get(username='jrmeloafrf')
t, created = Token.objects.get_or_create(user=u)
print('Token:', t.key)
"

# Para rotacionar: deletar e recriar
docker exec -it finanpy-web-1 python manage.py shell -c "
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
U = get_user_model()
u = U.objects.get(username='jrmeloafrf')
Token.objects.filter(user=u).delete()
t = Token.objects.create(user=u)
print('Novo token:', t.key)
"

# Após rotacionar: atualizar FINANPY_API_TOKEN no config.yaml e reiniciar Hermes
systemctl restart hermes-webui
```

## Deploy manual

```bash
# A partir do repositório local:
bash mcp/scripts/deploy_vps.sh
```

O script:
1. Roda os testes locais
2. Faz rsync para /opt/finanpy-mcp/ na VPS (preserva .venv e .env)
3. Reinstala as deps na venv
4. Reinicia o hermes-webui
5. Roda o smoke test