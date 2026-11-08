# Formato do plano e do relatório — versão 1.0

Esta referência define o contrato transferível entre os modos `plan`, `execute` e
`review`. O JSON é a fonte de verdade. O Markdown é uma visualização derivada, não
um segundo plano editável. Estado de execução e relatos dos workers ficam fora do
plano. Consulte [planejamento](planning.md), [execução](execution.md) e
[checklist de revisão](review-checklist.md) para os procedimentos.

## 1. Arquivos e identidade

Organização recomendada no projeto alvo, criada apenas com autorização:

```text
docs/plans/<slug>/
  plan.json                 # contrato canônico
  plan.md                   # renderização do mesmo JSON
  run-state.json            # opcional; coordenador é o único escritor
  reports/
    <task-id>-<attempt>.json # relatos individuais, sem edição do plano
```

O caminho é uma convenção, não um requisito de instalação. Não embuta caminhos
absolutos da máquina, segredos, tokens nem histórico integral de conversa no plano.
Os caminhos das tarefas são relativos à raiz do projeto alvo, não à pasta da skill.
Uma nova sessão precisa do plano e dos arquivos de referência declarados, não da
conversa que o originou.

`schema_version` é a string `"1.0"`. `plan_id` identifica o plano. Qualquer mudança
no contrato, nas verificações ou na ordem das tarefas gera outro digest e exige
nova revisão dos resultados afetados. `plan_id` sozinho não prova que dois planos
são idênticos.

### Digest canônico

A canonicalização desta versão é definida pelo seguinte algoritmo Python, usando
somente a biblioteca padrão:

```python
import hashlib
import json

canonical = json.dumps(
    plan,
    sort_keys=True,
    separators=(",", ":"),
    ensure_ascii=False,
    allow_nan=False,
).encode("utf-8")
plan_digest = hashlib.sha256(canonical).hexdigest()
```

Não acrescente newline antes de calcular o hash. Espaços e ordem de chaves no
arquivo original não alteram o digest; a ordem dos arrays altera. Em particular,
reordenar `tasks` pode mudar tanto o digest como o escalonamento. Não aplique
normalização Unicode adicional nem use `NaN`/`Infinity`. O digest vincula um relato
aos dados do plano; não é assinatura, autenticação do worker ou prova de execução.

## 2. Campos do plano

Todos os campos abaixo são explícitos e obrigatórios no contrato 1.0; objetos são
fechados e campos desconhecidos são rejeitados. Arrays vazios só são adequados nas
categorias que os permitem. Não acrescente status, commits ou logs ao plano para
simular progresso; consulte a tabela de limites nesta seção.

| Campo | Tipo e significado |
|---|---|
| `schema_version` | String `"1.0"`. |
| `plan_id`, `title`, `goal`, `architecture` | Strings não vazias: identidade, título, resultado observável e desenho/fluxo de dados. |
| `max_parallel` | Inteiro de 1 a 5; limite solicitado, não promessa de capacidade do harness. |
| `context.stack` | Array de strings com tecnologias e convenções relevantes. |
| `context.test_runner` | String identificando o executor de testes/verificações do projeto. |
| `requirements` | Array de `{id, text}` com requisitos rastreáveis. |
| `decisions` | Array de `{id, text}` com decisões efetivamente resolvidas. |
| `anti_scope` | Array de strings com limites globais e ideias explicitamente adiadas. |
| `interfaces` | Array de `{id, producer, file, signature}` com contratos compartilhados. |
| `tasks` | Array ordenado de tarefas; essa ordem desempata o escalonamento. |
| `final_checks` | Array de `{command, timeout_seconds}` para verificações globais realizadas pelo harness. |

Os IDs precisam ser únicos dentro de suas categorias e todas as referências
precisam existir. Recomenda-se `R-01`, `D-01`, `INT-01`, `T1` e `AC-T1-1`, sem
atribuir significado mágico aos prefixos. Um requisito ou decisão obrigatória deve
estar coberto por ao menos uma tarefa. Não declare decidido o que ainda depende do
usuário: resolva antes de entregar um plano executável ou relate o bloqueio fora
do plano.

### Campos de cada tarefa

