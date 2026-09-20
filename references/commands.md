# Comandos, modos e recuperação

Execute os scripts com Python 3.10+ e mantenha projetos fora da instalação da skill. Por padrão, use `C:\Users\eep0x10\Downloads\CritForge\<projeto>` como raiz privada de cada projeto; isso mantém os modelos e imagens organizados nos Downloads e separados do repositório público.

```sh
python scripts/workflow.py doctor
python scripts/workflow.py init PROJETO
# Para monstros ou escala não padrão:
python scripts/workflow.py limits PROJETO --max-height-mm 90 --base-mm 64
python scripts/workflow.py approve-images PROJETO --front frente.png --back verso.png --face rosto.png
python scripts/meshy.py submit PROJETO --mode image-4k
python scripts/meshy.py watch PROJETO --seconds 45
python scripts/meshy.py download PROJETO
python scripts/mesh.py inspect modelo.stl --out revisao.json --intersections
python scripts/mesh.py scale modelo.stl final.stl --height-mm 38
python scripts/mesh.py inspect final.stl --out final.json --units mm --base-mm 32 --intersections
python scripts/preview.py final.stl --out-dir vistas --face X Y Z LARGURA
python scripts/workflow.py artifact PROJETO final-stl 03-modelo-corrigido/final.stl
python scripts/workflow.py record PROJETO visual passed --note "Revisado" --evidence 06-verificacao/visual.md
python scripts/workflow.py record PROJETO mesh passed --note "Revisado" --evidence 06-verificacao/final.json
python scripts/workflow.py report PROJETO
```

## Modos do Meshy

| Modo | Entrada de geometria | Resolução | Uso |
| :--- | :--- | :--- | :--- |
| `image-4k` | vista frontal | 4096³ | padrão para maior detalhe |
| `multi-image-2k` | frente, verso e rosto | 2048³ | prioriza consistência multivista |

O cliente usa Meshy 7.1, ativa o aprimoramento de imagem para acompanhar o preset do site, não gera textura nem remesh, pede STL/GLB e registra o modo no projeto. No modo 4K, verso e rosto não são enviados como geometria: permanecem como referências obrigatórias para a revisão visual. `multi_view_thumbnails` não é enviado quando `auto_size` está desligado, pois a API documenta esse recurso apenas junto do dimensionamento automático.

`MESHY_API_KEY` vem apenas do ambiente. Nunca passe o valor por argumento, grave em `.env` dentro da skill ou imprima o ambiente.

## Submissões e falhas

Um marcador durável é criado antes do POST. Se a rede falhar depois da cobrança, o cliente bloqueia outro envio. Localize a tarefa na conta e recupere com o modo correto:

```sh
python scripts/meshy.py recover PROJETO TASK_ID --mode image-4k
```

Tarefas `FAILED`, `EXPIRED` ou `CANCELED` exigem diagnóstico antes de nova geração. Um modelo concluído mas artisticamente errado pode ser rejeitado e regenerado em outro projeto; limite tentativas automáticas para evitar gasto indefinido.

Downloads são atômicos, limitados a HTTPS do domínio Meshy e validados estruturalmente antes de substituir o arquivo parcial. URLs assinadas e respostas brutas não são persistidas.

## Contrato de entrega

O único artefato final obrigatório é `final-stl`. Ele deve ser STL válido, não vazio, dimensionado em milímetros, ter altura de até 45 mm e possuir revisões visual e de malha ligadas ao hash final. `delivery_ready=true` comprova esse contrato documental; não certifica impressão física.

`python scripts/validate.py` executa testes offline e auditoria do pacote público. Não chama a API nem modifica modelos privados.
