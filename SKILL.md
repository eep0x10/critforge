---
name: meshy-miniaturas
description: CritForge — criar miniaturas de RPG e boardgame com referências revisadas, geração 3D no Meshy e entrega de STL corrigido, dimensionado e validado. Use para personagens e monstros; não inclui fatiamento.
---

# CritForge · Miniaturas: imagem → Meshy → STL revisado

Nome público: **CritForge**. Identificador técnico: `meshy-miniaturas`.

## Padrões

- Modelo de execução preferido: `gpt-5.6-luna`, esforço `medium`. Usar scripts para operações determinísticas e carregar apenas a referência necessária. Não trocar automaticamente para modelo maior. A skill não altera o modelo da conversa: no desktop selecionar esse modelo; na CLI usar `codex --model gpt-5.6-luna --config model_reasoning_effort='"medium"'`. Uma preferência textual não comprova que o host aplicou o modelo.

- Personagem sem base ou terreno integrado, dimensionado para uma base separada de 32 mm.
- Monstros usam múltiplos de células de 32 mm, como 2×2 ou 4×2.
- Personagem humanoide comum: alvo de 38 mm de altura e máximo de 45 mm. Para monstros ou escala explicitamente diferente, registrar limites próprios com `workflow.py limits`.
- Entrega final: STL corrigido e evidências. Orientação, Hollow, Drill, suportes, layout e fatiamento pertencem ao usuário.
- Nunca iniciar uma impressão física.

## Fluxo

1. **Retomar com estado:** executar `scripts/workflow.py status PROJETO`. Projetos privados ficam fora da skill e do repositório.
2. **Criar referências:** ler [referência visual](references/images.md). Gerar frente, verso e detalhe do rosto consistentes, sem base. Revisar anatomia, pose, mãos, arma, capa, acessórios, espessuras e enquadramento. Corrigir falhas antes de apresentar.
3. **Aprovar imagens:** usar enquete/popup clicável quando disponível. Registrar os arquivos aprovados com `workflow.py approve-images`; a aprovação fica vinculada aos hashes.
4. **Gerar no Meshy:** ler [API e comandos](references/commands.md). O padrão é `meshy.py submit PROJETO --mode image-4k`: Meshy 7.1, geometria 4K, vista frontal como entrada e verso/rosto como referências de QA. A API Multi-Image aceita no máximo geometria 2K; use `--mode multi-image-2k` apenas quando consistência entre vistas for mais importante que 4K. A chave vem somente de `MESHY_API_KEY`.
5. **Revisar antes de aceitar:** baixar e renderizar o STL real. Comparar frente, costas, laterais, rosto, mãos, arma, capa e acessórios com todas as referências. Procurar peças fundidas, acessórios inventados, colisões, duplicações, membros errados, detalhes frágeis e mudança indevida do rosto. Um STL fechado pode continuar artisticamente errado.
6. **Regenerar quando bugado:** se houver erro artístico ou estrutural relevante, rejeitar a tentativa. Corrigir a referência que causou ambiguidade quando necessário e criar um projeto de revisão separado. No máximo duas novas gerações por conjunto aprovado sem voltar ao usuário; nunca repetir um POST incerto.
7. **Corrigir e dimensionar:** preservar o original. Aplicar a menor correção que resolva o defeito, remover base/terreno quando solicitado e comparar antes/depois. Escalar em Z para o alvo; `mesh.py scale` assenta o modelo em Z=0. Inspecionar o final com `--units mm --intersections --base-mm 32`.
8. **Aceitar o STL final:** só registrar `final-stl` quando a altura estiver em milímetros, não exceder 45 mm, a silhueta couber na base planejada e as revisões visual e de malha tiverem evidência atual. `workflow.py report` deve retornar `delivery_ready=true`.

## Critérios de rejeição

Regerar ou reparar antes da entrega quando qualquer item for relevante:

- rosto ou identidade divergente das referências;
- arma, roupa, cauda, asa ou ornamento fundido ao corpo de forma não intencional;
- membro extra, mão deformada, peça duplicada ou acessório inventado;
- componente solto sem função, malha aberta, normais incoerentes ou auto-interseções importantes;
- base integrada quando o pedido exige base separada;
- escala sem unidade confirmada, altura final acima do limite ou encaixe incompatível com a base.

Detalhes e ferramentas: [revisão de malha](references/mesh.md). Use `preview.py` para vistas reais; imagens geradas por IA não comprovam o STL.

## Segurança e publicação

Não gravar chave, URL assinada, resposta bruta, imagem do personagem ou modelo 3D no repositório público. Uma submissão incerta bloqueia novo POST até recuperar a tarefa existente. Publicar somente arquivos do manifesto após `scripts/public_audit.py` e revisão da identidade dos commits.
