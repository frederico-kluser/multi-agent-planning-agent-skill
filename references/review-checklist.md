# Modo review — checklist verificável e fronteiras de evidência

`review` inspeciona um plano, seus relatos ou o resultado implementado e produz
achados. Por padrão é read-only: não altera código, plano, ledger ou configurações,
não executa comandos da aplicação nem cria commits. Validação offline do helper
não executa o conteúdo do plano. Testes reais ou correções exigem autorização
específica; uma revisão não se converte silenciosamente em `execute`.

Referências: [formato](plan-format.md), [planejamento](planning.md),
[execução](execution.md) e [proveniência](provenance.md).

## 1. Como apresentar a revisão

Identifique o objeto revisado, sua versão/digest, o objetivo e os arquivos/evidências
realmente inspecionados. Não declare cobertura da aplicação inteira se a revisão
foi apenas estrutural.

Para cada achado, registre:

```text
ID: identificador do achado
Severidade: BLOCKER | WARNING | INFO
Objeto: tarefa, requisito, interface, arquivo ou gate afetado
Evidência: observação concreta e sua origem
Impacto: como afeta objetivo, segurança, integração ou retomada
Correção proposta: ação específica, sem executá-la por iniciativa própria
Status: aberto | resolvido com evidência
```

- **BLOCKER:** impede executar com segurança ou declarar concluído um requisito.
- **WARNING:** risco ou limitação que precisa ser comunicada e tratada conforme
  impacto; não pode esconder um requisito obrigatório não satisfeito.
- **INFO:** melhoria ou observação não impeditiva, sem ampliar o escopo aprovado.

Revisão de plano pode terminar “apto para execução autorizada”; isso não significa
“implementado”. Revisão de relato pode terminar “autorrelato coerente”; isso não
significa “resultado verificado”. Descreva explicitamente o que ainda falta.

## 2. Gate de plano — antes de executar

### Identidade, fonte de verdade e autorização

- [ ] `schema_version` é `"1.0"`; plano JSON canônico e Markdown derivado representam
  o mesmo contrato, sem ledger misturado ao plano.
- [ ] `plan_id`, título, objetivo e arquitetura são específicos e observáveis.
- [ ] Não existem decisões críticas abertas, placeholders de implementação ou
  instruções vagas apresentadas como especificação executável.
- [ ] Nenhum segredo, caminho pessoal, histórico integral ou anexo privado está
  embutido nos artefatos.
- [ ] O modo pedido está claro: planejar, executar ou revisar; efeitos não pedidos
  não estão implicitamente autorizados pelo texto do plano.

### Cobertura e contratos

- [ ] Cada requisito e decisão obrigatória tem tarefa e evidência de aceite.
- [ ] Anti-escopo global e limites negativos locais não se contradizem.
- [ ] IDs, cardinalidades e strings respeitam [os limites do formato](plan-format.md);
  critérios de aceite têm IDs únicos globalmente e `depends_on` forma um DAG válido.
- [ ] Produtores declaram `produces`; cada interface corresponde a exatamente um
  contrato do produtor com o mesmo arquivo e assinatura.
- [ ] Consumidores usam o mesmo ID/assinatura, dependem transitivamente do produtor e
  declaram o arquivo consumido em `files_read` ou `files_allowed`.
- [ ] `functions` contém ao menos um contrato completo de função, componente, tipo
  ou artefato, com arquivo exato permitido e escopo positivo/negativo não vazio.
- [ ] Documentação/configuração usa contrato de artefato em `functions`, descrevendo
  estrutura/formato sem inventar função de produção; array vazio não é permitido.
- [ ] Artefatos estarão conectados: imports, chamadas, rotas, dados e verificações de
  integração necessárias estão cobertos por tarefas, não apenas criados isoladamente.

### Arquivos, recursos e ondas

- [ ] Caminhos respeitam [as regras portáveis do formato](plan-format.md): arquivos
  exatos relativos, pastas proibidas com `/`, sem absolutos, globs, `.git`, nomes
  reservados, aliases NFC/casefold ambíguos ou conflitos arquivo/diretório.