| Campo | Contrato |
|---|---|
| `id`, `title` | ID estável e título orientado a ação. |
| `depends_on` | Array de IDs de tarefas; `[]` para raízes. Sem autorreferência ou ciclos. |
| `profile` | `fast-mechanical`, `standard-implementer` ou `deep-specialist`. É perfil de capacidade, não nome obrigatório de modelo. |
| `files_allowed` | Arquivos exatos que a tarefa pode criar/modificar/remover, incluindo testes e configurações atribuídas. |
| `files_forbidden` | Arquivos exatos ou diretórios terminados em `/` que a tarefa não pode escrever. |
| `files_read` | Arquivos exatos cuja leitura é necessária; explicita conflitos com escritas de outras tarefas. |
| `resources` | Array de nomes de locks lógicos exclusivos: banco de testes, porta, cache, gerador ou serviço compartilhado. |
| `functions` | Array de contratos `{name, file, signature, contains, does_not_contain}`. |
| `consumes` | Array de `{interface, signature}`; a assinatura deve ser a registrada para esse ID. |
| `produces` | Array de IDs de interfaces produzidas pela tarefa. |
| `requirement_ids`, `decision_ids` | Arrays de IDs cobertos pela tarefa. |
| `acceptance` | Array de `{id, text}` com critérios observáveis e identificáveis. |
| `verification.red` | `{command, timeout_seconds}` ou `null`, conforme aplicabilidade de TDD. |
| `verification.red_reason` | String explicando a falha esperada ou por que RED não se aplica. |
| `verification.green` | `{command, timeout_seconds}` com verificação de conclusão. |

### Limites efetivamente validados nesta versão

| Categoria | Limite/regra |
|---|---|
| Entrada PLAN/REPORT | Arquivo local regular, UTF-8 sem BOM, até 2 MiB e 64 níveis de nesting; sem chaves JSON duplicadas ou valores não finitos. |
| Objetos e strings | Campos explícitos, sem extras; strings até 20.000 caracteres, não vazias salvo a exceção de `red_reason`; controles proibidos exceto tab/CR/LF, sem surrogates ou bidi overrides. |
| IDs gerais | De 1 a 64 caracteres ASCII: começam por letra e usam letras, dígitos, `_` ou `-`. IDs de aceite são únicos globalmente entre tarefas. |
| `plan_id` | De 1 a 64 caracteres ASCII minúsculos/dígitos/hífens, começando por letra minúscula ou dígito; distinto do `name` de uma skill. |
| Arrays obrigatoriamente não vazios | `context.stack`, `requirements`, `anti_scope`, `tasks`, `final_checks`; por tarefa, `files_allowed`, `functions`, `acceptance`; por contrato, `contains`, `does_not_contain`. |
| Tamanho dos arrays | Até 500 tarefas; arrays em geral até 2.000 entradas. `decisions`, `interfaces` e listas sem mínimo podem ser vazias quando adequado; referências globais declaradas continuam exigindo cobertura. |
| Duplicatas | IDs/listas de strings e caminhos não se repetem; contratos são únicos por `(file, name)` e `final_checks` por `command`. Exceção: `report.verification` é histórico cronológico e permite comandos repetidos. |
| Números | `max_parallel`: inteiro 1..5; timeout RED/GREEN: inteiro 1..60 segundos; timeout final: inteiro 1..3600 segundos. Booleanos não contam como inteiros. |
| Exit code relatado | Inteiro entre -2147483648 e 2147483647, sem converter ausência de execução em zero. |

`red_reason` é estruturalmente obrigatório e não pode ser vazio quando RED é `null`.
O helper aceita string vazia quando RED existe, mas a política desta skill exige
explicar a falha esperada; isso pertence à revisão, não a uma garantia do validador.
Os limites de timeout são escolhas do contrato, não medições ou promessas de rapidez.

`command` é uma string de dados: documentá-la não a autoriza e o helper nunca a
executa. O harness confirma shell, diretório de trabalho, pré-requisitos e efeitos.
Não há expansão universal de sintaxe entre Bash, PowerShell e outros ambientes.

### Contratos de funções, tipos e artefatos

