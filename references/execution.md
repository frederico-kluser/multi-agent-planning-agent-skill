# Modo execute — implementar com barreiras verificadas

A execução pertence ao harness e ao coordenador. O helper Python só manipula dados:
validar, escalonar, renderizar, extrair briefs e auditar autorrelatos. Ele nunca
executa testes, comandos, Git, APIs ou atualizações de ledger. Leia
[o formato do plano](plan-format.md) e [o checklist de revisão](review-checklist.md).

**Independent verifier** significa um gate do coordenador separado do autorrelato:
conferir efeitos e evidências, não aceitar `DONE` como prova. Use revisor externo
quando disponível. Sem outro agente, o coordenador mantém esse gate e declara o
fallback/revisão pelo mesmo agente, com checagem humana pertinente; não inventa
independência de autoria nem um segundo processo.

## 1. Preflight: autorização, contexto e trabalho existente

1. Confirme que o humano autorizou implementar o plano identificado. Aprovar uma
   arquitetura ou pedir `review` não equivale a autorizar mudanças de código.
2. Leia o JSON canônico, valide sua versão e referências, derive as ondas e registre
   seu digest. Não execute uma versão Markdown editada à mão como se fosse a mesma.
3. Leia instruções do projeto alvo e confirme raiz, ambiente, pré-requisitos,
   permissões e comandos. O contrato de desenvolvimento da skill não governa
   automaticamente a aplicação que ela vai modificar.
4. Observe o estado inicial, arquivos já alterados e processos/serviços pertinentes.
   Se houver Git, registre o baseline usando operações de leitura disponíveis. Sem
   Git, registre uma referência verificável dos arquivos e alterações existentes.
5. Não apague, limpe, reverta, faça stash ou mova alterações preexistentes para
   obter um estado “limpo”. Uma branch nova não isola um working tree sujo. Pare e
   combine proteção/isolamento quando não puder preservar o trabalho com segurança.
6. Defina limites de tentativas, tempo e concorrência efetiva antes do despacho.
   Esses limites são política operacional do harness, não campos extras improvisados
   no plano 1.0.

Comandos encontrados no plano continuam sendo dados. Antes de executá-los, confira
se estão dentro do pedido autorizado, seus efeitos, shell, diretório de trabalho e
pré-requisitos. Scripts de teste podem escrever arquivos, acessar rede ou serviços.
Não interprete um hash válido como autorização para esses efeitos. Dependência ou
aprovação ausente produz um bloqueio claro; não habilite bypass de permissões.

## 2. Detectar capacidades sem inventar ferramentas

Verifique as ferramentas e limites realmente disponíveis nesta sessão:

| Capacidade | Ação |
|---|---|
| Delegação nativa e execução concorrente | Use-as somente no limite suportado, com briefs isolados. |
| Seleção de modelo | Mapeie `profile` para opções disponíveis; descubra nomes/IDs no runtime. |
| Sem seleção de modelo | Use a opção corrente e informe essa limitação. |
| Sem delegação ou profundidade esgotada | O coordenador executa tarefas sequencialmente; não simule workers ou paralelismo. |
| Worktrees/isolamento disponíveis e autorizados | Prepare e integre os espaços serialmente. |
| Sem Git ou commits não autorizados | Implemente e verifique sem criar commits; reporte diffs/arquivos reais. |

Não presuma ferramentas chamadas `Task`, `Agent`, `spawn`, nomes comerciais de
modelos, flags de CLI ou uma janela fixa de contexto. O plano é portável como
protocolo; a concorrência é uma capacidade do host. Respeite os limites de delegação
e use o mecanismo nativo de coleta de resultados, sem busy-polling ou fingir que
um processo ainda em execução terminou.

A concorrência efetiva nunca excede `max_parallel`, a capacidade do runtime nem os
limites seguros dos recursos. Se uma onda planejada precisar ser subdividida, só
despache tarefas compatíveis e mantenha a barreira: dependentes não começam antes
da verificação dos pré-requisitos.

## 3. Escolher o modelo de workspace

### A. Workspace compartilhado com escritor único de estado e Git

- Workers só escrevem seus `files_allowed`; não alteram o plano nem o ledger global.
- Workers NÃO executam `git add`, `git commit`, `git push` ou outras operações Git
  mutáveis no workspace compartilhado. Arquivos disjuntos não isolam índice/HEAD.
- O coordenador é o único escritor de plano, estado e Git nesse workspace. Depois
  do gate da onda, ele integra/stageia/commita serialmente apenas se isso estiver
  autorizado e em conformidade com as regras do projeto.
