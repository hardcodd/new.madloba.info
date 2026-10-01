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

# Sitemap completeness during regeneration

## Scope

Investigate the reported loss of category and article URLs using the current
local catalog data and the generator history. Preserve existing sitemap files
when a regeneration cannot produce complete output. Transfer the verified fix
from the local catalog checkout to this project.

## Expected behavior

- Every selected live page produces exactly one `<url>` entry in its section's
  primary language map. An exception or missing primary URL is reported with
  enough context to identify the affected page and aborts that section.
- A failed section leaves all its previously published files intact, including
  multi-file sections. A successful section removes stale numbered files.
- A large reduction from an existing section map is detected before replacing
  its files, so an unexpected change in page selection cannot silently remove
  most indexed URLs. An intentional large reduction can be explicitly allowed.
- Unselected sections and the sitemap index remain available during partial
  regeneration.

## Constraints

- Preserve the current sitemap URL structure and command usage by default.
- Avoid retaining changes in the local catalog checkout and avoid database
  writes during investigation.
- Do not add or change dependencies.

## Acceptance criteria

- Focused tests cover failed URL resolution, missing URLs, multi-file rollback,
  unexpected shrinkage, deliberate shrinkage, and normal regeneration.
- The local category and article counts are compared with their generated maps.
- The relevant Django checks and tests pass, and `git diff --check` is clean.

# Sitemap file delivery after regeneration

## Scope

Serve the generated sitemap index and section XML from the current files on
disk. Remove Django template-loader caching from the public sitemap path.

## Expected behavior

- A request reads the current XML file, including after that file is replaced
  while the application process remains running.
- Preserve existing sitemap URLs, XML bytes, `application/xml` responses, and
  404 behavior for missing files or unsupported languages.
- Stream section files so large organization maps are not loaded into memory
  as complete response bodies.

## Constraints

- Keep the generator's successful-write and rollback protections intact: old
  section files remain public until new files are ready, and stale files are
  removed only after successful publication.
- Do not alter the database, generated sitemap content, or dependencies.

## Acceptance criteria

- Focused tests show that repeated requests to both the index and a section
  return replacement file contents without resetting the template engine.
- Focused tests cover XML response type and missing-file handling.
- A full local regeneration produces an index and section URL lists that match
  the selected live database pages in every configured language, without
  duplicate URLs.
- Applicable Django checks and tests pass, and `git diff --check` is clean.
