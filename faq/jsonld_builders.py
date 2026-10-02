"""Structured data from the same translated fields rendered in the FAQ HTML."""

from typing import Any

from django.http import HttpRequest

from core.jsonld import build_jsonld
from .models import FaqCategoryPage, FaqIndexPage, FaqQuestionPage


@build_jsonld.register(FaqIndexPage)
@build_jsonld.register(FaqCategoryPage)
@build_jsonld.register(FaqQuestionPage)
def faq_jsonld(
    page: FaqIndexPage | FaqCategoryPage | FaqQuestionPage, request: HttpRequest
) -> dict[str, Any]:
    """Emit page dates, breadcrumbs and only visible questions/answers."""
    url = page.get_full_url(request=request) or request.build_absolute_uri()
    webpage: dict[str, Any] = {
        "@type": "WebPage",
        "@id": url,
        "url": url,
        "name": page.title,
    }
    ancestors = list(page.get_ancestors().live().public().exclude(depth=1).specific())
    breadcrumbs = [
        {
            "@type": "ListItem",
            "position": position,
            "name": ancestor.title,
            "item": ancestor.get_full_url(request=request),
        }
        for position, ancestor in enumerate(ancestors + [page], 1)
    ]
    graph = [
        webpage,
        {
            "@type": "BreadcrumbList",
            "@id": f"{url}#breadcrumbs",
            "itemListElement": breadcrumbs,
        },
    ]
    if isinstance(page, FaqQuestionPage):
        webpage["datePublished"] = page.answered_at.isoformat()
        webpage["dateModified"] = page.checked_at.isoformat()
        names = list(
            dict.fromkeys(
                [page.title] + [str(block.value) for block in page.people_also_ask]
            )
        )
        graph.append(
            {
                "@type": "FAQPage",
                "@id": f"{url}#faq",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": name,
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": page.short_answer,
                        },
                    }
                    for name in names
                ],
            }
        )
    return {"@context": "https://schema.org", "@graph": graph}
