import json
from functools import singledispatch
from typing import Any

from django.http import HttpRequest
from django.utils.html import mark_safe
from wagtail.models import Page


@singledispatch
def build_jsonld(page: Page, request: HttpRequest) -> dict[str, Any] | None:
    # default: no markup
    return None


def render_jsonld(page: Page, request: HttpRequest) -> str:
    data = build_jsonld(page, request)
    if not data:
        return ""
    return mark_safe(
        '<script type="application/ld+json">{}</script>'.format(
            json.dumps(data, ensure_ascii=False, separators=(",", ":"))
            .replace("<", "\\u003c")
            .replace(">", "\\u003e")
            .replace("&", "\\u0026")
        )
    )
