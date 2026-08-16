# V3 Launch Root-Cause Audit

`V3_ROOT_CAUSE_CONFIRMED_PASS`

The v3 infrastructure qualification workflow committed and pushed the freeze/authorization artifacts using the workflow `GITHUB_TOKEN`. The separate formal-sequence workflow depended on a later `push` of `formal-authorization-lock-v3.json`. That recursive event did not launch the second workflow, so no formal Candidate invocation occurred. v4 removes the second-event dependency and keeps formal execution in the same already-running workflow graph.