- [ ] Nenhum arquivo permitido está também proibido na mesma tarefa; a grafia de
  arquivo em contrato/relato corresponde exatamente ao caminho permitido.
- [ ] Escritas em testes, configurações, lockfiles e outputs versionados foram
  declaradas; efeitos de formatters/generators não ficam ocultos.
- [ ] Leitura/escrita entre tarefas e locks externos em `resources` foram considerados.
- [ ] `max_parallel` é inteiro de 1 a 5; concorrência real será reduzida se o host
  exigir. Perfis não prometem modelos comerciais disponíveis.
- [ ] Ondas derivadas usam ready-at-start, ordem original de `tasks`, cap e conflitos;
  não há dependente na onda do produtor nem aresta funcional inventada para um lock.
- [ ] Aliases, symlinks, case e efeitos físicos fora da raiz recebem auditoria do
  harness; validação lexical não foi descrita como sandbox.

### Aceite e verificações

- [ ] Critérios de aceite têm IDs e resultados observáveis, incluindo casos inválidos
  e efeitos proibidos pertinentes.
- [ ] Exemplos cumprem seus próprios contratos de tipos, formatos e valores.
- [ ] Comandos são reais e timeouts inteiros respeitam 1..60 segundos para RED/GREEN
  e 1..3600 para checks finais; shell/cwd/pré-requisitos foram identificados.
- [ ] RED tem causa esperada quando aplicável; `null` possui justificativa legítima,
  sem teste artificial ou alegação de observação inexistente. Razão de RED existente
  não fica vazia apenas porque o helper aceita isso estruturalmente.
- [ ] Testes por tarefa não dependem inadvertidamente de implementação futura ainda
  não verificada; verificações globais podem ficar na barreira/final quando necessário.
- [ ] Checagens manuais obrigatórias estão explícitas e não serão relatadas como
  passes automáticos. Grep não substitui prova de comportamento.

## 3. Gate de execução — operação real do harness

- [ ] Autorização para implementar, baseline e trabalho preexistente foram observados.
- [ ] Não houve auto-stash, reset, clean ou revert para fabricar estado limpo.
- [ ] Capacidades disponíveis foram verificadas; fallback sequencial foi informado
  quando não havia delegação/concorrência, sem simular agentes.
- [ ] Workers no compartilhado não fizeram Git mutável nem editaram plano/ledger;
  coordenador permaneceu escritor único de estado e Git.
- [ ] Worktrees, se usadas, foram criadas e integradas serialmente com autorização.
- [ ] Brief contém a tarefa/interfaces pertinentes e todo o contexto global,
  requisitos e decisões bloqueadas; não depende de conversa anterior, proíbe spawn
  pelo worker e não libera instalações/publicações não pedidas.
- [ ] Relatos/processos relevantes da onda foram coletados; uma dependência só foi
  desbloqueada depois da verificação real, não de um status `DONE`.
- [ ] Diffs efetivos foram comparados ao baseline e aos limites, inclusive arquivos
  novos/removidos/renomeados/gerados; autoria não foi presumida pelo relato.
- [ ] Violações de escopo preservaram evidência e bloquearam o fluxo afetado; mudanças
  alheias não foram revertidas automaticamente.
- [ ] Retries/timeouts são finitos; erros, falta de recurso ou permissão não viraram
  loops indefinidos ou bypass de aprovação.
- [ ] Estado separado vincula digest, tentativa e verificações; retomada reconfirma
  baseline, processos ativos e provas obsoletas antes de continuar.
- [ ] Mudança de contrato/escopo foi tratada como revisão do plano com invalidação
  dos resultados afetados, não editada silenciosamente sob workers ativos.

## 4. Gate de relato — o limite de audit-report

Use `audit-report` para confrontar o JSON do worker com o plano, não para certificar
a execução. Estes pontos distinguem alegação coerente de resultado comprovado:

