# FinanPy — entrega de mídia pública no Homelab

**Data:** 2026-09-14
**Status:** aprovado para implementação

## Contexto

O avatar cadastrado do único perfil existente está íntegro no banco e no volume
persistente `finanpy_media`, em `avatars/2/perfil.png`. Contudo, a URL pública
`/media/avatars/2/perfil.png` retorna 404 no domínio `finanpy.com.br`.

O problema não é o Tunnel, Traefik, banco ou volume. Em `core/urls.py`, a
aplicação chama `django.conf.urls.static.static()` quando
`SERVE_MEDIA_FILES=true`. O helper do Django retorna uma lista vazia quando
`DEBUG=False`, portanto nenhuma rota de mídia é registrada na produção.

O padrão atual de UrbanLive possui a mesma limitação. Ele é uma boa referência
para a borda compartilhada e para WhiteNoise nos estáticos, mas não deve ser
copiado como solução de mídia em produção.

## Decisão

Manter a separação de responsabilidades abaixo:

- WhiteNoise continua entregando exclusivamente `/static/` a partir da imagem
  imutável.
- Uma view Django explícita atende `/media/<path>` a partir de `MEDIA_ROOT`.
- A view só entrega mídia quando `DEBUG=True` ou `SERVE_MEDIA_FILES=true`; caso
  contrário responde 404.
- O volume Swarm `finanpy_media` segue como fonte persistente de uploads. Não
  haverá migração de dados, mudança de banco, alteração de Tunnel ou abertura
  de portas.

O uso de `django.views.static.serve` mantém a normalização segura de caminhos
feita pelo Django. Os arquivos de mídia permanecem acessíveis por URL direta,
como já pressuposto pelo campo de avatar renderizado na navegação autenticada.

## Alternativas rejeitadas

1. **Reutilizar `static()` com `SERVE_MEDIA_FILES`:** não funciona com
   `DEBUG=False` por contrato do Django.
2. **Adicionar Nginx para `/media/`:** cria uma camada operacional adicional e
   diverge da stack atual sem necessidade para o MVP.
3. **Migrar uploads para object storage:** é uma evolução válida, mas expande
   custo, credenciais e escopo além do reparo.

## Critérios de aceite

- Com produção simulada (`DEBUG=False`) e `SERVE_MEDIA_FILES=true`, um arquivo
  dentro de `MEDIA_ROOT` responde 200 pelo endpoint `/media/`.
- Com `SERVE_MEDIA_FILES=false`, o mesmo endpoint responde 404.
- O comportamento de desenvolvimento para estáticos e hot reload não muda.
- O deploy automatizado por push em `main` permanece íntegro.
- Após a promoção, a URL pública existente do avatar responde 200 com conteúdo
  de imagem, sem alterar o volume ou o banco.

## Limites e continuidade

Este reparo não autoriza desativar a VPS, rotacionar o token do Cloudflare ou
alterar DNS. Essas ações continuam condicionadas à validação funcional completa
da aplicação no domínio publicado.
