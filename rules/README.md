# Your rules

`RULES.md` holds R1 to R125, the system's rules. Do not edit or renumber those. Yours go in `rules/MY-RULES.md`, starting at R200. If yours clashes with an older rule, yours wins once the clash is settled (R84), and you write which one it replaces.

## How a rule gets here

Type `/shorts-rule` and give the note, like "captions too small". Claude writes the rule, adds a code gate if it can be measured, checks for a clash with an older rule, and tells you what changed. Notes saved in the review app work too: `/shorts` reads them on each run and uses this same process.

## What a good rule looks like

- It is a plain instruction someone can test. "Title at most 2 lines" is a rule. "Better titles" is not.
- It says why, in plain words: what went wrong.
- It says what checks it: a gate, or "by eye".

## Template for rules/MY-RULES.md

```markdown
# My rules

Rules from my own notes. They start at R200. Newest at the bottom.

- **R200 Short name.** The plain testable instruction. **Why:** what went wrong. **Check:** the gate, or "by eye". **Replaces:** R.. (only if it does)
```