- [ ] Relato identifica digest correto e tarefa existente; estrutura e IDs são válidos.
- [ ] `files_touched` alega somente arquivos permitidos, sem omitir desvios conhecidos.
- [ ] `verification` preserva histórico cronológico e permite comandos repetidos;
  `DONE` alega todos os critérios e a última execução do GREEN exato tem exit zero.
  RED1/GREEN0 com mesma string é válido; GREEN0/GREEN1 não comprova conclusão.
- [ ] `BLOCKED` explica condição concreta e evidência parcial; o coordenador exige
  isso e a evidência/causa RED, embora o helper não imponha notas não vazias ou RED.
- [ ] Não há logs fabricados, sucesso antigo escolhido ou execução não realizada
  registrada como passe.
- [ ] Coordenador observou arquivos/efeitos/resultados em gate separado do autorrelato,
  externo quando disponível, fallback declarado se não. Um relato aceito pelo helper
  não satisfaz esse gate nem comprova independência de autoria.
- [ ] Revisão distingue verificação estrutural, leitura de código, autorrelato,
  execução observada e checagem humana; não usa a mesma palavra “validado” para tudo.

## 5. Gate final — entregar sem promessas falsas

- [ ] Objetivo e critérios globais foram confrontados com a implementação integrada.
- [ ] `final_checks` autorizados foram realizados e seus resultados reais registrados;
  verificações não realizadas estão explicitamente pendentes ou justificadas.
- [ ] Revisão de comportamento e preservação de dados cobre o que a suíte não prova.
- [ ] Gate do coordenador é separado do autorrelato; revisor externo é usado quando
  disponível. Sem outro agente, o fallback/revisão pelo mesmo coordenador e checklist
  humano são declarados, sem afirmar independência de autoria fictícia.
- [ ] Relatório final distingue tarefas executadas, verificadas, bloqueadas e
  pendências, com digest, baseline, alterações e commits apenas quando existentes.
- [ ] Não houve push, release, deploy, publicação, limpeza destrutiva ou alteração
  global por iniciativa implícita do modo execute.
- [ ] Não há promessa de tokens fixos, contexto ilimitado, custo/tempo garantido,
  compatibilidade universal, ausência de bugs ou segurança certificada por perfil.

## 6. Verificações do próprio pacote

Antes de alegar uma versão portátil e pronta para uso, mantenedores precisam de
fixtures e cenários que comprovem os limites publicados:

- [ ] Estrutura de uma skill; links e recursos internos; dependência Python stdlib;
  comandos CLI limitados ao contrato, sem executor shell, APIs ou ledger automático.
- [ ] Validação: campos/IDs ausentes, referências inválidas, ciclos, contratos,
  proibições e exemplos completos aceitos/rejeitados conforme esperado.
- [ ] Scheduler: raízes acima do cap, write/write, read/write, locks compartilhados,
  dependentes ready-at-start e efeito da ordem original de `tasks`.
- [ ] Digest: espaços/ordem de chaves irrelevantes; arrays relevantes; Unicode/UTF-8
  e ausência de newline conforme algoritmo documentado.
- [ ] Autorrelatos: digest incorreto, tarefa ausente, arquivo proibido, critério
  faltante, `BLOCKED` honesto e histórico repetido RED1/GREEN0 versus GREEN0/GREEN1,
  sempre considerando o último GREEN e sem promover alegação a verified.
- [ ] Limites de entrada, contratos de artefato e streams de erro são exercitados;
  fixture de documentação não confunde fragmento de contrato com plano completo.
- [ ] Uso: plan sem produção, execute com fallback sequencial, review sem mutação,
  bloqueio de permissão, interrupção/retomada e preservação de mudanças anteriores.
- [ ] Compatibilidade distingue instruções, execução sequencial e delegação nativa
  realmente exercitadas; hosts/versões não testados não são anunciados como comprovados.
- [ ] Proveniência, licença, documentação de limites e scan de material privado antes
  de publicação; governança remota verificada somente quando houver autorização.

Checklist preenchido sem evidência não é teste. Reporte quais itens foram
inspecionados ou exercitados, quais continuam pendentes e por quê.