Cada tarefa declara ao menos um contrato em `functions`. O array abrange funções,
componentes, tipos ou **artefatos**. `file` corresponde exatamente a `files_allowed`,
inclusive spelling. Para funções, `signature` explicita parâmetros e retorno;
para tipos/artefatos, descreve a estrutura ou formato esperado. `contains` declara
lógica/regras/elementos obrigatórios e `does_not_contain` limites concretos, ambos
não vazios. Não altere interfaces públicas sob o pretexto de detalhe interno.

Para documentação/configuração sem funções de produção, represente o artefato em
`functions`: `name` identifica o artefato, `file` é seu caminho permitido e
`signature` descreve o formato, sem inventar uma função para preencher o contrato.
Exemplo de entrada de contrato, a ser inserida no array da tarefa correspondente:

```text
{
  "name": "artefato de documentação",
  "file": "docs/usage.md",
  "signature": "Markdown UTF-8 com seções Objetivo, Instalação e Limitações",
  "contains": ["Documentar os modos plan/execute/review e seus efeitos."],
  "does_not_contain": ["Não embutir credenciais ou caminhos pessoais."]
}
```

Cada interface tem um produtor existente que a declara em `produces`. Seu `file`
e `signature` correspondem a exatamente um contrato em `functions` desse produtor;
dois matches com o mesmo arquivo e assinatura tornam o registro ambíguo. O
consumidor declara o mesmo ID e assinatura, depende direta ou transitivamente do
produtor e inclui o arquivo em `files_read` ou `files_allowed`. Assinaturas são
comparadas character-for-character; testes e integração continuam necessários.
Não inferir dependência funcional apenas porque duas tarefas usam o mesmo arquivo.

### Caminhos e recursos

- Use caminhos relativos com `/`, sem absoluto, unidade/colon/ADS, backslash, `.` ou
  `..`, componentes vazios, globs ou caracteres reservados `<>:"|?*[]`.
- Componentes `.git`, nomes reservados DOS mesmo com extensão, controles e nomes
  terminados em espaço/ponto são rejeitados por portabilidade.
- `files_allowed` e `files_read` enumeram arquivos exatos. Diretórios em
  `files_forbidden` terminam em `/` e proíbem seus descendentes; permitido e proibido
  não podem se sobrepor na mesma tarefa.
- A chave conservadora de comparação de caminhos usa NFC + casefold. Spellings
  diferentes que produzam a mesma chave são rejeitados globalmente, assim como
  caminho simultaneamente arquivo/diretório ou com ancestral declarado como arquivo.
  Essa comparação NÃO normaliza o conteúdo JSON usado no digest.
- Conte escritas em testes, lockfiles, barrels, geradores e artefatos versionados;
  não esconda efeitos sob a expressão “rodar os testes”. `resources` usa identidades
  compartilhadas consistentes, comparadas como strings exatas, não locks do SO.
- `--repository` observa read-only escapes, aliases/symlinks/hard links e tipos dos
  caminhos atuais. Isso não impõe sandbox nem garante ausência de TOCTOU. O harness
  reconfirma caminhos reais e efeitos antes/durante a execução; a inspeção offline
  não limita permissões de escrita de nenhum processo.

## 3. Escalonamento derivado, não editado manualmente

`wave` não é campo do JSON 1.0: não o acrescente às tarefas. O helper deriva as ondas
a partir do DAG, da ordem original de `tasks`, do cap e dos conflitos declarados.

1. No início da onda, encontre as tarefas ainda não escalonadas cujos pré-requisitos
   pertencem a ondas anteriores.
2. Percorra esse conjunto na ordem original do array `tasks`.
3. Selecione até `max_parallel` tarefas que não conflitem com as já selecionadas.
   Uma candidata em conflito fica para onda posterior; outras compatíveis ainda
   podem preencher a onda.
4. Só após fechar a onda suas tarefas passam a contar como pré-requisitos satisfeitos
   para o escalonamento da próxima. Um dependente nunca entra na mesma onda que
   seu produtor, mesmo que ainda haja uma vaga.

