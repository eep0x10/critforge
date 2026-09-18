# Comandos e recuperação

Executar a partir da pasta da skill ou usar caminhos absolutos para os scripts. Python 3.10+. `workflow.py` e `meshy.py` usam apenas a biblioteca padrão; inspeção requer `requirements-mesh.txt`. Não instalar Blender, fatiador ou pacotes em segundo plano sem necessidade.

```sh
python scripts/workflow.py doctor
python scripts/workflow.py init /path/to/private-project
python scripts/workflow.py approve-images /path/to/private-project --front front.png --back back.png --face face.png
python scripts/meshy.py submit /path/to/private-project
python scripts/meshy.py watch /path/to/private-project --seconds 45
python scripts/meshy.py download /path/to/private-project
# Perguntar a escolha do usuário antes de registrar:
python scripts/workflow.py slicing /path/to/private-project manual
python scripts/mesh.py inspect model.stl --out review.json
python scripts/mesh.py scale model.stl model-scaled.stl --height-mm 36
python scripts/mesh.py inspect model-scaled.stl --out review-scaled.json --base-mm 32 --intersections
python scripts/preview.py model.stl --out-dir /path/to/private-project/06-verificacao/views
python scripts/mesh.py compare before.stl after.stl --out comparison.json
python scripts/preview.py after.stl --reference before.stl --out-dir /path/to/private-project/06-verificacao/comparison
python scripts/workflow.py artifact /path/to/private-project final-stl 03-modelo-corrigido/model.stl
python scripts/workflow.py record /path/to/private-project mesh passed --note "Reviewed geometry and scale" --evidence 06-verificacao/review.json
python scripts/workflow.py report /path/to/private-project
```

`approve-images` e `slicing` registram decisões; não são substitutos para consentimento humano. Configurar `MESHY_API_KEY` fora do repositório, pelo ambiente/gerenciador de segredos. Não passar o valor na linha de comando, não gravar `.env` na skill, não exibir variáveis do ambiente.

## API

O cliente fixa `meshy-7`, sem textura/remesh, frente primeiro e saídas STL/GLB. Verificar mudanças na [documentação oficial](https://docs.meshy.ai/en/api/multi-image-to-3d) antes de alterar os parâmetros. Não há preço fixo no script: registrar `consumed_credits` retornado. Os testes usam respostas simuladas, sem gastar créditos.

`submit` cria um marcador durável antes do POST. Uma falha de rede pode ocorrer depois da cobrança; **não repetir POST nem apagar o marcador para tentar novamente**. Recuperar o ID na conta Meshy e executar `meshy.py recover PROJETO TASK_ID`. O servidor é consultado para validar esse ID; o operador precisa confirmar que é a tarefa das imagens aprovadas. Se a tarefa realmente não foi criada, confirmar isso antes de iniciar uma nova revisão de projeto. Não há promessa de idempotência no servidor.

Uma trava exclusiva impede alterações simultâneas pelo CLI. Depois de um processo interrompido, conferir se ele terminou antes de remover manualmente `.workflow.lock`. `status` local mostra apenas estado salvo; `meshy.py status` atualiza a tarefa na API. `watch` não é um serviço agendado: termina no prazo definido, imprimindo apenas mudanças. O agente usa blocos curtos para continuar disponível ao usuário.

Downloads são atômicos, sem cabeçalho de autenticação e restritos a HTTPS no domínio Meshy, inclusive redirecionamentos. URLs assinadas e respostas brutas não são salvas. Uma mudança de CDN exige revisão do domínio; nunca relaxar essa restrição com host arbitrário. Retomar download não cria nova geração.

## Automação e saída

`python scripts/validate.py` executa testes offline e auditoria do pacote em um comando. CI repete essas verificações. Não inicia o CHITUBOX nem uma impressão. Relatórios extensos ficam em arquivos, saídas de terminal são JSON compacto.

`mesh.py` não corrige automaticamente nem descarta componentes. Verificações caras só devem ser repetidas após alteração do arquivo, das opções ou da versão das dependências. `public_audit.py` é defesa adicional, não uma garantia universal contra qualquer dado pessoal: revisar o manifesto, os arquivos e a identidade de commit antes da publicação.

Registrar os artefatos da etapa antes de marcar os checks correspondentes. Alterar um artefato já associado a um check invalida esse check; adicionar uma nova saída não invalida revisões anteriores. Reconfirmar a evidência aplicável após mudanças. Hashes detectam alterações, não comprovam que uma revisão humana foi feita.

## Contrato de entrega

Manual exige `final-stl` (.stl válido e não vazio), visual e mesh. Completo exige também `final-project` (.ctp ou .chitubox), `final-slice` (.ctb) e todas as etapas. O projeto e CTB são verificados por existência, extensão, tamanho, hash e evidências de reabertura; o script não interpreta o formato proprietário nem comprova compatibilidade sozinho.

Registrar `final-stl` **antes** de visual/mesh. Registrar os três finais antes de slice-review/reopen; esses checks precisam conter os hashes finais. Artefatos antigos chamados `corrected-stl` devem ser registrados como `final-stl` e ter as revisões reconfirmadas. Não preencher checks automaticamente para remover pendências. `delivery_ready` significa apenas contrato documental e arquivos verificados.

```sh
python scripts/workflow.py artifact /path/to/private-project final-project 04-chitubox/model.ctp
python scripts/workflow.py artifact /path/to/private-project final-slice 05-impressao/model.ctb
```

FAILED, EXPIRED e CANCELED/CANCELLED encerram `watch`; status desconhecido também interrompe a consulta automática. Consultar a falha na conta e decidir com o usuário antes de uma nova geração paga. Nunca limpar a trava de submissão para contornar isso.

Downloads validam estrutura e coordenadas finitas do STL e cabeçalho/chunks do GLB antes da promoção do `.partial`. Interrupções removem o parcial; executar `download` novamente recupera o arquivo sem novo POST. Essa validação estrutural não substitui inspeção de malha ou renderização.
