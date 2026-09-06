# AGENTS.md — notes for future development sessions

ReposCloner is a **teacher-only, local-only** tool for batch clone/update/inspect
of student conspect repos. No hosting, no accounts, no student-facing parts.

## Layout

- `main.py` — CLI (menu 1–9, RU/EN). Must stay **import-safe**: no work at
  module top level (`web.py` imports `build_runtime`, `load_inventory` from it).
- `web.py` — Streamlit console, the primary UI. Launched via `start-web.bat`
  (bootstraps `~/.streamlit/credentials.toml`, headless, opens browser).
- `reposcloner/` — library, reusable by both UIs, fully unit-testable:
  - `repo_store.py` — inventory: `repos.json` (tracked wanted-list) +
    `discover_local_repos()` (filesystem scan). Merges into `WorkItem`s.
  - `git_operations.py` — clone/update/history/delete/reclone. Data APIs
    (`get_commit_history`, `get_last_commit_summary`) for the web UI;
    print-only `view_commit_history` stays for the CLI.
  - `i18n.py` — RU (primary, default) + EN strings. `search.py`, `utils.py`,
    `config.py`, `report.py` (pure HTML dashboard builder, XSS-escaped).
- `tests/` — pytest, **fully offline** (git is mocked via fakes). Never add a
  test that hits the network.

## Standing user decisions (don't re-litigate, don't regress)

1. **No `repos.txt`-driven workflow.** One-time migration `repos.txt` →
   `repos.json` runs only when no tracked file exists. Never reintroduce
   pattern-filter search UI (`filter_repos()` stays as tested core API only).
2. **Runtime data never enters git.** `repos/`, `repos.json`,
   `changes_results*.json`, `commit_summaries_*.json`, `reposcloner.log`,
   `config.json` are git-ignored. Inventory loads via discovery + one-by-one
   adding in the UI.
3. **RU is primary**, EN secondary. Every user-visible string goes through
   `t(key, lang, **kwargs)` with ru-fallback. `test_i18n` enforces key parity
   and placeholder consistency — keep it green.
4. **Shallow clone is debug-only.** `clone_repo(..., depth=...)` lives in the
   core, but the UI option is gated behind the hidden debug switch:
   `REPOSCLONER_DEBUG=1` env, CLI `--debug` flag, web `?debug=1` URL param.
   No separate debug branch — the switch replaced that idea.
5. **Destructive ops need explicit confirmation**: force-update after
   `conflict`, reclone, Danger-zone delete (checkbox + list-only default).
   `update_repo()` defaults to `force=False` and reports `conflict`.
6. **Tests live on.** Keep the offline suite green; develop on a branch,
   merge to `main`, tag releases (`v1.1.0`, `v1.2.0` …), keep `CHANGELOG.md`
   (Keep a Changelog + SemVer) updated in the same change.

## Gotchas learned the hard way

- **Shell flakiness**: the agent `Bash` tool may be blocked/outaged. Fallback:
  ask the user to run commands via their `!` Git-Bash path (they have Tahoe
  dark theme, output lands in-conversation). `!` is Git Bash, not cmd —
  `del` fails there, use `rm -f`.
- **Python 3.14 here has no pip** — `ensurepip` bootstrap was needed once;
  if packages vanish, reinstall from
  `requirements.txt` / `requirements-dev.txt` / `requirements-web.txt`.
- **Streamlit first run hangs without TTY** (email prompt) — that's why
  `start-web.bat` writes `credentials.toml` first. Keep all launch complexity
  baked into the `.bat`, per user request.
- **`save_config` default-arg trap**: `path=CONFIG_FILE` is frozen at import,
  so monkeypatching `CONFIG_FILE` doesn't affect default-path calls. Tests
  must pass `path` explicitly (see `test_config.py`).
- Windows: expect `LF will be replaced by CRLF` warnings — harmless.
  `delete_repo_checkout` retries on `WinError 5` (locked files).
- Legacy checkout dirs come in two schemes: `owner__repo` (current) and
  `owner_repo` (read-only fallback in `repo_path_for`). Don't "clean up" the
  fallback — old clones still use it.
- Web language switch: widget keys holding translated strings (`danger_*`)
  are popped on switch, otherwise stale values break the rebuilt widgets.
  If you add more language-dependent widgets with keys, add them to that list.
- `st.query_params.get('debug', '')` is the hidden web debug entry point;
  `st.session_state['debug_url']` latches it for the session.
