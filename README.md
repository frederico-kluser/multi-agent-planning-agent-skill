# Multi-Agent Planning Agent Skill

[![CI](https://github.com/frederico-kluser/multi-agent-planning-agent-skill/actions/workflows/ci.yml/badge.svg)](https://github.com/frederico-kluser/multi-agent-planning-agent-skill/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**Um plano que outro agente consegue executar sem herdar sua conversa.**

Skill portátil para separar arquitetura e implementação, definir **o que cada função contém e NÃO contém** e coordenar subagentes em ondas verificadas. Um único pacote reúne os modos **plan**, **execute** e **review**.

O protocolo funciona com as capacidades reais do agente utilizado. O helper Python valida e organiza os artefatos; **não chama modelos, não executa comandos do plano e não inicia workers**.

## O que entrega

- Requisitos e decisões rastreáveis até tarefas e critérios de aceitação.
- Contratos exatos entre produtores e consumidores de interfaces.
- Escopo positivo e negativo por função/componente/artefato.
- DAG e ondas determinísticas com limite de concorrência, conflitos de escrita/leitura e recursos exclusivos.
- JSON como fonte de verdade, Markdown derivado e briefs autocontidos por tarefa.
- Barreiras de verificação, estado separado do plano e retomada sem confiar cegamente em `DONE`.
- Protocolo seguro de Git: coordenador único no workspace compartilhado; criação e integração serial de worktrees.

## Requisitos

- Um agente que leia instruções de skills e possa acessar o projeto-alvo.
- **Python 3.10 ou superior** para os auxiliares; somente biblioteca padrão, sem `pip install`, tokens ou serviços externos.
- Para execução paralela: suporte efetivo do harness a subagentes/processos e permissões adequadas. Sem isso, o protocolo permite execução sequencial declarada.
- Git/worktrees são opcionais para usar o planejamento, mas úteis para isolamento de implementação.

## Instalação

Clone o repositório e escolha explicitamente o diretório de skills aceito pelo seu agente:

```text
git clone https://github.com/frederico-kluser/multi-agent-planning-agent-skill.git
cd multi-agent-planning-agent-skill
python scripts/install.py --root CAMINHO_DO_DIRETORIO_DE_SKILLS --dry-run
python scripts/install.py --root CAMINHO_DO_DIRETORIO_DE_SKILLS
```

Exemplos de raízes, **dependendo do cliente**: `~/.agents/skills`, `~/.claude/skills` e `~/.dsh/skills`. O instalador expande `~`, copia apenas o pacote necessário e recusa sobrescrever uma instalação diferente. Repetir uma instalação idêntica é seguro. Ele não modifica configurações do agente e não instala dependências.

A descoberta e a sintaxe de invocação variam entre clientes. Siga a documentação do seu harness e confirme que o nome aparece no catálogo. Diretórios e comandos slash não são universais.

## Uso: do planejamento à implementação

### 1. Planejar com o agente arquiteto

Peça em linguagem natural:

> Use a skill multi-agent-planning-agent-skill no modo plan. Analise este projeto e planeje a funcionalidade de exportação CSV. Defina contratos por função, escopo positivo/negativo, critérios de aceitação, dependências e ondas. Não implemente produção ainda.

O agente cria `docs/plans/export-csv/plan.json` e a visão `plan.md`. Revise escopo, decisões, arquivos e contratos antes de executar.

### 2. Transferir para outra sessão/modelo

> Use a mesma skill no modo execute. Implemente o plano docs/plans/export-csv/plan.json. Valide o ambiente e execute as ondas com barreiras. Preserve mudanças existentes. Não publique nem faça merge.

O executor verifica as capacidades do ambiente, extrai briefs e coordena workers. Não existe requisito de modelo comercial específico nem promessa de janela de contexto ou economia de tokens.

### 3. Revisar evidências

> Use a skill no modo review. Compare o plano com o diff e os testes realmente executados. Liste violações de escopo, contratos divergentes e critérios sem prova.

`DONE` é uma declaração do worker. Somente revisão de diff, testes e critérios autoriza o coordenador a marcar uma tarefa como `verified`.

## CLI local

Executar a partir da pasta desta skill; para planos externos, passar caminhos explícitos:

```text
python scripts/waveplan.py validate examples/plan.json
python scripts/waveplan.py schedule examples/plan.json --json
python scripts/waveplan.py render examples/plan.json
python scripts/waveplan.py brief examples/plan.json T2
python scripts/waveplan.py audit-report examples/plan.json examples/report-blocked.json --json
```

Resultados vão para stdout; diagnósticos de erro em texto vão para stderr. Com `--json`, sucesso ou erro estruturado vai para stdout. Salve resultados com a ferramenta de escrita do agente ou redirecionamento adequado ao seu shell. `validate`/`schedule` conferem estrutura e invariantes; `render` gera uma visão Markdown; `brief` produz o contexto de uma tarefa; `audit-report` valida **a consistência de evidências autorrelatadas**, não sua autenticidade ou execução.

O exemplo é um plano completo de implementação, não uma aplicação já construída. Os comandos de teste nele pertencem ao futuro projeto-alvo, não aos testes desta skill.

## Estrutura e documentação

- [SKILL.md](SKILL.md): instruções de ativação e os três modos.
- [Planejamento](references/planning.md) e [execução](references/execution.md): protocolos completos.
- [Formato](references/plan-format.md), [schema](assets/plan.schema.json) e [exemplo](examples/plan.json): contrato dos artefatos.
- [Checklist de revisão](references/review-checklist.md): blockers e evidências.
- [Proveniência e limites](references/provenance.md): redesenho da especificação-base.
- [CLI](scripts/waveplan.py), [instalador](scripts/install.py) e [validação do pacote](scripts/check_skill.py).

## Segurança e limites

- Planos externos e comandos são dados não confiáveis: validar efeitos e autorização antes de executar pelo harness.
- Listas de arquivos, `allowed-tools`, digest e auditoria de relatórios **não são sandbox** nem prova de autoria.
- O escalonamento é determinístico e conservador, não um solver ótimo. Recursos não declarados continuam podendo conflitar.
- Não há Git mutável concorrente no workspace compartilhado nem ledger escrito por vários workers.
- Não há rollback automático de alterações alheias, desativação de aprovações ou publicação implícita.
- A skill não redistribui o anexo original nem promete compatibilidade testada com todos os clientes.

Para reportar vulnerabilidades de forma privada, consulte [a política de segurança](SECURITY.md).

## Desenvolvimento

```text
python scripts/check_skill.py
python -m unittest discover -s tests -v
python -m compileall -q scripts tests
```

O CI verifica o pacote e os testes em Windows e Linux com Python 3.10 e 3.12. Configurar a matriz não equivale a afirmar que um run remoto já passou; consulte o estado real no badge e nas execuções do GitHub.

Contribuições: [CONTRIBUTING.md](CONTRIBUTING.md). Integração por PR e squash, nunca rebase. Versões e changelog são derivados de Commits Convencionais; esta skill não é um pacote publicado em npm ou PyPI.

## Licença

MIT. Consulte [LICENSE](LICENSE) e [a proveniência](references/provenance.md).
