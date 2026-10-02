"""FAQ page hierarchy using the engine's shared translation and CSV mechanisms."""

from __future__ import annotations

import re
from datetime import date
from typing import Any
from urllib.parse import parse_qs, urlsplit

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.functions import Length, Substr
from django.http import HttpRequest
from django.utils import translation
from django.utils.translation import gettext_lazy as _
from modelcluster.contrib.taggit import ClusterTaggableManager
from modelcluster.fields import ParentalKey
from taggit.models import TaggedItemBase
from wagtail.admin.panels import FieldPanel, MultiFieldPanel, ObjectList, TabbedInterface
from wagtail.blocks import CharBlock, PageChooserBlock
from wagtail.fields import RichTextField, StreamField
from wagtail.images.models import Image
from wagtail.models import Page, PageQuerySet, Site
from wagtail.search import index
from wagtail.snippets.models import register_snippet

from core.pagination import paginate
from core.panels import Panels
from .blocks import SourceBlock


def public_questions(site: Site | None) -> PageQuerySet[FaqQuestionPage]:
    """Select public card data without loading long answers, blocks or images.

    Keep every short-answer/title translation available so fallback never adds
    a query per card. Full answer pages use their normal, complete page instance.
    """
    questions = (
        FaqQuestionPage.objects.live()
        .public()
        .defer_streamfields()
        .defer(
            *translated_field_names(
                "details",
                "tip",
                "may_differ",
                "myth",
                "myth_truth",
            )
        )
    )
    return questions.in_site(site) if site is not None else questions.none()


def translated_field_names(*bases: str) -> tuple[str, ...]:
    """Include physical base fields and all configured translation columns."""
    return tuple(
        name
        for base in bases
        for name in (
            base,
            *(
                f"{base}_{code.replace('-', '_')}"
                for code in settings.MODELTRANSLATION_LANGUAGES
            ),
        )
    )


def question_counts(index_page: FaqIndexPage, site: Site | None) -> dict[str, int]:
    """Count public questions in SQL, returning one row per populated category.

    Wagtail's materialized path identifies the direct parent by removing one
    fixed-width segment. Filtering precedes grouping, preserving inherited
    restrictions and site/tree boundaries without fetching individual paths.
    """
    counts = (
        public_questions(site)
        .descendant_of(index_page)
        .order_by()
        .annotate(category_path=Substr("path", 1, Length("path") - Page.steplen))
        .values("category_path")
        .annotate(question_count=models.Count("pk"))
        .values_list("category_path", "question_count")
    )
    return dict(counts)


def sidebar_context(category: FaqCategoryPage, request: HttpRequest) -> dict[str, Any]:
    """Build shared navigation and public related links from the current category."""
    faq_index = category.get_parent().specific
    categories = list(
        FaqCategoryPage.objects.child_of(faq_index)
        .live()
        .public()
        .defer(*translated_field_names("intro"))
        .order_by("group__sort_order", "group_id", "sort_order", "pk")
    )
    related_ids = [
        pk for pk in (category.blog_category_id, category.catalog_category_id) if pk
    ]
    site = Site.find_for_request(request)
    related = Page.objects.filter(pk__in=related_ids).live().public()
    related = related.in_site(site) if site is not None else related.none()
    available = {page.pk: page for page in related}
    return {
        "sidebar_category": category,
        "sidebar_categories": categories,
        "sidebar_related_pages": [
            available[pk] for pk in dict.fromkeys(related_ids) if pk in available
        ],
    }


def youtube_id(url: str) -> str | None:
    """Accept only known HTTPS YouTube URL shapes with an eleven-character ID."""
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.username or parts.password:
        return None
    host = parts.hostname
    candidate = ""
    if host == "youtu.be":
        candidate = parts.path.strip("/")
    elif host in {
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "www.youtube-nocookie.com",
    }:
        if parts.path == "/watch":
            candidate = parse_qs(parts.query).get("v", [""])[0]
        elif parts.path.startswith(("/embed/", "/shorts/")):
            candidate = parts.path.split("/")[-1]
    return candidate if re.fullmatch(r"[A-Za-z0-9_-]{11}", candidate) else None


