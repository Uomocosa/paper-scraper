---
name: plan-rules-fix
description: Scan the available skills catalog for all convention/pattern/rule skills, load each one, and analyze them for ambiguity, misinterpretation risk, and missing generality. Propose concrete clarifications.
---

## Instructions

1. Scan the `<available_skills>` catalog in your system prompt. Load every skill whose name or description matches conventions, patterns, syntax, architecture rules, or project standards.
2. For each loaded skill, identify any rules that:
   - Could be misinterpreted by an AI coding agent
   - Are too project-specific (should use {{template}} variables instead)
   - Have contradictions, edge cases, or gaps
   - Are not general enough for any Rust project
3. For each issue, propose a concrete fix.
4. If the rules are already clear and general, state that no changes are needed.
