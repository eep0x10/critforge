# Meshy Miniaturas

Skill em português para criar miniaturas de RPG/boardgame: **imagens revisadas → Meshy → revisão do STL → escolha de fatiamento manual ou completo no CHITUBOX**.

## O que melhora

- Estado por projeto e retomada pelo mesmo ID, evitando repetir gerações pagas.
- Aprovação vinculada aos hashes das três imagens.
- Consulta periódica com saída compacta e prazo definido.
- Inspeção de malha com cache por hash, opções e versões.
- Escala explícita, sem sobrescrever o original ou cortar peças automaticamente.
- Hollow e Drill sempre avaliados; Auto Support Light continua sujeito à revisão.
- Relatório de evidências e escolha manual para economizar chamadas e tokens.
- Entrega bloqueada quando faltam arquivos finais ou revisões vinculadas a seus hashes.
- Vistas reais via Blender, com cache e câmeras iguais para comparar revisões.
- Comparação de reparos: fechamento, componentes, dimensões e volume confiável.
- Validação estrutural STL/GLB e recuperação de downloads interrompidos.

Não há medição de economia de tokens nem promessa de impressão perfeita. O controle do CHITUBOX depende de ferramenta de interface disponível; os scripts **não são um fatiador headless**. Não há impressão física automática.

## Instalar

Copiar esta pasta para o diretório de skills do seu agente, com o nome `meshy-miniaturas` (por exemplo, `~/.codex/skills/meshy-miniaturas`). Começar por [SKILL.md](SKILL.md). Requer Python 3.10+.

```sh
python scripts/workflow.py doctor
python -m pip install -r requirements-mesh.txt
python scripts/validate.py
```

A API lê `MESHY_API_KEY` exclusivamente do ambiente. Configure o segredo localmente, sem registrá-lo no Git ou enviá-lo no chat. Veja [comandos e recuperação](references/commands.md).

## Configuração e limites

O perfil JSON de LD-006 / Standard V2 cinza contém valores **iniciais, não calibrados**, e não é um perfil nativo importável. Verifique resinagem, exposição e compatibilidade de firmware no seu equipamento. Base de 32 mm é uma convenção configurável deste fluxo; não define a altura da escultura.

Testes sintéticos cobrem estado, repetição de tarefas, interrupções, downloads, escala, cache e privacidade. Não gastam créditos nem comprovam comportamento de uma versão específica do CHITUBOX. A integração usa a [API oficial do Meshy](https://docs.meshy.ai/en/api/multi-image-to-3d).

Prévia requer Blender local (worker testado em 4.5) e Pillow. O teste offline/CI não inicia Blender; validar uma renderização real ao mudar o worker. Vistas assumem Z vertical e frente em -Y. O recorte automático superior precisa de conferência para representar o rosto.

## Privacidade e publicação

Projetos ficam fora desta pasta. Este pacote não inclui chaves, imagens, modelos, respostas reais da API, perfis exportados ou histórico de conversas. `PUBLIC_FILES.txt` define os arquivos permitidos; a auditoria examina também arquivos rastreados e blobs do histórico Git, quando executada com `--git`.

Use o projeto apenas para conteúdo que você possa processar e compartilhar. A licença do código não concede direitos sobre personagens, referências ou modelos criados pelos usuários.
