# Hermes Configuration for MCP FinanPy

## Neo (principal)

Adicionar ao `config.yaml` do Neo principal:

```yaml
mcp_servers:
  finanpy:
    command: /opt/finanpy-mcp/.venv/bin/python
    args: [/opt/finanpy-mcp/run_mcp.py]
    env:
      FINANFY_TOKEN: <your_token_here>
      FINANFY_USE_SQLITE: false
      FINANFY_DB_HOST: 127.0.0.1
      FINANFY_DB_PORT: 5432
```

## agente-braba

**NAO** adicionar `mcp_servers.finanpy` ao profile do agente-braba.
Este profile eh usado para outras tarefas e nao deve acessar o FinanPy.

## Configuracao manual (se nao usar GitHub Actions)

1. Copiar arquivos para VPS: `rsync -avz mcp/ root@vps:/opt/finanpy-mcp/`
2. Criar venv: `cd /opt/finanpy-mcp && python3.12 -m venv .venv`
3. Instalar: `.venv/bin/pip install -e .`
4. Editar config: `nano /home/hermes-admin/.hermes/config.yaml`
5. Reiniciar: `systemctl restart hermes-gateway`