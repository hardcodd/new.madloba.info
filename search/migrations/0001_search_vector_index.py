"""Index the combined vector used by Wagtail's PostgreSQL search backend."""

from django.db import migrations


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("wagtailsearch", "0008_remove_query_and_querydailyhits_models"),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                "CREATE INDEX CONCURRENTLY madloba_search_title_body_gin "
                "ON wagtailsearch_indexentry USING GIN ((title || body))"
            ),
            reverse_sql="DROP INDEX CONCURRENTLY madloba_search_title_body_gin",
        ),
    ]
