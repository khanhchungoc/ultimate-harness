# Detective Wifey - Project Harness Rules

## Project Principles

- **No Em Dashes**: Never use em dashes in responses, code, documentation, or UI text. Use a hyphen (`-`) instead.
- **Code Changes Agent**: Always read and operate under [.agents/agents/frontend-game-developer.md](.agents/agents/frontend-game-developer.md) before and during any code modification.
- **Global Harness Assets**: Use global `Ponytail` rules from root `AGENTS.md` and global `ui-ux-pro-max`, `motion`, `ui-styling`, and `engineering-standards` skills from `ultimate-harness` (do not duplicate them here).
- **Project-Only Assets**: Project-specific agent and skills live in this folder (`.agents/agents/frontend-game-developer.md`, `.agents/skills/develop-virtual-app/`, `.agents/skills/research-project-knowledge/`). Sync them into the `detective-wifey` repository's `.agents/` when deploying project updates.

---

## Project Context Reference (in `detective-wifey` repo)

- **Runtime Code Ownership**: `.agent-artifacts/project-knowledge-base/solution-context/architecture/runtime-code-ownership.md`
- **Product**: *Bắt được Tiểu tam* (Jealous Wife Detective Game)
- **Project Summary**: `.agent-artifacts/project-knowledge-base/project-summary.md`
- **Requirements SSOT**: `.agent-artifacts/requirements/output/vision-scope.md`
- **Software Architecture SSOT**: `.agent-artifacts/project-knowledge-base/solution-context/architecture/apps-features-architecture.md`
- **Universal Design System SSOT**: `.agent-artifacts/project-knowledge-base/solution-context/design-system/design.md`
- **Micro-App Design SSOT**: `.agent-artifacts/project-knowledge-base/solution-context/apps/`
- **Story & Level Design SSOT**: `.agent-artifacts/requirements/stories/`

---

## Deployment (GitHub Pages)

Both branches deploy through `.github/workflows/deploy.yml` (`build` matrix -> `package` -> `deploy` to `github-pages` environment):

- **Staging (`stg`):** https://khanhchungoc.github.io/detective-wifey/stg/
- **Production (`main`):** https://khanhchungoc.github.io/detective-wifey/
