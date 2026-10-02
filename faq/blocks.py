"""Native repeatable fields and the reusable home-page FAQ selector."""

from typing import Any

from django.conf import settings
from django.http import HttpRequest
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _
from wagtail.blocks import (
    CharBlock,
    ChoiceBlock,
    DateBlock,
    IntegerBlock,
    ListBlock,
    PageChooserBlock,
    StructBlock,
    URLBlock,
)
from wagtail.blocks import StructValue
from wagtail.models import Site


class SourceBlock(StructBlock):
    """One shared URL/check date with names in the engine's configured languages."""

    def __init__(self, **kwargs: Any) -> None:
        fields = [
            (
                f"name_{code.replace('-', '_')}",
                CharBlock(
                    label=format_lazy("{} ({})", _("Source name"), code), required=False
                ),
            )
            for code in settings.MODELTRANSLATION_LANGUAGES
        ]
        fields += [
            ("url", URLBlock(label=_("URL"))),
            ("checked_at", DateBlock(label=_("Checked at"))),
        ]
        super().__init__(fields, **kwargs)

    class Meta:
        form_template = "faq/admin/source_form.html"


class FaqQuestionsBlock(StructBlock):
    """Select public FAQ pages within the current site; manual order is preserved."""

    title = CharBlock(label=_("Title"), required=False)
    mode = ChoiceBlock(
        choices=[
            ("latest", _("Latest questions")),
            ("popular", _("Popular questions")),
            ("checked", _("Recently checked")),
            ("manual", _("Manual selection")),
        ],
        default="popular",
        label=_("Selection"),
    )
    count = IntegerBlock(default=6, min_value=1, max_value=24, label=_("Count"))
    questions = ListBlock(
        PageChooserBlock(page_type="faq.FaqQuestionPage"),
        required=False,
        max_num=24,
        label=_("Manual questions"),
        help_text=_("Used only for manual selection; list order is preserved."),
    )

    def get_context(
        self, value: StructValue, parent_context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        from .models import public_questions

        context = super().get_context(value, parent_context)
        request: HttpRequest | None = context.get("request")
        site = Site.find_for_request(request) if request is not None else None
        questions = public_questions(site)
        count = value["count"]
        mode = value["mode"]
        if mode == "manual":
            ids = list(dict.fromkeys(page.pk for page in value["questions"] if page))
            available = {page.pk: page for page in questions.filter(pk__in=ids)}
            context["questions"] = [available[pk] for pk in ids if pk in available][
                :count
            ]
        else:
            if mode == "popular":
                questions = questions.filter(is_popular=True)
            order = "-first_published_at" if mode == "latest" else "-checked_at"
            context["questions"] = list(questions.order_by(order, "-pk")[:count])
        return context

    class Meta:
        template = "faq/blocks/questions.html"
        icon = "help"
        label = _("FAQ questions")
