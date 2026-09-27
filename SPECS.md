# Application logging and Wagtail log report

## Scope

Port the `site_logs` system from Avtopilot into `new.madloba.info`, adapting it
to this project's Python 3.12, Django 5.2.1, and Wagtail 7.0 runtime. Replace
the current `errors.log` Django handler with the Loguru bridge. Keep existing
application logging calls through Python's standard `logging` API working.

## Expected behavior

- Send warnings and errors from Django and application loggers to Loguru.
  Display warnings and above on stderr by default. Keep warning and error
  records in separate process-specific files under `SITE_LOG_DIR` (default:
  `<project root>/logs`). An error must not be duplicated in the warning file.
- Use the Avtopilot defaults and environment settings: 50 MB rotation,
  30-day warning retention, 90-day error retention, and a `WARNING` console
  threshold. Compress rotated files with gzip. Create log files with owner-only
  permissions. Reject non-positive rotation and retention settings.
- Provide a Wagtail Reports entry for superusers. Show recent complete records
  from the selected warning or error group, merged by timestamp, with limits
  of 200 records, 16 worker files, and 256 KiB per file. List up to 50 files
  available for download. Reading the report must not require log data in the
  database.
- Permit only superusers to view or download logs. Reject invalid level
  groups and filenames. Never follow a symbolic link while downloading a log
  file. Escape log content in the admin page.
- Support direct Loguru calls as well as standard-library logging. Configure
  sinks once per process and reconfigure after a process fork.

## Constraints

- Pin Loguru to the Avtopilot resolved version, 0.7.3; update the project lock
  and dependency declarations consistently. Do not upgrade other packages.
- Preserve unrelated application behavior, files, and existing Git changes.
- Follow existing Wagtail hooks, templates, and Django test conventions.

## Acceptance criteria

- Focused tests prove severity routing, rotation/compression, retention,
  bounded reading, filename and symlink protection, superuser access, and
  denial for other users.
- Django system checks and the applicable project test suite pass, or any
  environmental blocker is reported precisely.
- `git diff --check` reports no whitespace errors.

# Public-site translation completion

## Scope

Complete gettext translations used by visitor-facing templates, catalog
filters and nearby results, comment and review forms, public responses, and
client-side JavaScript for Russian (`ru`), Georgian (`ka`), Danish (`da`),
Finnish (`fi`), Norwegian Bokmål (`nb`), and Swedish (`sv`). English is the
source language. Keep Wagtail administration, import/export, and other
staff-only messages outside this translation pass.

## Expected behavior

- Every active public message has a non-fuzzy translation in each target
  catalog, with valid interpolation placeholders and plural forms.
- Compiled catalogs serve those translations at runtime.
- The review-saving error message uses a constant gettext key so extraction
  and translation work for every target language.
- Remove the obsolete `dk` catalog if no project setting or code uses that
  language code; retain `da` as the supported Danish catalog.

## Constraints

- Preserve existing translations and administrative catalog entries.
- Do not change configured site languages or add dependencies.
- Keep unrelated Git changes and generated files out of the task.

## Acceptance criteria

- Focused tests verify public template, Python response, and JavaScript
  messages in all six catalogs, including placeholders and compiled output.
- The project checks and focused tests pass, or blockers are reported.
- No project references require the removed `dk` catalog, and
  `git diff --check` reports no whitespace errors.
