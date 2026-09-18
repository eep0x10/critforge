# Revisão e reparo de malha

Preservar sempre o original. A inspeção registra hash, extensão em unidades do STL, fechamento, normais, componentes e opcionalmente auto-interseções. STL não declara unidade: só interpretar dimensões como mm após confirmar escala. A contagem de componentes pode revelar fragmentos, mas acessórios legítimos também podem estar separados.

`mesh.py scale entrada.stl saida.stl --height-mm 36` aplica escala uniforme assumindo Z vertical, assenta Z mínimo em zero e registra antes/depois. Confirmar orientação antes. Não usar largura total da escultura como medida dos pés. `--base-mm 32 --foot-band-mm 2` na inspeção mede um círculo conservador dos vértices próximos ao chão; falha nesse teste não prova que o melhor círculo não cabe, e aprovação não prova contato plano.

Remover base/terreno respeitando pés, cauda e equipamento. Não automatizar cortes com coordenadas de outro modelo. Para reparos, começar pela menor alteração que resolva o defeito. Se usar reconstrução volumétrica, preferir implementação esparsa (como OpenVDB); escolher resolução pela escala final e recursos disponíveis. Comparar volume, dimensões e detalhes antes/depois, e refazer inspeção. Não transformar “watertight” em sinônimo de qualidade de impressão.

Verificar espessura e fragilidade de dedos, dentes, pontas e membranas no modelo final. As ferramentas fornecidas não certificam espessuras, cavidades ou resistência. Gerar vistas reais com um renderizador de malha/Blender e comparar com as imagens; não usar geração de imagem para representar o STL inspecionado.

## Prévia e comparação reproduzíveis

`preview.py modelo.stl --out-dir PASTA --blender EXECUTAVEL` gera frente, verso, lados, perspectiva, detalhe e uma folha de contato. Usa triângulos reais sem remesh ou decimação, câmeras ortográficas e material neutro. STL/PLY assumem Z vertical, frente observada de -Y; confirmar orientação. `--face X Y Z WIDTH` enquadra explicitamente o rosto em unidades do modelo. Sem isso, o detalhe é um recorte superior **heurístico**, não uma localização automática garantida do rosto.

`preview.py depois.stl --reference antes.stl --out-dir NOVA_PASTA` gera as duas revisões com limites/câmeras compartilhados, mantendo diferenças de tamanho visíveis. Os modelos precisam compartilhar orientação e unidades; não centralizar cada revisão separadamente para esconder mudanças. O cache verifica entradas, worker, executável Blender e hashes das saídas. Pasta alterada exige novo diretório de revisão. Nenhuma imagem criada por IA substitui essas vistas.

`mesh.py compare antes.stl depois.stl --out comparacao.json` registra hashes, métricas e alertas. Tolerâncias padrão: 2% nas dimensões e 5% no volume, configuráveis com `--dimension-tolerance`/`--volume-tolerance`; são indicadores de revisão, não tolerâncias garantidas de impressão. Volume só é comparado se ambas as malhas estiverem fechadas, com orientação consistente e volume positivo. Componentes alterados, fechamento perdido ou normais incoerentes exigem investigação. Comparar reparos na mesma escala; uma alteração de escala intencional deve ser avaliada separadamente.

Revisar lado a lado face, dedos, cauda, asas e acessórios mesmo sem alertas numéricos. O comparador não aceita reparos automaticamente e não mede espessura ou auto-interseções. Rodar a inspeção com `--intersections` e os demais checks aplicáveis antes da entrega.
