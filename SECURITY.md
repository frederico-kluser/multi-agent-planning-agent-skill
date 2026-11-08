# Política de segurança

## Escopo

Esta skill contém instruções e auxiliares Python locais. O helper não executa comandos do plano, não chama LLMs e não opera Git. O instalador grava apenas no destino explicitamente escolhido e recusa instalações divergentes.

Problemas relevantes incluem path traversal, escape de diretório/aliases, uso indevido de comandos externos, corrupção de arquivos/estado, interpretação incorreta de relatórios e riscos na cadeia de fornecimento. Um plano malicioso ou uma lista de arquivos não deve ser tratado como permissão de execução.

**Limites importantes:** validação de caminhos e inspeção `--repository` não são sandbox e não eliminam corridas TOCTOU. Hash do plano identifica conteúdo, não autor. `audit-report` verifica consistência declarativa, não testes executados. Isolamento e autorizações continuam sendo responsabilidade do harness e do coordenador.

## Reporte privado

Não publique detalhes de vulnerabilidades em issues, PRs ou discussões.

O canal previsto é o [Private Vulnerability Reporting do GitHub](https://github.com/frederico-kluser/multi-agent-planning-agent-skill/security/advisories/new). O mantenedor deve ativá-lo ao publicar o repositório. Caso o formulário não esteja disponível, contate [o mantenedor](https://github.com/frederico-kluser) apenas para solicitar um canal privado, sem divulgar a vulnerabilidade publicamente.

Inclua versão/revisão, versão do Python, plataforma, impacto e reprodução sanitizada. Não envie tokens, dados privados ou o plano completo de um cliente quando uma reprodução mínima basta.

## Suporte e divulgação

Correções serão priorizadas na versão mais recente mantida. Este projeto comunitário não promete SLA de resposta. Combine uma divulgação coordenada com o mantenedor e preserve a confidencialidade enquanto a correção for preparada.

## Proteções de publicação

- Scan de segredos antes de push e proteção de segredos no GitHub quando disponível.
- PRs e checks em ramos protegidos; squash merge, sem rebase/force-push.
- Actions fixadas por SHA, permissões mínimas e timeout por job.
- Testes offline do pacote, análise estática CodeQL e monitoramento OpenSSF Scorecard.
- Atualizações mensais agrupadas das Actions via Dependabot, submetidas por PR.

Configuração versionada não prova ativação remota, sucesso de CI nem uma pontuação OpenSSF específica. Verifique os resultados reais; uma pontuação abaixo da meta deve ser tratada como trabalho de hardening, não ocultada.