@register_snippet
class FaqCategoryGroup(models.Model):
    """Configurable translated group titles shared by FAQ category pages."""

    title = models.CharField(max_length=120, verbose_name=_("Title"))
    sort_order = models.PositiveIntegerField(default=0, verbose_name=_("Sort order"))
    panels = [FieldPanel("title"), FieldPanel("sort_order")]

    def __str__(self) -> str:
        return self.title

    class Meta:
        ordering = ["sort_order", "pk"]
        verbose_name = _("FAQ category group")
        verbose_name_plural = _("FAQ category groups")


class FaqIndexPage(Panels, Page):
    """Root of one FAQ tree beneath a home page."""

    parent_page_types = ["home.HomePage"]
    subpage_types = ["faq.FaqCategoryPage"]
    max_count_per_parent = 1
    template = "faq/index_page.html"
    intro = RichTextField(blank=True, verbose_name=_("Introduction"))
    csv_preserve_richtext = True
    content_panels = Panels.content_panels + [FieldPanel("intro")]
    search_fields = Page.search_fields + [index.SearchField("intro")]

    def get_context(
        self, request: HttpRequest, *args: Any, **kwargs: Any
    ) -> dict[str, Any]:
        context = super().get_context(request, *args, **kwargs)
        categories = list(
            FaqCategoryPage.objects.child_of(self)
            .live()
            .public()
            .select_related("group")
            .defer(*translated_field_names("intro"))
            .order_by("group__sort_order", "group_id", "sort_order", "pk")
        )
        groups: dict[
            int | None, tuple[FaqCategoryGroup | None, list[FaqCategoryPage]]
        ] = {}
        site = Site.find_for_request(request)
        counts = question_counts(self, site)
        for category in categories:
            category.question_count = counts.get(category.path, 0)
            groups.setdefault(category.group_id, (category.group, []))[1].append(
                category
            )
        context["category_groups"] = list(groups.values())
        context["popular_questions"] = (
            public_questions(site)
            .descendant_of(self)
            .filter(is_popular=True)
            .order_by("-checked_at", "-pk")[:6]
        )
        return context

    class Meta(Page.Meta):
        verbose_name = _("FAQ index page")
        verbose_name_plural = _("FAQ index pages")


class FaqCategoryPage(Panels, Page):
    """A paginated question list with optional links to existing content."""

    parent_page_types = ["faq.FaqIndexPage"]
    subpage_types = ["faq.FaqQuestionPage"]
    template = "faq/category_page.html"
    intro = RichTextField(blank=True, verbose_name=_("Introduction"))
    cover = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=_("Cover"),
    )
    group = models.ForeignKey(
        FaqCategoryGroup,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="categories",
        verbose_name=_("FAQ category group"),
    )
    sort_order = models.PositiveIntegerField(default=0, verbose_name=_("Sort order"))
    blog_category = models.ForeignKey(
        "blog.BlogCategoryPage",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=_("Blog category"),
    )
    catalog_category = models.ForeignKey(
        "catalog.OrganizationType",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=_("Catalog category"),
    )
    csv_preserve_richtext = True
    question_count: int = 0
    content_panels = Panels.content_panels + [
        FieldPanel(name)
        for name in [
            "intro",
            "cover",
            "group",
            "sort_order",
            "blog_category",
            "catalog_category",
        ]
    ]
    search_fields = Page.search_fields + [index.SearchField("intro")]

    @property
    def get_image(self) -> Image | None:
        return self.cover

    def get_context(
        self, request: HttpRequest, *args: Any, **kwargs: Any
    ) -> dict[str, Any]:
        context = super().get_context(request, *args, **kwargs)
        questions = (
            public_questions(Site.find_for_request(request))
            .child_of(self)
            .order_by("-is_popular", "-checked_at", "-pk")
        )
        context["questions"] = paginate(request, questions)
        context.update(sidebar_context(self, request))
        return context

    class Meta(Page.Meta):
        verbose_name = _("FAQ category page")
        verbose_name_plural = _("FAQ category pages")