Há conflito entre duas tarefas quando elas escrevem o mesmo arquivo, quando uma
escreve arquivo que a outra lê, ou quando compartilham um lock em `resources`.
Leituras entre si não conflitam. O scheduler não inventa `depends_on` para justificar
a serialização: dependência funcional e impedimento operacional são conceitos
separados.

`1 + max(onda dos pré-requisitos)` é somente um limite inferior. Cinco raízes sem
conflitos, com `max_parallel: 2`, ocupam três ondas; não cabem todas na onda 1.
O algoritmo estável não é um solver de mínimo global de tempo. Uma ordem diferente
pode produzir outra distribuição válida. Durante execução, “escalonado” não é
“verificado”: a barreira real continua obrigatória.

## 4. Exemplo completo de plano

Este exemplo pressupõe um projeto Python com uma função existente que ainda não
remove espaços externos. O planejador precisa conferir essa hipótese no projeto
real, criar testes de comportamento e manter os comandos adequados ao ambiente.

```json
{
  "schema_version": "1.0",
  "plan_id": "normalizar-rotulo",
  "title": "Normalização local de rótulos",
  "goal": "Aceitar rótulos não vazios sem espaços externos e rejeitar entradas inválidas.",
  "architecture": "Uma função pura existente normaliza a entrada. Testes unitários observam retorno, erros e ausência de mutação ou I/O.",
  "max_parallel": 1,
  "context": {
    "stack": ["Python", "biblioteca padrão", "funções puras"],
    "test_runner": "unittest"
  },
  "requirements": [
    {"id": "R-01", "text": "Remover somente espaços externos e rejeitar rótulos vazios ou entradas que não sejam strings."}
  ],
  "decisions": [
    {"id": "D-01", "text": "TypeError para entrada que não seja string; ValueError para string vazia após strip()."}
  ],
  "anti_scope": [
    "Não acessar rede ou disco na função.",
    "Não aplicar case folding, normalização Unicode ou cache.",
    "Não publicar nem enviar alterações ao remoto."
  ],
  "interfaces": [
    {"id": "INT-01", "producer": "T1", "file": "src/labels.py", "signature": "def normalize_label(value: str) -> str"}
  ],
  "tasks": [
    {
      "id": "T1",
      "title": "Ajustar normalize_label e seus testes unitários",
      "depends_on": [],
      "profile": "standard-implementer",
      "files_allowed": ["src/labels.py", "tests/test_labels.py"],
      "files_forbidden": ["infra/", "pyproject.toml"],
      "files_read": ["src/labels.py", "tests/test_labels.py"],
      "resources": [],
      "functions": [
        {
          "name": "normalize_label",
          "file": "src/labels.py",
          "signature": "def normalize_label(value: str) -> str",
          "contains": [
            "Verificar que value é string e lançar TypeError caso contrário.",
            "Calcular value.strip(); lançar ValueError se o resultado for vazio.",
            "Retornar o resultado mantendo espaços internos e capitalização."
          ],
          "does_not_contain": [
            "Não executar I/O nem alterar estado global.",
            "Não fazer coerção de objetos para string.",
            "Não transformar capitalização ou espaços internos."
          ]
        }
      ],
      "consumes": [],
      "produces": ["INT-01"],
      "requirement_ids": ["R-01"],
      "decision_ids": ["D-01"],
      "acceptance": [
        {"id": "AC-T1-1", "text": "Entrada '  Nome Composto  ' retorna 'Nome Composto'."},
        {"id": "AC-T1-2", "text": "Entrada vazia ou somente espaços lança ValueError; None e números lançam TypeError."},
        {"id": "AC-T1-3", "text": "Somente os arquivos permitidos foram modificados; a função não contém I/O ou estado global."}
      ],
      "verification": {
        "red": {"command": "python -m unittest discover -s tests -p test_labels.py", "timeout_seconds": 60},
        "red_reason": "Após escrever os testes, a função existente deve falhar no caso de espaços externos; falha de importação ou ambiente não comprova RED comportamental.",
        "green": {"command": "python -m unittest discover -s tests -p test_labels.py", "timeout_seconds": 60}
      }
    }
  ],
  "final_checks": [
    {"command": "python -m unittest discover -s tests", "timeout_seconds": 180}
  ]
}
```

