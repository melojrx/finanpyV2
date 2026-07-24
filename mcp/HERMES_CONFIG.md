# Hermes Configuration for MCP FinanPy

## Neo (principal)

Adicionar ao `config.yaml` do Neo principal:

```yaml
mcp_servers:
  finanpy:
    command: /opt/finanpy-mcp/.venv/bin/python
    args:
      - /opt/finanpy-mcp/run_mcp.py
    timeout: 60
    connect_timeout: 30
    env:
      FINANPY_API_BASE_URL: http://127.0.0.1:8001/api/v1/
      FINANPY_API_TOKEN: <cole-aqui-o-token-do-user-hermes>
    enabled: true
```

## agente-braba

**NÃO** adicionar `mcp_servers.finanpy` ao profile do agente-braba.
Este profile é usado para outras tarefas (Brabus store, etc.) e não deve
acessar o FinanPy. A política de `mcp_exclude` no perfil garante isolamento.

## Setup do user hermes (uma única vez)

```bash
# Na VPS, dentro do container FinanPy:
bash mcp/scripts/setup_hermes_user.sh
# Copiar o token exibido para FINANPY_API_TOKEN no config.yaml acima.
```

## Rotacionamento do token

Para rotacionar o DRF Token do user hermes:

```bash
# 1. Revogar token atual
docker exec -it finanpy-web-1 python manage.py shell -c "
from rest_framework.authtoken.models import Token
from django.contrib.auth import get_user_model
U = get_user_model()
u = U.objects.get(username='hermes')
Token.objects.filter(user=u).delete()
print('Token revogado.')
"

# 2. Gerar novo token
bash mcp/scripts/setup_hermes_user.sh

# 3. Atualizar FINANPY_API_TOKEN no config.yaml do Hermes

# 4. Reiniciar Hermes
ssh root@38.52.128.62 'systemctl restart hermes-gateway'
```

## Deploy manual

```bash
# A partir do repositório local:
bash mcp/scripts/deploy_vps.sh
```

O script:
1. Roda os testes locais
2. Faz rsync para /opt/finanpy-mcp/ na VPS
3. Reinstala as deps na venv
4. Reinicia o hermes-gateway
5. Roda o smoke test