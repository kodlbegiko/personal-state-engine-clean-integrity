# Candidate-v13 External Validity v4 — Orchestration Design

## Control flow

```text
single push starts one workflow job
  -> bootstrap fresh v4 lineage
  -> candidate-blind prequalification
  -> candidate-blind source/allocation/materialization qualification
  -> formal-runner QA
  -> LAUNCH_PATH_QA
  -> complete preregistration lock
  -> persist pre-freeze evidence
  -> freeze + authorization
  -> verify immutable freeze and zero-use ledger
  -> EV-A-v4
  -> preregistered gate
  -> EV-B-v4
  -> preregistered gate
  -> EV-C-v4
  -> independent final integrity audit
  -> terminal decision
```

No formal stage depends on a recursive `GITHUB_TOKEN` event. No `workflow_dispatch` exists for formal execution. The formal runner uses a one-shot persisted ledger and fails closed on authorization/hash mismatch. Post-freeze infrastructure patches and formal reruns are forbidden.
