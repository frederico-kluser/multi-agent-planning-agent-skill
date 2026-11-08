# Contrato operacional — multi-agent-planning-agent-skill

Este arquivo governa o desenvolvimento do pacote, não a codebase onde a skill será utilizada. As instruções de uso ficam em [SKILL.md](SKILL.md). O contrato é espelhado em [CLAUDE.md](CLAUDE.md).

## Reentry e governança

O mantenedor deve carregar `opensource-project` e `github-agent-skill` antes de ações de ciclo de vida. Defina `OSS_SKILL_ROOT` como o caminho da instalação local de `opensource-project`; nenhum caminho pessoal é versionado.

```bash
bash "$OSS_SKILL_ROOT/scripts/oss-enforce.sh" --local
bash "$OSS_SKILL_ROOT/scripts/oss-doctor.sh" --local
```

Com remoto GitHub autorizado, remover `--local` para verificar/aplicar rulesets e proteção de segredos. Se a skill de governança ou uma ferramenta estiver ausente, informar a dependência e resolver antes de publicar; não simular um gate aprovado nem instalar globalmente sem autorização. Subagentes com escopo de escrita restrito não devem aplicar governança fora desse escopo: reportam ao coordenador, que executa a reentry.

<!-- oss:merge-policy:begin -->
## Política de integração: merge, nunca rebase

A integração é **merge**; rebase é proibido. Merge commit e squash merge são
merges — rebase não é.

- **Sincronizar a ramificação**: `git fetch origin && git merge origin/main` (ou
  `git pull`, que faz merge). **Nunca** `git rebase`, `git pull --rebase` nem
  `git rebase origin/main`.
- **Integrar o PR**: `gh pr merge --squash --delete-branch` no cofre (`main` é
  squash-only por ruleset; squash é merge e mantém o histórico linear). Onde o
  ruleset permitir, `gh pr merge --merge` também é merge; **rebase-merge nunca**.
- **PR desatualizado**: `gh pr update-branch` (merge) ou merge de `origin/main` na
  ramificação; depois `gh pr checks --watch`. Sem rebase e sem force-push.
- **Configuração imposta**: `oss-enforce.sh` deteta rebase no projeto
  (`pull.rebase`, `branch.*.rebase`, `allow_rebase_merge`, `allowed_merge_methods`)
  e corrige — `[CONFIGURADO]` — sem perguntar. Diagnóstico dedicado:
  `oss-merge-policy.sh check` (na instalação da skill).
<!-- oss:merge-policy:end -->

## Gates obrigatórios

1. Branches humanas: `<tipo>/<slug>`, tipos `feat fix docs style refactor perf test build ci revert hotfix release`; sem prefixos reservados para automação.
2. Commits e títulos de PR Convencionais, cabeçalho com até 72 caracteres; tipos de commit `feat fix docs style refactor perf test build ci chore revert`.
3. Rodar `oss-gate.sh commit-msg`, `branch`, `push`/`pr` e `merge` conforme a ação. Não contornar hooks nem usar `--no-verify`.
4. Versionamento SemVer calculado de commits; changelog gerado por `oss-changelog.py` ou release-please, nunca reescrito manualmente. Tags de release anotadas e imutáveis; publicação exige autorização e gate específico.
5. Actions fixadas por SHA, permissions mínimos, timeout em todo job e status check obrigatório `build`. Configuração versionada não comprova que proteções remotas estejam ativas; verificar o estado real.
6. Nenhum segredo, anexo privado, caminho pessoal, histórico de sessão ou output sensível no Git. Rodar scan de segredos antes do push. Nunca imprimir tokens.

## Arquitetura e qualidade

- Uma única skill na raiz; `name` coincide com o nome da pasta instalada.
- Python 3.10+ e stdlib. Não adicionar dependências, chamadas de LLM ou executor shell ao helper.
- Plano JSON canônico, Markdown derivado, estado de execução separado e escritor único.
- Workers no workspace compartilhado não fazem Git mutável nem escrevem no ledger global.
- `audit-report` valida autorrelato, não prova execução/autoria nem promove `DONE` a `verified`.
- Preservar trabalho existente; não apagar, limpar ou reverter automaticamente mudanças de terceiros.
- Cada mudança comportamental precisa de teste de regressão. Instruções de skill e exemplos também devem ter verificações estáticas e cenários de uso.

## Antes de concluir

```text
python scripts/check_skill.py
python -m unittest discover -s tests -v
python -m compileall -q scripts tests
```

Conferir reentry/doctor, links, schema/exemplo, instalador, contratos espelhados, pins, segredo scan, estado Git e evidência real do CI. Reportar mudanças, testes executados, limitações e URLs criadas. Merge/delete/release/publicação não são implícitos em uma implementação.

Erros dos gates: `Erro: <o que aconteceu> — Solução: <próxima ação>`. Não marcar tarefa ou objetivo concluído com blockers conhecidos ou publicação ainda pendente.
