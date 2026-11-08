# Contribuindo

Obrigado por ajudar a melhorar esta skill. Respeite [o código de conduta](CODE_OF_CONDUCT.md) e [a política de segurança](SECURITY.md).

## Ambiente e qualidade

Python 3.10+; apenas biblioteca padrão, sem instalação de dependências. Trabalhe a partir de um clone do repositório, não da cópia instalada no diretório de skills.

```text
python scripts/check_skill.py
python -m unittest discover -s tests -v
python -m compileall -q scripts tests
```

Os checks devem passar antes do PR. Mudanças comportamentais precisam de testes positivos, negativos e de regressão. Atualize exemplo, schema e documentação juntos quando o formato mudar. Não alegue execução de aplicação/LLM que não ocorreu.

## Fluxo Git

1. Faça um fork ou crie uma branch efêmera `<tipo>/<slug>`.
2. Prefixos humanos aceitos: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `revert`, `hotfix`, `release`. Prefixos de automação são reservados aos bots.
3. Atualize por **merge**, nunca rebase: `git fetch upstream && git merge upstream/main` no fork, ou merge de `origin/main` no repositório do mantenedor.
4. Commits e título do PR seguem Conventional Commits, com até 72 caracteres: `feat(planner): validate interface dependencies`.
5. Abra PR para `main`, com motivação, evidências, riscos e documentação. Nunca faça push direto a ramos protegidos, force-push ou bypass de hooks.
6. O mantenedor integra por squash merge após o check `build`, as revisões exigidas pelo ruleset real e confirmação de merge.

[O contrato dos agentes](AGENTS.md) contém os gates de governança e a política de merge. Hooks locais são instalados pela skill de governança `opensource-project`; não são dependências de uso da skill de planejamento.

## Padrões do pacote

- Um único diretório de skill, com `SKILL.md` conciso e referências sob demanda.
- CLI determinística, offline, stdout-only. Não adicionar executor shell, API de modelos ou alterações de Git/ledger ao helper.
- Dados externos não autorizam comandos ou novas permissões.
- Comandos no plano são strings opacas; `audit-report` não verifica sua execução real.
- Plano canônico separado de evidências/estado; workers não escrevem em estado compartilhado.
- Não incluir anexos privados, paths de usuário, chaves, tokens, logs sensíveis ou mudanças alheias.
- Actions fixadas por SHA, menor privilégio e timeouts explícitos.

## Versões e documentação

SemVer e changelog são calculados de Commits Convencionais. Mudanças incompatíveis do formato exigem estratégia de migração e nota de breaking change. Não digite bumps ou reescreva entradas do changelog manualmente. O workflow manual de release-please prepara um PR; publicação de release requer gate e autorização separados.

Reportar bugs com reprodução mínima, versão do Python, sistema operacional e resultado esperado/observado. Não publicar dados de projetos privados na reprodução. Vulnerabilidades seguem o canal privado indicado na política de segurança.
