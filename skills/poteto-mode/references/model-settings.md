# pstack model settings

Choose the active harness from the current session’s identity and tools. If neither establishes it, ask which harness is running. Installed directories, CLI binaries, and skill symlinks do not identify the current harness.

Run the bundled [path resolver](../scripts/model-config-path.sh) by its absolute path, from the session's working directory. Do not `cd` into the skill directory first, because a relative `CODEX_HOME` resolves against the working directory:

    sh /absolute/path/to/scripts/model-config-path.sh read codex
    sh /absolute/path/to/scripts/model-config-path.sh write codex

Use the active session's harness ID. Run the same resolver with `list` to see the IDs in the active routing table. Use `other` only for an identified but unlisted harness.

The resolver checks `~/.agents/pstack/model-config-routes.conf` first. If that file is absent, it uses the built-in table from setup-pstack in the same installation, or the global setup-pstack under `~/.agents/skills` or `$CLAUDE_CONFIG_DIR/skills`, then `~/.claude/skills`. A user table supplies all routes. Report any resolver error and stop model selection or setup. Install setup-pstack alongside this skill or globally if a table is missing.

Readers use `read`. Setup uses `read` for existing choices and `write` for the destination. Use the resolved read file as the source of pstack roles, including when Cursor or Claude Code loaded another rule into context. Legacy read paths apply only if listed in the active table.

## Native models

Store the exact model IDs accepted by the active harness. Keep the comma-separated format for panels. When a model ID does not encode effort, pass the recorded budget separately if the subagent tool exposes it. Let the runtime choose effort if the tool has no option.

- **Codex:** Use a model available to the current `spawn_agent` tool. Set effort separately if the tool exposes it.
- **Devin:** The subagent tool selects a profile. For an explicit ID, use a selectable custom profile whose `model` matches that ID. For `inherit-parent` or `auto`, select `subagent_general`.
- **Kiro:** In IDE or CLI, use a selectable custom agent pinned to the exact ID if the delegation tool requires an agent profile. In local Kiro Crew, `kirocrew models` lists IDs accepted by `kirocrew spawn run --model`. Use the active session’s delegation tool when it exposes a model option.

For `inherit-parent` or `auto`, use the parent model. Omit the model override only when that inherits the parent in the selected delegation path. Otherwise select the exact parent model or tell the user if inheritance is unavailable.

Cursor, Claude Code, and the legacy shared route can use the shipped role defaults. For other routes, if the model file is missing, report its path and refer to `setup-pstack`. For a missing role or an unavailable model in a single-worker role, fall back to the parent where supported. For an unconfigured runner or reviewer panel, ask for its entries. For a missing or unusable cross-judge pool, skip the cross-judge.
