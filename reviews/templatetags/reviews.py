from __future__ import annotations

from collections.abc import Mapping

from django import template
from django.core.paginator import Page as PaginatorPage
from django.http import HttpRequest
from wagtail.models import Page

from core.pagination import paginate
from reviews.models import Review, ReviewStatus

register = template.Library()


@register.simple_tag
def get_reviews_count(page):
    """
    Return the number of reviews for a given page.
    """
    return Review.objects.filter(
        content_type=page.content_type,
        object_id=page.pk,
        status=ReviewStatus.PUBLISHED,
    ).count()


@register.simple_tag(takes_context=True)
def get_reviews(
    context: template.Context | Mapping[str, HttpRequest], page: Page
) -> PaginatorPage:
    """Return published reviews, applying the public pagination contract."""
    request = context["request"]

    reviews = Review.objects.filter(
        content_type=page.content_type,
        object_id=page.pk,
        status=ReviewStatus.PUBLISHED,
    ).order_by("-created_at")

    return paginate(request, reviews, 10)


@register.simple_tag
def get_total_reviews_count():
    """
    Return total reviews count over the website
    """
    return Review.objects.filter(status=ReviewStatus.PUBLISHED).count()