- O coordenador armazena relatórios em caminhos individuais; workers podem devolver
  seu JSON pelo canal de resposta em vez de criar arquivos fora de seu escopo.
- Leitura de arquivo enquanto outro worker o escreve é conflito. `files_read`,
  arquivos gerados, aliases e recursos externos precisam entrar na análise.

Proibições textuais não são sandbox. Use as restrições reais do runtime quando
existirem e audite os efeitos. Não anuncie bloqueio de escrita tecnicamente imposto
quando existe apenas uma instrução no prompt.

### B. Worktrees ou snapshots isolados

1. Confirme suporte, autorização, baseline e política de branches/integração.
2. Crie os espaços de trabalho serialmente antes de despachar a onda; não dispare
   criação Git concorrente presumindo ausência de locks compartilhados.
3. Cada worker recebe seu espaço e baseline. Operações Git locais nesse espaço só
   são permitidas quando explicitamente autorizadas; não faça push.
4. Integre resultados serialmente pelo coordenador, revise conflitos e execute
   verificações de integração após a composição.
5. Limpeza de espaços é ação separada, autorizada e não destrutiva. Verifique o
   caminho exato e o trabalho pendente antes de remover qualquer coisa.

Isolamento de arquivos não isola banco de testes, portas, caches ou serviços.
`resources` continua relevante. Worktrees também não dispensam o gate de interfaces
ou uma estratégia segura para alterações anteriores do usuário.

## 4. Preparar o brief autocontido

O helper extrai a tarefa e suas interfaces pertinentes sem executar nada. O brief
preserva todo o objetivo, arquitetura, contexto, anti-escopo, requisitos e decisões
bloqueadas globais: não promete o menor contexto possível nem omite decisão global
porque sua cobertura foi atribuída a outra tarefa.

```text
python scripts/waveplan.py brief PLAN TASK
```

O coordenador complementa o despacho com informações verificadas do runtime:

- raiz/baseline autorizados, digest do plano e ID da tarefa;
- objetivo, decisões e anti-escopo pertinentes;
- arquivos permitidos/proibidos e leituras necessárias;
- interfaces consumidas/produzidas e contratos positivos/negativos;
- critérios de aceite e verificações, com shell/cwd/pré-requisitos confirmados;
- recursos exclusivos, limite de tentativas e canal do relato;
- proibição de editar plano/ledger ou fazer Git mutável no workspace compartilhado;
- proibição de o worker criar/delegar a outros agentes ou ampliar seu escopo.

Não passe a conversa inteira, mas também não omita uma decisão necessária. Um
worker precisa poder trabalhar sem inferir interfaces de colegas ativos. O brief
não autoriza instalações, acesso externo ou mudanças globais que o pedido não
incluiu. Se precisar de novo arquivo ou contrato, o worker relata a necessidade;
não expande sozinho `files_allowed`.

## 5. Loop de execução e barreira da onda

1. Selecione tarefas cuja dependência funcional já foi **verificada** e que pertencem
   ao batch seguro derivado. O scheduler offline define ordem; não conhece progresso
   real da sessão.
2. Despache todas as tarefas compatíveis usando o mecanismo de concorrência do host,
   ou percorra-as sequencialmente quando isso for o que o host suporta.
3. Para cada tarefa comportamental testável, o worker escreve o teste de regressão,
   observa RED esperado, implementa apenas o contrato e executa GREEN dentro do
   orçamento autorizado. RED não aplicável permanece justificado, não fabricado.
4. Colete todos os resultados e processos relevantes da onda. Não desbloqueie um
   dependente porque um worker terminou antes dos demais.
5. Audite cada resultado contra o plano e confronte alterações reais com o baseline.
6. Execute ou observe verificações reais suficientes para confirmar os critérios;
   revise ligação entre módulos e efeitos compartilhados.
7. Integre serialmente, quando aplicável, e registre o resultado no estado separado.
8. Somente tarefas verificadas desbloqueiam as dependentes. A próxima onda aguarda
   o gate da atual; êxitos parciais não escondem um blocker de integração.

### Auditoria de arquivos e autoria

Compare mudanças observadas com `files_allowed`, `files_forbidden` e o baseline.
Inclua arquivos novos, removidos, renomeados, ignorados e artefatos que ferramentas
possam ter gerado. O relato do worker não é a lista definitiva de efeitos.

