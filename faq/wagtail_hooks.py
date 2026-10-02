"""Connect nested source names to the engine's existing language controls."""

from django.utils.html import format_html
from django.utils.safestring import SafeString
from wagtail import hooks
from django.templatetags.static import static


@hooks.register("insert_global_admin_js")
def source_language_script() -> SafeString:
    """Load the narrow adapter; it creates no separate language selector."""
    return format_html(
        '<script src="{}" defer></script>', static("faq/source_languages.js")
    )
