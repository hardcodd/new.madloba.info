# Project instructions

## Changelog reports

When the user asks for a changelog or a report about completed changes, follow these rules.

### Report scope

- Create reports for a completed logical task stack, not automatically for every commit.
- A task stack may contain several related commits that together deliver one understandable result.
- Split unrelated work into separate task stacks and separate report pairs.
- Use only facts confirmed by the repository history, diffs, tests, and other checks actually performed. Do not invent results or checks.

### Files

- Store all reports in `changelog/`.
- Create exactly two Markdown files for each task stack:
  - `YYYY-MM-DD-<slug>-brief.md` — a short version for the employer;
  - `YYYY-MM-DD-<slug>-detailed.md` — a detailed version for the developer.
- Use the task completion date. Write the human-readable date inside both reports.
- Use the same date and slug for both files.

### Employer report

Write the brief report in Russian, in the first person, using very simple language that is understandable to a non-technical reader.

Keep only the essentials:

- what I changed;
- why it was needed;
- what improved as a result;
- what was actually checked.

Avoid technical jargon, implementation details, corporate language, long introductions, and unnecessary lists. Keep the report concise.

### Developer report

Write the detailed report in Russian. Include:

- the date and completion status;
- every commit included in the task stack;
- what changed and why;
- important effects on safety, reliability, performance, or maintenance when applicable;
- the checks that were actually run and their results;
- remaining limitations, risks, or required manual steps.

Keep it practical and readable. Do not repeat the diff line by line or add unrelated background information.

### Commit links

- List every included commit in both reports and in `changelog/README.md`.
- Make every short commit hash a Markdown link to the full GitHub commit URL.
- Use this format:
  - `[short_hash](https://github.com/hardcodd/new.madloba.info/commit/FULL_HASH)`
- Resolve hashes from Git; never guess or shorten a hash manually without verifying it.

### Index and navigation

- Maintain `changelog/README.md` as the main index.
- Group report pairs by date and place the newest task stacks first.
- For every task stack, include its title, linked commits, detailed report, and brief report.
- At the top of every report, add links to:
  - the previous task stack when it exists;
  - `changelog/README.md`;
  - the paired report version;
  - the next task stack when it exists.
- Keep navigation links within the same report type where possible: brief to brief and detailed to detailed.
- When adding a new report pair, update navigation in neighboring reports as needed.

### Verification and Git workflow

- Before writing, inspect the relevant commits and their diffs and determine the logical task stacks.
- Check that every task stack has both report files.
- Check dates, commit hashes, GitHub URLs, report facts, and all local Markdown links.
- Run `git diff --check` after editing.
- Do not claim that tests or checks passed unless they were actually run.
- Do not automatically commit changelog changes. Show the result and wait for the user's explicit confirmation before creating a logical commit.
