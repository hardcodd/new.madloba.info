# new.madloba.info

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