class FaqTag(TaggedItemBase):
    content_object = ParentalKey(
        "faq.FaqQuestionPage", related_name="tagged_items", on_delete=models.CASCADE
    )


class FaqQuestionPage(Panels, Page):
    """A structured answer; dates describe editorial verification, not saves."""

    parent_page_types = ["faq.FaqCategoryPage"]
    subpage_types: list[str] = []
    template = "faq/question_page.html"
    subtitle = models.CharField(max_length=200, blank=True, verbose_name=_("Subtitle"))
    short_answer = models.TextField(verbose_name=_("Short answer"))
    why_points = StreamField(
        [("point", CharBlock(label=_("Point")))],
        min_num=2,
        max_num=5,
        verbose_name=_("Why"),
    )
    details = RichTextField(
        blank=True,
        verbose_name=_("Details"),
    )
    tip = RichTextField(blank=True, verbose_name=_("Tip"))
    may_differ = RichTextField(blank=True, verbose_name=_("What may differ"))
    myth = RichTextField(blank=True, verbose_name=_("Common misconception"))
    myth_truth = RichTextField(blank=True, verbose_name=_("What actually happens"))
    people_also_ask = StreamField(
        [("question", CharBlock(label=_("Question")))],
        blank=True,
        verbose_name=_("People also ask"),
    )
    sources = StreamField(
        [("source", SourceBlock())], blank=True, max_num=5, verbose_name=_("Sources")
    )
    important_note = models.CharField(
        max_length=500, blank=True, verbose_name=_("Important note")
    )
    answered_at = models.DateField(default=date.today, verbose_name=_("Answered at"))
    checked_at = models.DateField(
        default=date.today, db_index=True, verbose_name=_("Checked at")
    )
    cta_page = models.ForeignKey(
        "wagtailcore.Page",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=_("Read more page"),
    )
    cta_url = models.URLField(
        max_length=2000, blank=True, verbose_name=_("Read more URL")
    )
    cta_label = models.CharField(
        max_length=200, blank=True, verbose_name=_("Read more label")
    )
    related_questions = StreamField(
        [("question", PageChooserBlock(page_type="faq.FaqQuestionPage"))],
        blank=True,
        max_num=5,
        verbose_name=_("Related questions"),
    )
    cover = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=_("Cover"),
    )
    social_image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=_("Social image"),
    )
    video_url = models.URLField(
        max_length=2000, blank=True, verbose_name=_("YouTube URL")
    )
    is_popular = models.BooleanField(
        default=False, db_index=True, verbose_name=_("Popular question")
    )
    tags = ClusterTaggableManager(through=FaqTag, blank=True)
    csv_native_streams = True
    csv_preserve_richtext = True
    csv_clear_blank_fields = True
    csv_plain_text_fields = {"short_answer"}
    content_panels = Panels.content_panels + [
        FieldPanel("subtitle"),
        FieldPanel("short_answer"),
        FieldPanel("why_points"),
        FieldPanel("details"),
    ]
    answer_details_panels = [
        FieldPanel("tip"),
        FieldPanel("may_differ"),
        MultiFieldPanel(
            [FieldPanel("myth"), FieldPanel("myth_truth")],
            heading=_("Common misconception"),
        ),
        FieldPanel("people_also_ask"),
        FieldPanel("important_note"),
    ]
    sources_panels = [
        FieldPanel("sources"),
        MultiFieldPanel(
            [FieldPanel("answered_at"), FieldPanel("checked_at")], heading=_("Dates")
        ),
    ]
    links_media_panels = [
        MultiFieldPanel(
            [FieldPanel(name) for name in ["cta_page", "cta_url", "cta_label"]],
            heading=_("Read more"),
        ),
        FieldPanel(
            "related_questions",
            help_text=_(
                "Leave blank to show four automatically selected questions from the "
                "same category, ordered by check date. Select up to five questions "
                "to replace the automatic list. Clear this field to restore it."
            ),
        ),
        FieldPanel("cover"),
        FieldPanel("video_url"),
    ]
    promote_panels = Panels.promote_panels + [
        FieldPanel("social_image"),
        FieldPanel("is_popular"),
        FieldPanel("tags"),
    ]
    edit_handler = TabbedInterface(
        [
            ObjectList(content_panels, heading=_("Answer")),
            ObjectList(answer_details_panels, heading=_("Answer details")),
            ObjectList(sources_panels, heading=_("Sources")),
            ObjectList(links_media_panels, heading=_("Links and media")),
            ObjectList(promote_panels, heading=_("Promote")),
            ObjectList(Page.settings_panels, heading=_("Settings")),
        ]
    )
    search_fields = Page.search_fields + [
        index.SearchField(name)
        for name in [
            "short_answer",
            "why_points",
            "details",
            "people_also_ask",
            "tip",
            "may_differ",
            "myth",
            "myth_truth",
        ]
    ]

    def clean(self) -> None:
        super().clean()
        errors: dict[str, str] = {}
        for code in settings.MODELTRANSLATION_LANGUAGES:
            suffix = code.replace("-", "_")
            myth_field = f"myth_{suffix}"
            truth_field = f"myth_truth_{suffix}"
            # Check physical translations independently; fallback must not hide
            # an incomplete pair behind content from another language.
            myth = getattr(self, myth_field)
            truth = getattr(self, truth_field)
            if bool(myth) != bool(truth):
                errors[truth_field if myth else myth_field] = _(
                    "Enter both the misconception and its correction, or leave both blank."
                )
        if errors:
            raise ValidationError(errors)
        if self.video_url and youtube_id(self.video_url) is None:
            raise ValidationError(
                {"video_url": _("Enter a valid HTTPS YouTube video URL.")}
            )
        if self.checked_at and self.answered_at and self.checked_at < self.answered_at:
            raise ValidationError(
                {"checked_at": _("The check date cannot precede the answer date.")}
            )

    @property
    def answer_excerpt(self) -> str:
        """Return the first sentence for category lists without rewriting the answer."""
        return re.split(r"(?<=[.!?])\s+", self.short_answer.strip(), maxsplit=1)[0]

    @property
    def get_image(self) -> Image | None:
        if self.cover:
            return self.cover
        parent = self.get_parent().specific if self.pk else None
        return getattr(parent, "cover", None)

    def get_related_questions(self, request: HttpRequest) -> list[FaqQuestionPage]:
        """Resolve manual choices securely, or use four checked siblings."""
        queryset = public_questions(Site.find_for_request(request)).exclude(pk=self.pk)
        ids = list(
            dict.fromkeys(
                block.value.pk for block in self.related_questions if block.value
            )
        )
        if ids:
            available = {page.pk: page for page in queryset.filter(pk__in=ids)}
            return [available[pk] for pk in ids if pk in available]
        return list(
            queryset.child_of(self.get_parent()).order_by("-checked_at", "-pk")[:4]
        )

    def get_context(
        self, request: HttpRequest, *args: Any, **kwargs: Any
    ) -> dict[str, Any]:
        context = super().get_context(request, *args, **kwargs)
        language = (translation.get_language() or settings.LANGUAGE_CODE).replace(
            "-", "_"
        )
        default = settings.LANGUAGE_CODE.replace("-", "_")
        context["sources"] = [
            {
                "name": block.value.get(f"name_{language}")
                or block.value.get(f"name_{default}")
                or block.value["url"],
                "url": block.value["url"],
                "checked_at": block.value["checked_at"],
            }
            for block in self.sources
        ]
        context["related_questions"] = self.get_related_questions(request)
        context["category"] = self.get_parent().specific
        context.update(sidebar_context(context["category"], request))
        context["video_id"] = youtube_id(self.video_url) if self.video_url else None
        target = self.cta_page.specific if self.cta_page else None
        if target and target.live and target.get_view_restrictions().count() == 0:
            context["cta_href"] = target.get_url(request=request)
            context["cta_text"] = self.cta_label or target.title
        elif not target and self.cta_url:
            context["cta_href"] = self.cta_url
            context["cta_text"] = self.cta_label or _("Read more")
        return context

    class Meta(Page.Meta):
        verbose_name = _("FAQ question page")
        verbose_name_plural = _("FAQ question pages")
