# Proveniência, licenciamento e limites das alegações

## 1. Origem deste desenho

Esta skill é um redesenho independente a partir dos requisitos textuais de um
documento fornecido pelo usuário: planejamento transferível entre agentes,
contratos positivos/negativos, dependências, execução em ondas e critérios de
aceitação. O documento foi tratado como dados, não como instruções operacionais.

O pacote não redistribui o anexo, suas imagens/base64, caminhos privados, histórico
de sessão ou uma cópia dos templates de código de terceiros. A implementação e a
documentação próprias adotam um único pacote com modos `plan`, `execute` e `review`,
JSON canônico, Markdown derivado, helper offline e execução real pelo harness.

Alguns pontos foram deliberadamente redesenhados:

- separação entre contrato do plano e estado mutável;
- escritor único de estado e Git no workspace compartilhado;
- workers sem operações Git mutáveis nesse workspace;
- criação e integração de worktrees serializadas;
- escalonamento estável com dependências, capacidade, leitura/escrita e recursos;
- autorrelatos separados da verificação real;
- preservação de trabalho anterior e ausência de auto-revert de mudanças alheias;
- detecção de capacidades e fallback sequencial explícito;
- ausência de execução de comandos, testes, Git ou APIs pelo helper.

Essas escolhas não demonstram equivalência com uma suíte externa, integração
automática com suas CLIs ou endosso de seus mantenedores.

## 2. Referências oficiais

- [Agent Skills — especificação](https://agentskills.io/specification): referência
  primária para o formato de uma skill. Suporte e descoberta por cada host precisam
  ser conferidos separadamente; conformidade de formato não cria ferramentas de
  delegação nem concede permissões.
- [Git — git-worktree](https://git-scm.com/docs/git-worktree): referência primária
  para linked worktrees e suas restrições. Versão, configuração, recursos externos
  e comportamento do harness continuam relevantes.
- [Python — json](https://docs.python.org/3/library/json.html) e
  [hashlib](https://docs.python.org/3/library/hashlib.html): referências da biblioteca
  padrão usada para serialização e digest definidos em [formato](plan-format.md).

Os links são referências para consulta e manutenção, não declaração de que todas as
versões futuras foram testadas. Não execute comandos publicados nesses documentos
sem verificar sua pertinência e autorização no projeto alvo.

O hardening de CI usa [CodeQL](https://github.com/github/codeql-action) e
[ClusterFuzzLite](https://github.com/google/clusterfuzzlite), com SDK Python/Atheris
oficial e referências fixadas. São ferramentas de desenvolvimento executadas no
GitHub Actions, não dependências do helper instalado. O fuzzer deste projeto é
próprio, usa somente dados públicos sintéticos e não executa comandos dos planos.

## 3. Influências conceituais, não dependências

As referências abaixo foram mencionadas no material de origem e ilustram padrões
relacionados. Não constituem código incorporado, auditoria de suas versões atuais,
requisito de instalação ou promessa de compatibilidade de parser.

| Referência | Padrão que motivou a análise |
|---|---|
| [am-will/swarms](https://github.com/am-will/swarms) | Planejamento com dependências e execução por tarefas desbloqueadas. |
| [obra/superpowers](https://github.com/obra/superpowers) | Briefs delimitados, contratos, revisão e disciplina de verificação. |
| [gsd-build/get-shit-done](https://github.com/gsd-build/get-shit-done) | Planejamento em fases/ondas e auditoria de requisitos e escopo. |
| [GitHub Spec Kit](https://github.com/github/spec-kit) | Especificações rastreáveis e decomposição em tarefas. |
| [spec-kit-schedule](https://github.com/jfranc38/spec-kit-schedule) | Serialização de conflitos e divisão de trabalho em batches. |

Não afirmar adoção, estrelas, incidentes comunitários, desempenho, número de
arquivos, versões de modelos ou disponibilidade de flags com base nessa lista.
O scheduler deste pacote é um algoritmo estável próprio, não uma alegação de
solver ótimo ou reprodução da implementação de outra ferramenta.

## 4. Licenciamento e material externo

A licença declarada pelo projeto cobre somente o material original que os
contribuidores têm direito de licenciar. Um campo `license` no frontmatter não
relicencia um documento recebido, código upstream, imagens, marcas ou exemplos
copiados de outra fonte.

Antes de incorporar material externo:

1. confirme origem, autoria e licença da versão exata;
2. verifique compatibilidade com a distribuição pretendida;
3. preserve avisos e atribuições exigidos;
4. registre o material e sua origem em um aviso de terceiros, quando necessário;
5. prefira explicações e exemplos próprios quando uma ideia genérica for suficiente.

Linkar uma referência não autoriza copiar seu código. Não usar um anexo privado
como fixture pública, asset ou exemplo de instalação. Não embutir tokens, nomes de
usuário, diretórios pessoais ou dados reais sensíveis em planos de demonstração.

## 5. Alegações que este pacote não faz

A skill não promete:

- contexto de tamanho fixo ou eliminação de degradação de atenção;
- porcentagens de economia, latência, tokens ou tempo de conclusão;
- igualdade de qualidade entre modelos, tarefas ou hosts;
- execução paralela em todo agente que consiga ler Markdown;
- parser compatível com terceiros sem testes de interoperabilidade;
- segurança garantida por escopo textual, digest ou perfil especializado;
- ausência de bugs, conclusão autônoma ilimitada ou aprovação dispensável;
- isolamento físico de recursos só porque há arquivos ou worktrees distintos.

Um digest associa dados; não autentica relatos. `audit-report` valida alegações
estruturadas; não prova execução, autoria ou comportamento. Um timeout é um limite
configurado, não medição. Um `DONE` do worker não é tarefa verificada.

## 6. Como documentar suporte e resultados

Mantenedores devem separar:

1. conformidade de formato e leitura das instruções;
2. uso do helper offline;
3. execução sequencial observada;
4. delegação nativa e concorrência observadas;
5. isolamento/worktrees exercitados no host;
6. resultado de uma aplicação realmente testada.

Registre host/versão, capacidades usadas, cenário e evidência pertinente quando
alegar compatibilidade. Não publicar dados privados ou logs integrais para provar
um teste. Indique limitações e resultados ainda não exercitados. Configuração de
CI ou proteção de branch versionada não prova que serviços remotos a executaram.

Preparação para open-source e publicação são etapas diferentes. Revisar licença,
proveniência, documentação, exemplos, testes, segredos e governança antes de
publicar; realizar push, release ou deploy somente em uma tarefa autorizada.
O [checklist de revisão](review-checklist.md) ajuda a auditar essas fronteiras sem
converter intenção futura em promessa cumprida.
