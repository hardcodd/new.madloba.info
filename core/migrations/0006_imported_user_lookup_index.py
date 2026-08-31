from django.db import migrations


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("core", "0005_sitesettings_slogan_sitesettings_slogan_en_and_more"),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS "
                "auth_user_import_name_idx "
                "ON auth_user (first_name, username varchar_pattern_ops)"
            ),
            reverse_sql=(
                "DROP INDEX CONCURRENTLY IF EXISTS auth_user_import_name_idx"
            ),
        ),
    ]
