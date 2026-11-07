---
name: dev-flow
description: "One-command full development pipeline: grill the plan (creating ADRs/glossary as you go), publish a spec, break it into tracer-bullet tickets, implement every ticket, run a two-axis code-review, then close with a retro. Replaces manually chaining /grill-with-docs → /to-spec → /to-tickets → /implement → /code-review → /retro."
---

# Dev Flow

Run the user's standard pipeline end to end in one invocation. The user should never need to type another slash command; you chain the stages yourself.

## Autonomy contract

- Proceed automatically after every successful stage; never ask "shall I continue to the next stage?".
- On the successful path, user input is required only at:
  1. The grilling interview.
  2. `to-spec`'s seam confirmation.
  3. `to-tickets`' breakdown approval.
  4. Stage 6's approval of retro candidates before applying them.
- Stop early for missing prerequisites, a blocked / needs-re-scope ticket, or exhausted model fallback. Surface the failure and repository state instead of silently continuing.
- If the user passed "全自动", "--auto", "yolo", or "don't ask", decide at the first three gates yourself and record each decision in the spec instead of waiting. Batch the grill questions into one message rather than dripping them. Retro changes still require approval.

## Run baseline

At invocation, before any pipeline work is committed, record `START_SHA=$(git rev-parse HEAD)`. Carry this exact SHA through the run and use it as the stage 5 review fixed point; do not recompute a merge-base later.

## Prerequisite check

The spec, tickets, and review stages need the issue tracker and triage vocabulary configured by `/setup-matt-pocock-skills`. Verify that configuration exists before stage 2. If missing, stop and tell the user to run `/setup-matt-pocock-skills` first.

## Stage 1 — Grill (with docs)

Call the Skill tool twice: `grilling` and `domain-modeling`. Run the interview relentlessly; create ADRs and glossary entries as decisions are made. Move on only when the plan is sharp and the user confirms.

## Stage 2 — Spec

Read `~/.claude/skills/to-spec/SKILL.md` and follow it exactly: synthesis only, no interview; publish with the `ready-for-agent` label. Note the published spec's URL/path — stages 4 and 5 reference it.

## Stage 3 — Tickets

Read `~/.claude/skills/to-tickets/SKILL.md` and follow it exactly. After the user approves the breakdown and you publish, keep the topological order (ticket list with blocking edges) — stage 4 consumes it.

## Stage 4 — Implement every ticket

You are the orchestrator; the tickets are implemented by sub-agents, one fresh context per ticket (that is what the tracer-bullet sizing in stage 3 assumes).

Dispatch each ticket to the Agent tool with `subagent_type: "ticket-implementer"`. The prompt must carry everything a fresh context needs, because it inherits nothing from the grill/spec discussion:

- Ticket title + full body as published
- The spec path/URL from stage 2
- The pre-agreed test seams
- "You may commit" (default)

Scheduling rules:

- Implement tickets serially in topological order. WAIT for each sub-agent to finish, spot-check its landed diff and tests, then dispatch the next unblocked ticket.
- Never dispatch implementation tickets in parallel: they would share the checkout, HEAD, index, and test workspace, so one ticket's commit or tests could include another ticket's unfinished work.
- If a sub-agent reports blocked / needs-re-scope, STOP and surface it to the user with what was learned — do not patch the plan silently.
- Model fallback: if a dispatch fails at the MODEL level (unavailable, overloaded, or a persistent API error surviving the harness's own retries), re-dispatch the SAME ticket with the next model down the chain: current → `opus` → `sonnet`. Never go below `sonnet` for tickets.
- Before re-dispatching, inspect `git status`, recent commits, and the diff. If the previous attempt already committed the ticket, do not implement it again: spot-check that commit and its tests, then continue. If it left uncommitted changes, describe them in the re-dispatch prompt; the next agent may adopt only changes verified to belong to this ticket and must leave unrelated or pre-existing changes untouched. Never reset or discard work merely to make a retry clean.
- If `sonnet` also fails at the model level, STOP. Report the ticket, each attempt's outcome, and the current working-tree state; there is no further fallback.
- A task-level failure (ticket reported blocked / needs-re-scope) is NOT a model failure — never retry it on another model; surface it to the user.

The `implement` skill's own final `code-review` step stays DEFERRED: stage 5 reviews all tickets together, per the user's flow.

## Stage 5 — Code review (after ALL tickets)

Read `~/.claude/skills/code-review/SKILL.md` and follow it, with:

- Fixed point: the exact `START_SHA` recorded at invocation, not a `HEAD~N` guess or a merge-base recomputed after the work.
- Spec source: the spec published in stage 2.
- Fix or explicitly acknowledge every finding before moving on; commit the fixes.

## Stage 6 — Retro

Read `~/.claude/skills/retro/SKILL.md` and follow it for the current session. Present improvement candidates ordered by severity; apply the ones the user approves.

## Finishing

Recap the whole run: spec link, tickets done/flagged, review findings and their resolutions, retro proposals.