Os tempos são limites configurados para o exemplo, não medições ou garantia de
conclusão. Não force RED se a inspeção mostrar que o comportamento já é correto;
revise a tarefa e documente a aplicabilidade antes da execução.

## 5. Formato do relato de worker

O relato é JSON separado e usa estes campos:

```text
plan_digest: string SHA256 hexadecimal do plano canônico
task_id: ID de uma tarefa do plano
status: DONE | BLOCKED
files_touched: array de caminhos exatos efetivamente escritos
verification: array de {command: string, exit_code: inteiro, summary: string}
acceptance_passed: array de IDs de critérios alegadamente satisfeitos
notes: array de strings com contexto, limites e bloqueios
```

`DONE` significa “o worker alega conclusão”. Não significa que o coordenador
verificou o diff, executou comandos ou comprovou os critérios. O relato precisa
identificar o plano exato, arquivos realmente tocados e resultados sem fabricar
logs ou converter verificação não executada em `exit_code: 0`.

`verification` é histórico cronológico: preserve a ordem das execuções e permita
comandos repetidos. Para alegar `DONE`, inclua todos os critérios da tarefa em
`acceptance_passed`; a **última execução alegada do comando GREEN exato** precisa
ter `exit_code: 0`. Com RED/GREEN usando a mesma string, falha 1 seguida de sucesso
0 é válida; sucesso 0 seguido de falha 1 não comprova conclusão. Não escolha uma
execução antiga bem-sucedida nem descarte uma falha posterior.

O helper verifica digest, estrutura, escopo alegado, IDs de aceite e a última
execução GREEN de `DONE`. NÃO impõe toda a política de execução: evidência RED e
sua causa esperada, `red_reason` preenchido mesmo quando RED existe e a condição
concreta de `BLOCKED` em `notes` pertencem ao gate do coordenador. Um relato BLOCKED
pode passar estruturalmente com evidência parcial ou notas vazias; isso não é uma
explicação de bloqueio suficiente para esta skill. Não omita critérios/verificações
para transformar pendência em sucesso.

`audit-report` NÃO lê diff para provar autoria, NÃO testa a aplicação e NÃO marca
a tarefa como verified. Mesmo um relato aceito requer o gate separado do autorrelato
pelo coordenador, com revisão externa quando disponível e fallback declarado quando
não houver outro agente; consulte [execução](execution.md).

## 6. CLI offline e fronteira de responsabilidade

Executar a partir da raiz da skill, ou substituir o caminho pelo local instalado:

```text
python scripts/waveplan.py validate PLAN
python scripts/waveplan.py schedule PLAN
python scripts/waveplan.py schedule PLAN --json
python scripts/waveplan.py render PLAN
python scripts/waveplan.py brief PLAN TASK
python scripts/waveplan.py audit-report PLAN REPORT
```

`PLAN` e `REPORT` são arquivos locais regulares UTF-8 sem BOM, dentro dos limites
[definidos acima](#2-campos-do-plano); `TASK` é um ID existente. O loader observa se o
arquivo mudou durante a leitura, sem constituir transação à prova de escritor hostil.

Os cinco subcomandos aceitam `--json` e `--repository`, antes ou depois do nome do
subcomando. Resultados vão para stdout; diagnósticos padrão de erro vão para stderr.
Com `--json`, sucesso/erro estruturado vai para stdout; `render`/`brief` devolvem um
objeto com `markdown`, não Markdown puro. Exit codes: 0 sucesso, 1 contrato inválido,
2 uso inválido, 3 falha de I/O de entrada/repositório.

A CLI não escreve planos, estado ou relatórios, não instala pacotes e nunca executa
comandos do plano, testes, Git ou APIs. Gravar stdout em arquivo é ação separada do
chamador, respeitando autorização, leitura do arquivo existente e escritor único.

A CLI valida/escalona/renderiza dados e extrai briefs. A aprovação, a capacidade de
delegar, a execução real, a inspeção de efeitos e a verificação da aplicação são
responsabilidades do harness e do coordenador, nunca efeitos implícitos de um
comando de validação.
