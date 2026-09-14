# Plano de implementação — mídia pública do FinanPy

> **Para execução:** seguir as tarefas na ordem, em branch normal
> `codex/finanpy-public-media`, criada a partir de `main`; não usar worktree.

**Objetivo:** corrigir a entrega de uploads persistentes em `/media/` no
Homelab sem modificar a entrega de estáticos por WhiteNoise.

**Arquitetura:** WhiteNoise mantém `/static/`; uma view de mídia em `core`
valida o feature flag de entrega e delega a leitura segura ao `serve` do Django.
O roteamento explicitamente associa `MEDIA_URL` a essa view. A mídia continua
no volume Swarm existente.

**Stack:** Django 5.2, WhiteNoise, Docker/Swarm, Traefik e Cloudflare Tunnel.

---

### Tarefa 1 — Escrever testes de regressão da rota de mídia

**Arquivos:**

- Modificar: `core/tests.py`

**Passos:**

1. Criar uma classe de testes que use um `TemporaryDirectory` como `MEDIA_ROOT`.
2. Criar um PNG mínimo em `avatars/test/avatar.png`.
3. Verificar 200 e bytes esperados com `DEBUG=False` e
   `SERVE_MEDIA_FILES=True`.
4. Verificar 404 com `DEBUG=False` e `SERVE_MEDIA_FILES=False`.

**Verificação inicial esperada:** o teste de entrega habilitada falha antes da
implementação porque a rota não existe em produção.

### Tarefa 2 — Implementar entrega explícita de mídia

**Arquivos:**

- Criar: `core/media_views.py`
- Modificar: `core/urls.py`

**Passos:**

1. Implementar a view com o gate `DEBUG or SERVE_MEDIA_FILES`.
2. Retornar `Http404` quando a entrega estiver desabilitada.
3. Delegar o arquivo ao `django.views.static.serve` com `MEDIA_ROOT`.
4. Trocar o uso de `static(settings.MEDIA_URL, ...)` por uma rota explícita
   baseada em `MEDIA_URL`, preservando a rota de estáticos somente para dev.

**Verificação:**

```bash
python manage.py test core.tests
```

### Tarefa 3 — Atualizar os contratos operacionais

**Arquivos:**

- Modificar: `tests/scripts/test-finanpy-swarm-manifest.sh`
- Modificar: `docs/deployment.md`
- Modificar: `/home/jrmelo/Documentos/Obsidian Vault/02-Projetos/FinanPy/04-Migracao-VPS-para-Homelab.md`

**Passos:**

1. Fazer o teste de manifesto confirmar a rota explícita de mídia, em vez de
   apenas a presença do flag.
2. Documentar que `SERVE_MEDIA_FILES` habilita a view de mídia, e que
   `static()` não é usado para produção.
3. Registrar no vault o diagnóstico e o contrato corrigido, sem segredos.

**Verificação:**

```bash
sh tests/scripts/test-finanpy-swarm-manifest.sh
```

### Tarefa 4 — Validar e promover

**Passos:**

1. Executar testes Django focados e o teste do manifesto.
2. Executar a suíte de testes aplicável e o build de imagem.
3. Revisar o diff e commitar a alteração.
4. Integrar em `main` e fazer push para disparar o deploy automatizado.
5. Acompanhar o GitHub Actions até sucesso e validar o serviço no Homelab.
6. Fazer `GET` público com cache-control de revalidação para a URL real do
   avatar, esperando `200` e tipo de imagem.

**Critério de conclusão:** o avatar armazenado no volume atual aparece pela URL
de produção e todos os testes definidos acima passam.
