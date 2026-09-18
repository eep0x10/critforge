# Revisão e reparo de malha

Preservar sempre o original. A inspeção registra hash, extensão em unidades do STL, fechamento, normais, componentes e opcionalmente auto-interseções. STL não declara unidade: só interpretar dimensões como mm após confirmar escala. A contagem de componentes pode revelar fragmentos, mas acessórios legítimos também podem estar separados.

`mesh.py scale entrada.stl saida.stl --height-mm 36` aplica escala uniforme assumindo Z vertical, assenta Z mínimo em zero e registra antes/depois. Confirmar orientação antes. Não usar largura total da escultura como medida dos pés. `--base-mm 32 --foot-band-mm 2` na inspeção mede um círculo conservador dos vértices próximos ao chão; falha nesse teste não prova que o melhor círculo não cabe, e aprovação não prova contato plano.

Remover base/terreno respeitando pés, cauda e equipamento. Não automatizar cortes com coordenadas de outro modelo. Para reparos, começar pela menor alteração que resolva o defeito. Se usar reconstrução volumétrica, preferir implementação esparsa (como OpenVDB); escolher resolução pela escala final e recursos disponíveis. Comparar volume, dimensões e detalhes antes/depois, e refazer inspeção. Não transformar “watertight” em sinônimo de qualidade de impressão.

Verificar espessura e fragilidade de dedos, dentes, pontas e membranas no modelo final. As ferramentas fornecidas não certificam espessuras, cavidades ou resistência. Gerar vistas reais com um renderizador de malha/Blender e comparar com as imagens; não usar geração de imagem para representar o STL inspecionado.
