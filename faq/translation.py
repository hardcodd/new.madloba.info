from modeltranslation.decorators import register
from modeltranslation.translator import TranslationOptions

from .models import FaqCategoryGroup, FaqCategoryPage, FaqIndexPage, FaqQuestionPage


@register(FaqCategoryGroup)
class FaqCategoryGroupTR(TranslationOptions):
    fields = ("title",)


@register(FaqIndexPage)
class FaqIndexPageTR(TranslationOptions):
    fields = ("intro",)


@register(FaqCategoryPage)
class FaqCategoryPageTR(TranslationOptions):
    fields = ("intro",)


@register(FaqQuestionPage)
class FaqQuestionPageTR(TranslationOptions):
    fields = (
        "subtitle",
        "short_answer",
        "why_points",
        "details",
        "tip",
        "may_differ",
        "myth",
        "myth_truth",
        "people_also_ask",
        "important_note",
        "cta_label",
    )
