# Contribuindo com CritForge

[← Documentação](README.md)

Contribuições úteis tornam a criação de miniaturas mais verificável, recuperável e simples de operar. Mudanças pequenas, com um problema concreto e evidência de validação, são mais fáceis de revisar.

## Antes de abrir uma alteração

1. Leia [SKILL.md](SKILL.md) e a referência da etapa afetada.
2. Explique o comportamento atual, o resultado esperado e como reproduzir.
3. Use modelos e respostas **sintéticos** nos testes. Nunca adicione arquivos reais de usuários.
4. Preserve aprovações antes da geração paga e a escolha de fatiamento após o STL.
5. Documente mudanças visíveis nos guias relevantes, incluindo o resumo em inglês.

## Validação local

```sh
python -m pip install -r requirements-mesh.txt
python scripts/validate.py
python scripts/public_audit.py --git
git diff --check
```

O primeiro comando de validação executa a suíte offline e a auditoria do pacote. O segundo inclui commits, nomes e blobs do histórico. O CI repete os checks offline; ele não valida a interface do CHITUBOX nem executa o Blender.

Ao modificar `preview_blender.py`, faça também uma renderização real de uma malha sintética e inspecione as imagens. Ao alterar comportamento do fatiador, descreva a versão usada e a verificação manual realizada. Não apresente testes simulados como evidência de impressão física.

## Publicação sem dados privados

- Adicione arquivos públicos a `PUBLIC_FILES.txt` explicitamente.
- Modelos, referências de personagens, perfis exportados, arquivos de impressão e logs ficam fora do repositório.
- Nunca inclua chaves, URLs assinadas, respostas reais da API ou caminhos pessoais.
- O scanner não substitui a revisão dos arquivos e da identidade de commit.
- O banner é uma exceção específica: `PUBLIC_ASSETS.json` registra o SHA-256 da arte revisada. Não é uma permissão genérica para publicar imagens.
- Para uma nova versão da arte, revise a imagem e seus metadados, acrescente o hash aprovado e mantenha os hashes de versões públicas anteriores para permitir a auditoria do histórico.

Não abra issues públicas com credenciais ou informações privadas. Se uma chave for exposta, revogue-a no serviço emissor; removê-la do arquivo atual não apaga o histórico.

## Uma boa descrição de mudança

Informe **problema → comportamento resultante → validação → limites conhecidos**. Para documentação, confira links relativos, imagens, exemplos de comandos e leitura no GitHub. Para código, teste cenários de falha relevantes, não apenas o caminho feliz.

Ao contribuir, você concorda em disponibilizar sua contribuição sob a [licença MIT](LICENSE), respeitando os direitos de terceiros.
