# new.madloba.info

## FAQ

The native FAQ app reuses Wagtail pages, translation, search and CSV import/export.
See [FAQ editing, import and deployment](faq/README.md).

## Application logs

Loguru receives Django, Wagtail, and application warnings and errors through
Python's standard logging API. Each process writes separate `warnings.*.log`
and `errors.*.log` files in `logs/` by default. Errors do not appear in the
warning files. The previous `errors.log` is not imported into the new report.

Files rotate at 50 MB, rotated files are compressed with gzip, and warning and
error files are retained for 30 and 90 days respectively. The runtime user must
be able to create the log directory. Override the defaults with `SITE_LOG_DIR`,
`SITE_LOG_ROTATION_MB`, `SITE_LOG_WARNING_RETENTION_DAYS`,
`SITE_LOG_ERROR_RETENTION_DAYS`, and `SITE_LOG_CONSOLE_LEVEL`.

Superusers can view recent warnings and errors and download current or archived
files from Wagtail's Reports menu. The report reads bounded file tails on demand;
it does not store logs in the database.

## Tests

Tests use the dedicated PostgreSQL database `test_newmadloba`. Create it as a
PostgreSQL administrator, keep the administrator as its owner, and grant the
application role access only to the test database:

```sql
CREATE DATABASE test_newmadloba;
REVOKE CONNECT ON DATABASE test_newmadloba FROM PUBLIC;
GRANT CONNECT, TEMPORARY ON DATABASE test_newmadloba TO madloba;

\connect test_newmadloba
GRANT USAGE, CREATE ON SCHEMA public TO madloba;
```

Run the test suite without creating or dropping databases:

```bash
.venv/bin/python manage.py test
```

The management command automatically selects `app.settings.test` and enables
`--keepdb`. The test settings reject the working database name and use
`postgres` only as the maintenance connection.

## Search performance

Run `python manage.py migrate search` during deployment. Migration
`search.0001_search_vector_index` adds a PostgreSQL GIN index on the combined
`title || body` vector used by Wagtail 7.0. It builds concurrently to allow
ongoing writes; it does not change indexed content or require a search rebuild.
The migration must run outside an enclosing transaction.

Search results retain relevance ordering within the open/closed groups. Only the
current page's specific models, first organization images and image renditions
are loaded for rendering. Result lists are not cached, so closure status changes
are reflected on the next request.
