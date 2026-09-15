"""Preserve literal subtitles when introducing the rich text editor."""

from html import escape
from typing import Any

from django.apps.registry import Apps
from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor


SUBTITLE_FIELDS = ("subtitle", "subtitle_ru", "subtitle_en", "subtitle_ka")


def rich_subtitle(value: str | None) -> str | None:
    """Escape previously literal text, including apparent HTML and entities."""
    return f"<p>{escape(value)}</p>" if value else value


def preserve_subtitles(apps: Apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    """Convert live fields and saved revisions so restoring a draft stays safe.

    This data migration is intentionally irreversible: later rich text may
    exceed the former character limit or contain links that plain text loses.
    """
    database = schema_editor.connection.alias
    index_page = apps.get_model("blog", "BlogIndexPage")
    revision = apps.get_model("wagtailcore", "Revision")
    for page in index_page.objects.using(database).all().iterator():
        values = {name: rich_subtitle(getattr(page, name)) for name in SUBTITLE_FIELDS}
        index_page.objects.using(database).filter(pk=page.pk).update(**values)

    revisions = revision.objects.using(database).filter(
        content_type__app_label="blog", content_type__model="blogindexpage"
    )
    for item in revisions.iterator():
        content: dict[str, Any] = dict(item.content)
        for name in SUBTITLE_FIELDS:
            if name in content:
                content[name] = rich_subtitle(content[name])
        revision.objects.using(database).filter(pk=item.pk).update(content=content)


class Migration(migrations.Migration):
    dependencies = [
        ("blog", "0006_blogindexpage_banners_blogindexpage_banners_en_and_more"),
        ("wagtailcore", "0094_alter_page_locale"),
    ]
    operations = [migrations.RunPython(preserve_subtitles)]
