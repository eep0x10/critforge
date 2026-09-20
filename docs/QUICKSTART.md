# Sua primeira miniatura com CritForge

[← Visão geral](../README.md) · [Comandos completos](../references/commands.md)

## 1. Diagnóstico

```sh
python scripts/workflow.py doctor
```

Instale `requirements-mesh.txt` para inspeção e comparação. Blender produz as vistas reais; `pymeshlab` habilita a busca de auto-interseções. Nenhum fatiador faz parte deste fluxo.

## 2. Chave privada

Configure `MESHY_API_KEY` no ambiente do processo ou gerenciador de segredos. Não use argumento de comando, `.env` versionado, relatório ou chat. A conta precisa de créditos da API Meshy.

## 3. Projeto privado

```sh
python scripts/workflow.py init /path/to/private-project
```

```text
private-project/
├── 00-documentacao/       briefing e relatório
├── 01-imagens/            referências aprovadas
├── 02-meshy-original/     downloads preservados
├── 03-modelo-corrigido/   STL reparado e dimensionado
├── 06-verificacao/        métricas e renders
├── 90-processamento/      intermediários
└── project.json           estado retomável
```

## 4. Aprovação e geração

Depois de revisar frente, verso e rosto:

```sh
python scripts/workflow.py approve-images PROJETO --front frente.png --back verso.png --face rosto.png
python scripts/meshy.py submit PROJETO --mode image-4k
python scripts/meshy.py watch PROJETO --seconds 45
python scripts/meshy.py download PROJETO
```

O modo padrão gera geometria 4K a partir da frente. As outras vistas continuam obrigatórias para comparar o STL. `--mode multi-image-2k` usa as três imagens diretamente, com o limite 2K do endpoint multivista.

## 5. Revisão e escala

```sh
python scripts/mesh.py inspect original.stl --out original.json --intersections
python scripts/preview.py original.stl --out-dir vistas-original
python scripts/mesh.py scale original.stl final.stl --height-mm 38
python scripts/mesh.py inspect final.stl --out final.json --units mm --intersections --base-mm 32
python scripts/preview.py final.stl --out-dir vistas-final --face X Y Z LARGURA
```

Compare a geometria com todas as referências. Rejeite peças fundidas, colisões, acessórios inventados, mãos ou rosto divergentes. Uma tentativa rejeitada permanece preservada; uma nova geração usa outro projeto de revisão.

## 6. Entrega

```sh
python scripts/workflow.py artifact PROJETO final-stl 03-modelo-corrigido/final.stl
python scripts/workflow.py record PROJETO visual passed --note "Renders comparados com as referências" --evidence 06-verificacao/visual.md
python scripts/workflow.py record PROJETO mesh passed --note "Escala e topologia revisadas" --evidence 06-verificacao/final.json
python scripts/workflow.py report PROJETO
```

O relatório só fica pronto com `final-stl`, evidência atual de visual e malha e altura final de até 45 mm. O resultado não inclui suportes, projeto de fatiador ou arquivo fatiado.

## Recuperação

- **POST incerto:** não repita. Recupere o ID e informe o modo original em `meshy.py recover PROJETO ID --mode image-4k`.
- **Download interrompido:** execute `meshy.py download` novamente; isso não cria outra geração.
- **Blender fora do PATH:** use `preview.py ... --blender EXECUTAVEL`.
- **Resultado bugado:** registre a rejeição, corrija a referência se necessário e use uma nova pasta de revisão.
