---
name: No rushing into fixes
description: Always discuss the problem and solutions before making code changes
type: feedback
originSessionId: 923cc607-481d-423f-8eb6-fb20519e8727
---
Don't rush into code fixes. Before changing anything:
1. Explain what the issue is
2. Where it happens
3. Why it happens
4. Discuss solution options
5. Wait for explicit approval before editing any file

**Why:** Tomer wants to maintain solid, stable organization. Understanding the problem fully before acting leads to better decisions. Confirmed by an incident on 2026-04-26: I started editing files mid-session for a small-feeling change (per-doctor scoping + dev reset) without a plan, and Tomer interrupted and rejected — said "we always plan before code changes."

**How to apply:** Always pause to discuss before proposing or making code changes, even when the fix seems obvious. The bar for "small enough to skip planning" is essentially zero. Even mid-session follow-up tweaks need a written plan first. If multiple files will change or any new endpoint/abstraction is involved, use plan mode (ExitPlanMode flow). For a one-line fix, still write the plan inline and ask before editing.