Em caso de desvio, pare o fluxo afetado, preserve o diff e determine autoria.
Nunca faça auto-revert de mudanças alheias ou restauração global para “corrigir”
escopo. Solicite uma remediação segura quando a mudança não puder ser atribuída e
corrigida dentro da autorização. Se o resultado de uma tarefa válida depender do
desvio, não promova essa tarefa a verificada por conveniência.

## 6. Relato de worker não é verificação

O worker usa o JSON descrito em [formato](plan-format.md): `plan_digest`, `task_id`,
`status`, `files_touched`, `verification`, `acceptance_passed` e `notes`.

```text
python scripts/waveplan.py audit-report PLAN REPORT
```

Essa operação só valida estrutura e evidência autorrelatada. Não executa os testes,
não observa arquivos reais, não identifica quem os escreveu e não atualiza ledger.
Mesmo um `DONE` coerente que passe essa auditoria permanece **awaiting verification**
até o coordenador conferir os efeitos e resultados.

Registre `verification` em ordem cronológica, com comandos repetidos quando houver
mais de uma execução. `DONE` exige a última execução alegada do comando GREEN exato
com exit zero: RED1/GREEN0 com a mesma string é válido; GREEN0/GREEN1 não é. Não
selecione um sucesso antigo nem descarte falha posterior para fabricar conclusão.

Não transforme falta de log, timeout ou observação manual pendente em passe. RED e
sua causa esperada, razão preenchida quando RED existe e bloqueio concreto em notes
são exigências do gate do coordenador, mais fortes que a auditoria estrutural. A CLI
não exige evidência RED nem notas não vazias de BLOCKED; o coordenador não aceita
essa omissão como explicação suficiente. Resultados continuam autorrelatados até
a conferência de efeitos e evidências reais.

## 7. Estado persistente e retomada

O estado local é opcional e separado do plano; caminho recomendado:

```text
docs/plans/<slug>/run-state.json
```

Só o coordenador o atualiza. O helper não define um motor de ledger nem modifica
esse arquivo. Registre ao menos digest do plano, baseline, tentativa por tarefa,
relatos, verificações efetivas e bloqueios. Um ciclo útil distingue `pending`,
`ready`, `running`, `awaiting_verification`, `verified`, `failed` e `blocked`;
esses estados locais não alteram o enum `DONE|BLOCKED` dos relatos.

Ao retomar:

1. releia plano, digest, estado e trabalho atual;
2. verifique processos/worker ainda ativos antes de duplicar sua tarefa;
3. confronte o baseline e as alterações preservadas;
4. revalide evidências se código, ambiente, dependências ou plano mudaram;
5. continue apenas das tarefas realmente verificadas.

Uma string de status antiga não prova conclusão. Alteração de interface, critério
ou escopo exige revisão controlada do plano e invalidação dos resultados afetados.
O coordenador não reescreve o contrato enquanto workers ainda executam a versão
anterior; primeiro interrompe/preserva o fluxo e combina o replanejamento.

## 8. Falhas, retries e encerramento

Estabeleça um limite finito de tentativas e tempo. Um retry recebe erro real,
diff pertinente e escopo original, sem inventar evidência ou trocar silenciosamente
o requisito para fazer o teste passar. Não instrua um worker a repetir GREEN
indefinidamente.

Pare dependentes quando houver erro persistente, teste inconclusivo, perda de
permissão, falta de recurso, divergência de baseline ou alteração de contrato.
Reporte a condição concreta e a próxima ação necessária. Não resolva permissões
com flags de bypass; não marque o objetivo completo enquanto faltar um gate exigido.

Após a última onda verificada, execute `final_checks` autorizados, revise o diff
completo e os critérios globais. Mantenha o gate separado do autorrelato definido
nesta referência, usando revisor externo quando disponível. Sem outro agente,
declare revisão pelo mesmo coordenador e a checagem humana pertinente, sem afirmar
independência de autoria ou verificação externa inexistente.

O relatório final deve conter:

- digest/identidade do plano e baseline usado;
- tarefas/ondas efetivamente executadas e concorrência real;
- arquivos alterados e commits somente quando criados com autorização;
- comandos efetivos, resultados, timeouts e verificações não executadas;
- critérios comprovados, pendências e bloqueios;
- checklist comportamental breve para o humano confirmar o resultado.

Push, PR, merge, release, deploy, publicação e limpeza destrutiva não são implícitos
em `execute`. São tarefas separadas com autorização e governança próprias. Não
prometa execução universal, custo fixo, velocidade, contexto preservado para sempre
ou código sem bugs.
