# Sua primeira miniatura com CritForge

[← Visão geral](../README.md) · [Comandos completos](../references/commands.md)

Você pode começar pela conversa com o agente. Os scripts organizam os arquivos e verificações; o agente continua responsável por revisar imagens e malhas e registrar decisões reais.

## 1. Instalação e diagnóstico

Siga os comandos de instalação no [README](../README.md#comece-em-poucos-minutos). Para outro agente, instale a pasta onde ele descobre skills e use [SKILL.md](../SKILL.md) como entrada; a integração de ferramentas depende desse agente.

Execute na pasta da skill:

```sh
python scripts/workflow.py doctor
```

O diagnóstico verifica módulos opcionais, Blender no PATH e presença de `MESHY_API_KEY`. Um resultado negativo indica algo a preparar para a etapa correspondente, não a necessidade de instalar tudo.

| Dependência | Quando é necessária |
| :--- | :--- |
| Python 3.10+ | Scripts locais |
| NumPy, trimesh e SciPy | Inspeção, escala e comparação |
| Pillow | Montagem das folhas de contato |
| Blender | Renderização real; informe `--blender` se não estiver no PATH |
| pymeshlab | Inspeção com `--intersections` |
| Meshy API | Geração e download do modelo |
| CHITUBOX + controle de interface | Somente quando você escolher fatiamento completo |

Para instalar `pymeshlab`, se necessário:

```sh
python -m pip install pymeshlab
```

Use o mesmo interpretador/ambiente Python nas instalações e nos comandos. Em Windows, `py -3` pode ser usado no lugar de `python` quando esse for o comando disponível.

## 2. Configure a chave de forma privada

O cliente lê **`MESHY_API_KEY`** do ambiente do processo. Configure-a pelo mecanismo de segredos do seu agente ou nas variáveis de ambiente do sistema, fora da conversa e do repositório. Se alterou o ambiente após abrir o agente, inicie uma nova sessão para que ele receba a variável.

- Não coloque a chave em argumentos de comandos, imagens, relatórios ou `.env` dentro da skill.
- Não imprima variáveis do ambiente para diagnosticar; use `doctor`.
- A conta precisa de acesso à API e créditos. Veja a [documentação oficial do Meshy](https://docs.meshy.ai/en/api/multi-image-to-3d).

## 3. Abra um projeto separado

Escolha uma pasta **fora da instalação da skill**, por exemplo `D:/Miniaturas/guerreiro-draconico` no Windows. Esse caminho é apenas ilustrativo; use uma pasta válida no seu sistema.

```sh
python scripts/workflow.py init /path/to/private-project
```

Estrutura criada:

```text
private-project/
├── 00-documentacao/       decisões e relatório de entrega
├── 01-imagens/            frente, verso e rosto aprovados
├── 02-meshy-original/     STL e GLB originais preservados
├── 03-modelo-corrigido/   versões de escala e reparo
├── 04-chitubox/           projeto editável, quando solicitado
├── 05-impressao/          arquivo fatiado, quando solicitado
├── 06-verificacao/        métricas, vistas e evidências
├── 90-processamento/      arquivos intermediários
└── project.json          estado local para retomada
```

## 4. Dê um briefing útil

Inclua espécie/personagem, classe, pose, equipamentos, detalhes importantes e espaço de base. Personagens são gerados sem base integrada; 32 mm é a referência para a base separada. Para monstros, indique a área do grid, como 2×2 ou 4×2 células de 32 mm.

**Exemplo**

> Use CritForge ($meshy-miniaturas) para criar uma patrulheira anã com capa curta e machado, em postura defensiva. Sem terreno ou base integrada, para encaixar numa base separada de 32 mm. Frente e verso devem mostrar a mesma pose. Quero um detalhe do rosto e revisão completa das imagens antes da minha aprovação.

A revisão visual procura membros extras, fusões, mãos e armas inconsistentes, cauda mal conectada, detalhes frágeis e diferenças entre vistas. O agente corrige e apresenta as referências antes da geração paga.

## 5. Escolha como finalizar

Depois do download do STL, o agente pergunta se você quer fatiar manualmente ou seguir com a preparação completa. Essa escolha não elimina reparos, remoção de base e escala que você já solicitou.

| Escolha | Entrega |
| :--- | :--- |
| Manual | STL final revisado e relatório de limites/pendências |
| Completa | STL, projeto editável, CTB e relatório, após preparação e revisão |

Os comandos `approve-images`, `slicing` e `record` registram decisões e evidências. Eles não concedem consentimento nem realizam uma revisão humana por si só.

## 6. Retome sem repetir trabalho

```sh
python scripts/workflow.py status /path/to/private-project
```

Esse comando lê o estado salvo. `meshy.py status PROJETO` consulta o serviço; `meshy.py watch PROJETO --seconds 45` acompanha por um período curto. Veja os argumentos completos com `--help` ou no [guia de comandos](../references/commands.md).

<details>
<summary><strong>O envio ao Meshy foi interrompido</strong></summary>

Não envie outra geração nem apague o marcador de submissão. A tarefa pode existir e já ter consumido créditos. Localize o ID na conta, confirme que corresponde às imagens aprovadas e use `meshy.py recover PROJETO TASK_ID`.

</details>

<details>
<summary><strong>O download falhou ou o arquivo veio corrompido</strong></summary>

Execute `meshy.py download PROJETO` novamente. Isso retoma os arquivos da tarefa existente, sem gerar um novo modelo. Arquivos já verificados são preservados; arquivos desconhecidos existentes exigem inspeção antes de substituição.

</details>

<details>
<summary><strong>O Blender não foi encontrado</strong></summary>

Use `preview.py MODELO --out-dir PASTA --blender EXECUTAVEL`. O caminho deve apontar para o executável Blender, não para a pasta de instalação. A renderização é feita em segundo plano e não modifica a malha.

</details>

<details>
<summary><strong>O relatório ainda mostra pendências</strong></summary>

Confira os arquivos `final-stl`, `final-project` e `final-slice` aplicáveis ao modo escolhido. Verifique se as evidências existem e se foram registradas para os hashes finais. Não marque checks como aprovados apenas para limpar o relatório.

</details>

## Atualização e validação

Se instalou por Git, confira mudanças locais antes de atualizar:

```sh
git status --short
git pull --ff-only
python -m pip install -r requirements-mesh.txt
python scripts/validate.py
```

Preserve alterações locais antes do `pull`; não use reset forçado para descartá-las. Os testes são offline. Eles não geram modelos, abrem o fatiador ou iniciam impressão.

**Próximo passo:** [entenda a revisão de malha](../references/mesh.md) ou [consulte o fluxo do CHITUBOX](../references/chitubox.md).
