---
name: meshy-miniaturas
description: Criar miniaturas de RPG e boardgame com imagens revisadas, Meshy, inspeção de STL e fatiamento opcional no CHITUBOX. Use para esse fluxo de miniaturas em resina, não para impressão FDM genérica.
---

# Miniaturas: imagem → Meshy → STL → fatiamento opcional

## Operação compacta

Use `scripts/workflow.py status PROJETO` primeiro em retomadas. Ele indica a próxima etapa e evita reler todo o histórico. Execute scripts pelo Python disponível; caminhos dos comandos são relativos a esta skill. Logs, imagens, respostas e modelos ficam no projeto privado, fora da skill/repositório.

Padrões configuráveis: personagem sem base/terreno; base separada de 32 mm, não altura de 32 mm. Monstros usam múltiplos de 32 mm por célula. CHITUBOX, LD-006 e Standard V2 cinza são o perfil inicial de referência, não uma calibração garantida. Nunca iniciar impressão física.

## Fluxo

1. **Inicializar:** `python scripts/workflow.py init PROJETO`. Perguntas e aprovações por enquete clicável quando disponível. Registrar decisões já explícitas, sem perguntar novamente.
2. **Imagens:** ler [referência visual](references/images.md); gerar frente, verso e rosto com a ferramenta de imagens disponível. Revisar anatomia, consistência e robustez; corrigir falhas antes de apresentar. Após aprovação explícita, `workflow.py approve-images PROJETO --front F --back V --face R`. A aprovação é vinculada aos hashes das imagens, não apenas aos nomes.
3. **Meshy:** ler [API e comandos](references/commands.md). `meshy.py submit PROJETO` usa apenas `MESHY_API_KEY` do ambiente. Nunca inserir chave em argumento, script, relatório ou chat. Uma submissão incerta bloqueia novo POST; recuperar a tarefa existente. `meshy.py watch PROJETO --seconds 45` consulta com intervalo limitado e resumo compacto; repetir a mesma tarefa em retomadas. `meshy.py download PROJETO` preserva originais.
4. **Escolha ao receber STL:** mostrar o link e perguntar: **“Quer que eu faça a preparação e o fatiamento completos ou prefere fatiar manualmente para economizar tokens?”** Opções: “Vou fatiar manualmente” / “Fazer preparação e fatiamento completos”. Registrar com `workflow.py slicing PROJETO manual|full`. A aprovação das imagens não autoriza automaticamente o fatiamento. Aguardar escolha; respeitar decisão explícita já dada para esse modelo.
5. **Malha:** executar `mesh.py inspect ARQUIVO --out RELATORIO.json`; adicionar `--intersections` quando a dependência estiver disponível. Comparar vistas reais com as referências, especialmente face, cauda, mãos e asas. Malha fechada não comprova fidelidade ou imprimibilidade. Não descartar componentes por tamanho sem inspecioná-los. Reparo, corte da base e escala já solicitados permanecem no escopo mesmo no modo manual. Ler [revisão de malha](references/mesh.md) quando necessário. Mudança artística relevante exige correção ou aprovação específica.
6. **Manual:** entregar STL e relatório com limites reais. Não abrir fatiador nem produzir CTB. **Completo:** seguir [CHITUBOX](references/chitubox.md): orientar → avaliar Hollow → avaliar Drill → Auto Support Light → Auto Layout → fatiar → revisar → exportar e reabrir. Nunca pular silenciosamente Hollow/Drill.
7. **Entrega:** `workflow.py report PROJETO` escreve um relatório compacto das decisões e evidências, com hashes dos arquivos registrados. Usar `workflow.py record --help` para registrar etapas. O relatório não certifica qualidade sozinho. Só chamar CTB de pronto após revisão das camadas e pendências resolvidas; distinguir validação digital de teste físico.

## Economia sem perder controle

- `workflow.py doctor` confere dependências sem exibir segredos; instalar apenas o necessário.
- `mesh.py inspect` reutiliza relatório apenas para o mesmo hash, versão do verificador e opções. Saída curta; detalhes no JSON.
- Preparar artefatos e usar scripts para arquivos, métricas e API. Interface do CHITUBOX exige observação e verificação; não automatizar cliques cegos nem usar coordenadas fixas.
- Se a interface ignorar duas tentativas de texto, usar controle acessível ou salvar com nome padrão exclusivo e organizar depois. Não repetir indefinidamente.
- Publicação usa somente os arquivos do manifesto e `scripts/public_audit.py`; projetos, perfis exportados, histórico de conversas e segredos nunca pertencem ao pacote público.
