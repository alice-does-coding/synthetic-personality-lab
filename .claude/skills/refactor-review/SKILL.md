---
name: refactor-review
description: Review the codebase (or a scoped subset) for refactor opportunities — duplication, dead code, oversized functions, mixed concerns, leaky abstractions, naming/structure smells, and premature complexity. Outputs a prioritized list of findings with file:line references and concrete refactor proposals. Use when the user asks for a refactor pass, a "refactor review", code smells, structural cleanup, or wants to know what to clean up before further feature work.
---

# Refactor Review

You are performing a refactor-oriented code review of the Synthetic Personality Lab repo. The goal is **structural** feedback, not correctness review (use `/code-review` for bugs) and not security review (use `/security-review` for that). Findings should identify *what* to refactor and *why*, with enough specificity that a follow-up edit session can act on them without re-investigating.

## Scope selection

Determine scope from the user's invocation:

1. **No argument** → review the working tree against `origin/main` (`git diff --stat origin/main...HEAD` and `git diff origin/main...HEAD`). If no diff, fall back to a whole-repo pass focused on the largest modules.
2. **A path** (e.g. `/refactor-review backend/engine.py`) → review that file or directory only.
3. **`--full`** → whole-repo pass. Prioritize files >300 lines and shared modules first.

Always state the chosen scope in the first line of output so the user can correct it.

## What to look for

Organize findings under these categories. Skip a category if you have no findings for it — don't pad.

- **Duplication** — repeated logic across files (esp. `backend/routes/*.py`, `backend/providers/*.py`, `frontend/src/pages/*`, `frontend/src/components/*`). Look for copy-paste request/response handling, repeated OCEAN trait iteration, repeated chart config, duplicate fetch+state patterns.
- **Oversized units** — functions >60 lines, files >500 lines, components with deeply nested JSX. `backend/engine.py` and `backend/seed.py` are known hotspots — check whether responsibilities can be split (tick loop vs. agent action vs. IPIP scoring vs. news fetching).
- **Mixed concerns** — route handlers that do DB queries + business logic + response shaping inline; React components that own data fetching, transformation, and rendering all at once; LLM prompt construction tangled with provider dispatch.
- **Leaky / premature abstractions** — base classes used by one subclass, indirection that obscures more than it hides, config flags with one call site, helper functions only used once.
- **Dead code** — unused exports, unreachable branches, commented-out blocks, `_unused` params, routes with no frontend caller, frontend helpers with no importer.
- **Naming & structure** — vague names (`data`, `result`, `handle`), inconsistent casing between Python (snake_case) and JS (camelCase) at the API boundary, files whose name no longer matches their contents.
- **State & data flow** — prop drilling that should be context, context that should be props, `useEffect` chains that could be derived state, mutable globals in Python that should be passed explicitly.
- **Error handling shape** — repeated try/except wrappers that could be a decorator, inconsistent error response shapes across routes, swallowed exceptions.
- **Test gaps that block refactor** — modules with no test coverage that you'd want covered *before* refactoring (note these, don't write the tests).

## How to investigate

- Use `Explore` subagent for broad searches across many files. Use `Grep`/`Bash` for targeted lookups.
- Read whole files for any module flagged as oversized — don't skim.
- For duplication claims, cite at least two file:line locations.
- Cross-check Python ↔ JS boundary by reading both the route handler and its frontend caller before claiming mixed concerns.
- Don't claim "dead code" without grepping for the symbol across both `backend/` and `frontend/src/`.

## Output format

Lead with a one-line scope statement, then a one-paragraph executive summary (3 sentences max), then findings grouped by category. Each finding:

```
### [Category] Short title
**Where:** path/to/file.py:line-range (and any related locations)
**Smell:** one sentence describing the structural issue
**Refactor:** one or two sentences proposing the concrete change
**Effort:** S / M / L
**Priority:** P0 (blocking further work) / P1 (high value) / P2 (nice to have)
```

End with a **Suggested order** section: 3–7 findings to tackle first, in order, with one-line rationale each. Don't propose a sweeping rewrite — favor incremental, independently-mergeable refactors.

## Don'ts

- Don't propose new features or behavior changes — refactors preserve behavior.
- Don't suggest adding comments, docstrings, or type hints as standalone findings. Only mention them if they're part of a larger restructuring.
- Don't flag style/formatting issues — that's lint's job.
- Don't write the refactor. This skill produces the review only; the user will decide what to act on.
- Don't pad with low-value findings to look thorough. Five strong findings beat twenty weak ones.
