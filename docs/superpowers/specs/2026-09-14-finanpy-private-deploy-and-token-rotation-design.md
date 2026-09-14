# Especificação: deploy privado e rotação posterior do Tunnel FinanPy

**Data:** 14/09/2026  
**Status:** aprovado para planejamento  
**Escopo:** subir e validar o FinanPy no Homelab com o Tunnel atual, publicar
`finanpy.com.br` em gate separado e rotacionar o token somente após a validação
pública do MVP.

## Decisão

O token atual do Tunnel `finanpy-edge` permanecerá em uso durante o deploy
privado, o corte público e a validação inicial. Esta é uma aceitação de risco
temporária para o MVP de acesso restrito do proprietário. Como o token foi
fornecido em conversa, ele será substituído por um token novo após a validação
de `finanpy.com.br`.

O deploy privado não altera DNS nem publica o web. Ele instala a configuração
não secreta no Homelab, restaura os dados finais no volume definitivo e executa
PostgreSQL, migration one-shot e web no Swarm. A validação usa health interno,
Traefik na rede `edge` e login autenticado não destrutivo.

## Estado confirmado

| Recurso | Estado |
|---|---|
| Tunnel | `finanpy-edge`, conectado por duas sessões QUIC |
| Conector | `finanpy-edge_cloudflared`, uma réplica no Homelab |
| Secret atual | `finanpy_cloudflared_tunnel_token`, sem valor registrado |
| Imagem candidata | GHCR por digest, já staged no Homelab |
| Dados | dump e mídia restaurados em ensaio isolado com inventário compatível |
| App Swarm | ainda não implantado |
| DNS/corte | não autorizado nesta etapa |

## Sequência de gates

1. **Deploy privado:** instalar `/srv/finanpy/finanpy.env` com valores não
   secretos, restaurar dados finais no volume definitivo e implantar o stack
   por digest. O serviço web é alcançado somente pela rede `edge`/Traefik.
2. **Validação privada:** confirmar PostgreSQL, migration, liveness, readiness,
   login e fluxo autenticado não destrutivo. Falha mantém a VPS como origem e
   impede o corte.
3. **Corte público:** somente com nova autorização, configurar os hostnames do
   Tunnel, publicar `finanpy.com.br` e `www.finanpy.com.br`, validar HTTPS,
   sessão, CSRF e retorno à VPS.
4. **Rotação pós-publicação:** gerar token novo na Cloudflare, criar secret
   Swarm versionado, atualizar o conector para a nova referência, confirmar
   conexão saudável, revogar o token anterior na Cloudflare e remover o secret
   antigo após a confirmação.

## Rotação do token

Docker Swarm Secrets são imutáveis. A rotação usará nomes versionados, por
exemplo `finanpy_cloudflared_tunnel_token_20260914`, e a referência do secret
será parametrizada pelo release. Durante a troca, o serviço recebe o secret
novo, reinicia uma réplica e precisa registrar pelo menos uma conexão antes da
revogação do token anterior. Não haverá valor de token em Git, vault, logs ou
respostas.

## Critérios de aceite

- Deploy privado não cria ou altera DNS.
- Web, banco e migration não expõem portas do host.
- Dados finais restaurados conferem com inventário e mídia de origem.
- Health interno e login autenticado funcionam antes do corte público.
- Após corte autorizado, a rotação troca token sem perda de conectividade do
  Tunnel e o token anterior é revogado.
- A VPS permanece disponível como contingência até aprovação explícita de
  desativação.

## Fora de escopo

- Rotacionar o token atual antes do deploy privado ou do corte público.
- Publicar o domínio, alterar DNS ou desativar a VPS nesta etapa.
- Registrar credenciais, dados financeiros ou dados pessoais na documentação.
