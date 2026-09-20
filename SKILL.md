---
name: meshy-miniaturas
description: CritForge — criar miniaturas de RPG e boardgame com imagens revisadas, Meshy, inspeção de STL e fatiamento opcional no CHITUBOX. Use para esse fluxo de miniaturas em resina, não para impressão FDM genérica.
---

# CritForge · Miniaturas: imagem → Meshy → STL → fatiamento opcional

Nome público: **CritForge**. Identificador técnico e invocação: `meshy-miniaturas`. Para apresentação e instalação, ler [README.md](README.md); este arquivo concentra a operação do agente.

## Operação compacta

Use `scripts/workflow.py status PROJETO` primeiro em retomadas. Ele indica a próxima etapa e evita reler todo o histórico. Execute scripts pelo Python disponível; caminhos dos comandos são relativos a esta skill. Logs, imagens, respostas e modelos ficam no projeto privado, fora da skill/repositório.

Padrões configuráveis: personagem sem base/terreno; base separada de 32 mm, não altura de 32 mm. Monstros usam múltiplos de 32 mm por célula. CHITUBOX, LD-006 e Standard V2 cinza são o perfil inicial de referência, não uma calibração garantida. Nunca iniciar impressão física.

## Fluxo

1. **Inicializar:** `python scripts/workflow.py init PROJETO`. Toda pergunta, escolha e aprovação usa enquete/popup clicável quando essa função estiver disponível; não substituir por opções apenas em texto. Se o ambiente realmente não oferecer popup, explicar isso brevemente e fazer uma única pergunta direta. Registrar decisões já explícitas, sem perguntar novamente.
2. **Imagens:** ler [referência visual](references/images.md); gerar frente, verso e rosto com a ferramenta de imagens disponível. Revisar anatomia, consistência e robustez; corrigir falhas antes de apresentar. Após aprovação explícita, `workflow.py approve-images PROJETO --front F --back V --face R`. A aprovação é vinculada aos hashes das imagens, não apenas aos nomes.
3. **Meshy:** ler [API e comandos](references/commands.md). `meshy.py submit PROJETO` usa apenas `MESHY_API_KEY` do ambiente. Nunca inserir chave em argumento, script, relatório ou chat. Uma submissão incerta bloqueia novo POST; recuperar a tarefa existente. `meshy.py watch PROJETO --seconds 45` consulta com intervalo limitado e resumo compacto; repetir a mesma tarefa em retomadas. `meshy.py download PROJETO` preserva originais.
4. **Escolha ao receber STL:** mostrar o link e perguntar: **“Quer que eu faça a preparação e o fatiamento completos ou prefere fatiar manualmente para economizar tokens?”** Opções: “Vou fatiar manualmente” / “Fazer preparação e fatiamento completos”. Registrar com `workflow.py slicing PROJETO manual|full`. A aprovação das imagens não autoriza automaticamente o fatiamento. Aguardar escolha; respeitar decisão explícita já dada para esse modelo.
5. **Malha:** executar `mesh.py inspect ARQUIVO --out RELATORIO.json`; adicionar `--intersections` quando a dependência estiver disponível. Comparar vistas reais com as referências, especialmente face, cauda, mãos e asas. Malha fechada não comprova fidelidade ou imprimibilidade. Não descartar componentes por tamanho sem inspecioná-los. Reparo, corte da base e escala já solicitados permanecem no escopo mesmo no modo manual. Ler [revisão de malha](references/mesh.md) quando necessário. Mudança artística relevante exige correção ou aprovação específica.
6. **Manual:** entregar STL e relatório com limites reais. Não abrir fatiador nem produzir CTB. **Completo:** seguir [CHITUBOX](references/chitubox.md): orientar → avaliar Hollow → avaliar Drill → Auto Support Light → Auto Layout → fatiar → revisar → exportar e reabrir. Nunca pular silenciosamente Hollow/Drill.
7. **Entrega:** registrar `final-stl`; no completo, também `final-project` (CTP/CHITUBOX) e `final-slice` (CTB). Registrar antes dos checks: visual/malha vinculam o STL final; slice-review/reopen vinculam os três finais. `workflow.py report PROJETO` exige esses arquivos e evidências atuais. Só entregar como revisado quando `delivery_ready=true`; isso não certifica impressão física. Ver [comandos](references/commands.md).

## Economia sem perder controle

- `workflow.py doctor` confere dependências sem exibir segredos; instalar apenas o necessário.
- `mesh.py inspect` reutiliza relatório apenas para o mesmo hash, versão do verificador e opções. Saída curta; detalhes no JSON.
- `preview.py MODELO --out-dir VISTAS` renderiza seis vistas reais; confirmar e ajustar o recorte do rosto com `--face X Y Z WIDTH`. Após reparos, usar `mesh.py compare` e `preview.py CORRIGIDO --reference ANTES --out-dir COMPARACAO`. Vistas compartilham câmeras; não aceitar reparo apenas porque desapareceu um defeito.
- Tarefas FAILED/EXPIRED/CANCELED exigem diagnóstico e autorização antes de nova geração; não repetir consultas sem fim. Estado desconhecido exige inspeção.
- Preparar artefatos e usar scripts para arquivos, métricas e API. Interface do CHITUBOX exige observação e verificação; não automatizar cliques cegos nem usar coordenadas fixas.
- Se a interface ignorar duas tentativas de texto, usar controle acessível ou salvar com nome padrão exclusivo e organizar depois. Não repetir indefinidamente.
- Publicação usa somente os arquivos do manifesto e `scripts/public_audit.py`; projetos, perfis exportados, histórico de conversas e segredos nunca pertencem ao pacote público.
