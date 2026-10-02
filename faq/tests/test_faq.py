import json
from datetime import date, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import RequestFactory, TestCase
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.template.loader import render_to_string
from django.utils import timezone
from wagtail.models import Page, PageViewRestriction, Site
from wagtail.search.backends import get_search_backend
from django.utils.translation import override
from django.http import Http404
from django.urls import reverse

from core.import_views import import_pages
from core.jsonld import render_jsonld
from core.serializers import serialize_page_field
from core.views import import_page
from core.views import run_field_handler
from faq.blocks import FaqQuestionsBlock
from faq.models import FaqCategoryGroup, FaqCategoryPage, FaqIndexPage, FaqQuestionPage
from home.models import HomePage


class FaqTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        root = Page.get_first_root_node()
        cls.home = root.add_child(instance=HomePage(title="FAQ home", slug="faq-home"))
        cls.site = Site.objects.get(is_default_site=True)
        cls.site.root_page = cls.home
        cls.site.save()
        cls.index = cls.home.add_child(
            instance=FaqIndexPage(title="Questions", slug="faq")
        )
        cls.group = FaqCategoryGroup.objects.create(title="Travel", sort_order=1)
        cls.category = cls.index.add_child(
            instance=FaqCategoryPage(title="Money", slug="money", group=cls.group)
        )
        cls.user = get_user_model().objects.create_superuser(
            "faq-admin", "faq@example.com", "test-password"
        )

    def setUp(self):
        self.factory = RequestFactory()
        self.request = self.factory.get("/ru/faq/")
        self.request.site = self.site
        self.request.user = self.user

    def question(self, slug="currency", **kwargs):
        defaults = dict(
            title="Which currency?",
            slug=slug,
            short_answer="Use lari. Exchange at a bank.",
            answered_at=date(2026, 9, 21),
            checked_at=date(2026, 9, 22),
            why_points=[("point", "Local currency"), ("point", "Official rates")],
        )
        defaults.update(kwargs)
        page = self.category.add_child(instance=FaqQuestionPage(**defaults))
        if page.live:
            page.save_revision().publish()
        return page

    def row(self, values):
        request = self.factory.post(
            "/core/import-page/",
            {
                "page_type": "faq.models.FaqQuestionPage",
                "csv_row": json.dumps(values),
                **{f"field_mapping[{key}]": key for key in values},
            },
        )
        request.user = self.user
        return import_page(request)

    def test_native_hierarchy(self):
        self.assertIn(HomePage, FaqIndexPage.allowed_parent_page_models())
        self.assertFalse(FaqQuestionPage.can_create_at(self.index))
        self.assertTrue(FaqQuestionPage.can_create_at(self.category))
        self.assertEqual(FaqQuestionPage.creatable_subpage_models(), [])
        self.assertFalse(FaqIndexPage.can_create_at(self.home))

    def test_native_admin_edit_forms_render(self):
        self.client.force_login(self.user)
        for page in (self.index, self.category, self.question()):
            with self.subTest(model=type(page).__name__):
                response = self.client.get(
                    reverse("wagtailadmin_pages:edit", args=[page.pk])
                )
                self.assertEqual(response.status_code, 200)

    def test_long_answers_use_native_rich_text_editor(self):
        from wagtail.fields import RichTextField

        for name in ("details", "tip", "may_differ", "myth", "myth_truth"):
            with self.subTest(field=name):
                field = FaqQuestionPage._meta.get_field(name)
                self.assertIsInstance(field, RichTextField)
                self.assertIsNone(field.features)
        self.assertNotIsInstance(
            FaqQuestionPage._meta.get_field("short_answer"), RichTextField
        )

    def test_question_editor_tabs_preserve_translations_and_settings(self):
        from django.conf import settings

        with override("en"):
            handler = FaqQuestionPage.get_edit_handler()
            tabs = {str(tab.heading): tab for tab in handler.children}
        self.assertEqual(
            list(tabs),
            ["Answer", "Answer details", "Sources", "Links and media", "Promote", "Settings"],
        )
        fields = {
            name: tab.get_form_options()["fields"] for name, tab in tabs.items()
        }
        for code in settings.MODELTRANSLATION_LANGUAGES:
            suffix = code.replace("-", "_")
            for name in ("title", "short_answer", "why_points", "details"):
                self.assertIn(f"{name}_{suffix}", fields["Answer"])
            for name in ("tip", "may_differ", "myth", "myth_truth"):
                self.assertIn(f"{name}_{suffix}", fields["Answer details"])
        self.assertIn("sources", fields["Sources"])
        self.assertIn("checked_at", fields["Sources"])
        self.assertIn("related_questions", fields["Links and media"])
        self.assertIn("cover", fields["Links and media"])
        self.assertIn("social_image", fields["Promote"])
        for name in ("tags", "is_popular"):
            self.assertIn(name, fields["Promote"])
            self.assertNotIn(name, fields["Settings"])
        for name in ("go_live_at", "expire_at"):
            self.assertIn(name, fields["Settings"])
        flattened = [name for tab_fields in fields.values() for name in tab_fields]
        self.assertEqual(len(flattened), len(set(flattened)))

    def test_manual_related_selection_overrides_automatic_until_cleared(self):
        page = self.question()
        older = self.question("older", checked_at=date(2026, 9, 22))
        newer = self.question("newer", checked_at=date(2026, 9, 23))
        page.related_questions = [("question", older)]
        self.assertEqual(
            [question.pk for question in page.get_related_questions(self.request)],
            [older.pk],
        )
        page.related_questions = []
        self.assertEqual(
            [question.pk for question in page.get_related_questions(self.request)],
            [newer.pk, older.pk],
        )

    def test_source_form_marks_translations_for_existing_language_picker(self):
        from faq.blocks import SourceBlock

        html = SourceBlock().render_form_template()
        for code in ("ru", "ka", "en"):
            self.assertIn(f'data-faq-source-language="{code}"', html)
        self.assertIn('data-contentpath="url"', html)
        self.assertIn('data-contentpath="checked_at"', html)

    def test_empty_optional_sections_and_server_rendered_answer(self):
        page = self.question()
        html = page.serve(self.request).render().content.decode()
        self.assertIn("Use lari.", html)
        self.assertNotIn("faq-tip", html)
        self.assertNotIn("faq-myth", html)
        self.assertNotIn("faq-video", html)
        self.assertNotIn("faq-read-more", html)

    def test_related_fallback_excludes_private_and_drafts(self):
        page = self.question()
        visible = self.question("visible")
        self.question("draft", live=False)
        private = self.question("private")
        PageViewRestriction.objects.create(
            page=private, restriction_type="password", password="secret"
        )
        self.assertEqual(
            [q.pk for q in page.get_related_questions(self.request)], [visible.pk]
        )

    def test_block_modes_and_manual_order(self):
        older = self.question("older", is_popular=True, checked_at=date(2026, 9, 23))
        newer = self.question("newer", checked_at=date(2026, 9, 24))
        Page.objects.filter(pk=older.pk).update(
            first_published_at=timezone.now() - timedelta(days=2)
        )
        self.question("draft", live=False)
        block = FaqQuestionsBlock()
        for mode, expected in [
            ("latest", [newer.pk, older.pk]),
            ("popular", [older.pk]),
            ("checked", [newer.pk, older.pk]),
            ("manual", [older.pk, newer.pk]),
        ]:
            with self.subTest(mode=mode):
                value = block.to_python(
                    {
                        "title": "FAQ",
                        "mode": mode,
                        "count": 6,
                        "questions": [older.pk, newer.pk],
                    }
                )
                context = block.get_context(value, {"request": self.request})
                self.assertEqual([q.pk for q in context["questions"]], expected)

    def test_category_order_and_groups(self):
        self.question("newer", checked_at=date(2026, 9, 24))
        popular = self.question("popular", is_popular=True)
        context = self.category.get_context(self.request)
        self.assertEqual(context["questions"][0].pk, popular.pk)
        self.assertEqual(
            self.index.get_context(self.request)["category_groups"][0][0].pk,
            self.group.pk,
        )

    def test_safe_jsonld_and_visible_alternative_wording(self):
        page = self.question(
            people_also_ask=[("question", "Money in Georgia?")],
            short_answer="Use lari. </script><script>alert(1)</script>",
        )
        output = render_jsonld(page, self.request)
        self.assertEqual(output.count("</script>"), 1)
        data = json.loads(output.split(">", 1)[1].rsplit("</script>", 1)[0])
        faq = next(node for node in data["@graph"] if node["@type"] == "FAQPage")
        self.assertEqual(
            [q["name"] for q in faq["mainEntity"]], [page.title, "Money in Georgia?"]
        )
        self.assertEqual(
            faq["mainEntity"][0]["acceptedAnswer"]["text"], page.short_answer
        )

    def test_video_host_validation(self):
        page = self.question()
        page.video_url = "https://example.com/watch?v=abcdefghijk"
        with self.assertRaises(ValidationError):
            page.clean()

    def test_import_ui_contains_faq_and_existing_parent_id(self):
        response = import_pages(self.request)
        self.assertContains(response, "faq.models.FaqQuestionPage")
        self.assertContains(response, "parent_id")

    def test_csv_round_trip_preserves_text_html_sources_and_references(self):
        other = self.question("other")
        page = self.question(
            details="<p><b>Verified</b> <a href='https://example.com'>source</a></p>",
            sources=[
                (
                    "source",
                    {
                        "name_ru": "Bank",
                        "name_en": "Bank",
                        "url": "https://example.com",
                        "checked_at": date(2026, 9, 22),
                    },
                )
            ],
            related_questions=[("question", other)],
        )
        values = {
            key: serialize_page_field(page, key)
            for key in [
                "id",
                "short_answer_ru",
                "details_ru",
                "why_points_ru",
                "sources",
                "related_questions",
                "checked_at",
            ]
        }
        response = self.row(values)
        self.assertEqual(response.status_code, 200, response.content)
        page.refresh_from_db()
        self.assertEqual(page.short_answer_ru, "Use lari. Exchange at a bank.")
        self.assertIn("<b>Verified</b>", str(page.details_ru))
        self.assertEqual(page.sources[0].value["url"], "https://example.com")
        self.assertEqual(page.related_questions[0].value.pk, other.pk)

    def test_draft_import_preserves_live_content(self):
        page = self.question()
        response = self.row(
            {"id": page.pk, "short_answer_ru": "Draft answer", "live": "0"}
        )
        self.assertEqual(response.status_code, 200, response.content)
        page.refresh_from_db()
        self.assertEqual(page.short_answer_ru, "Use lari. Exchange at a bank.")
        self.assertEqual(
            page.get_latest_revision_as_object().short_answer_ru, "Draft answer"
        )

    def test_create_draft_and_invalid_row_roll_back(self):
        values = dict(
            parent_id=self.category.pk,
            title_ru="New?",
            slug="new-question",
            short_answer_ru="Answer",
            why_points_ru=json.dumps(
                [{"type": "point", "value": "One"}, {"type": "point", "value": "Two"}]
            ),
            answered_at="21.09.2026",
            checked_at="22.09.2026",
            live="0",
        )
        response = self.row(values)
        self.assertEqual(response.status_code, 200, response.content)
        page = FaqQuestionPage.objects.get(slug="new-question")
        self.assertFalse(page.live)
        with patch.object(
            FaqQuestionPage, "save_revision", side_effect=ValueError("failed")
        ):
            response = self.row(dict(values, slug="failed-question"))
        self.assertEqual(response.status_code, 400)
        self.assertFalse(
            FaqQuestionPage.objects.filter(slug="failed-question").exists()
        )

    def test_blank_optional_import_clears_value(self):
        page = self.question(tip="Old advice")
        response = self.row({"id": page.pk, "tip_ru": ""})
        self.assertEqual(response.status_code, 200, response.content)
        page.refresh_from_db()
        self.assertEqual(page.tip_ru, "")

    def test_import_rejects_missing_reference_and_locked_page(self):
        page = self.question()
        response = self.row({"id": page.pk, "cta_page": "9999999"})
        self.assertEqual(response.status_code, 400)

        page.locked = True
        page.save()
        response = self.row({"id": page.pk, "tip_ru": "changed"})
        self.assertEqual(response.status_code, 400)

    def test_existing_named_stream_handler_keeps_precedence(self):
        page = self.question()
        with patch("core.field_handlers.why_points_ru_handler", create=True) as handler:
            run_field_handler(page, "why_points_ru", "custom-format")
        handler.assert_called_once_with(page, "why_points_ru", "custom-format")

    def test_import_does_not_publish_or_destroy_pending_draft(self):
        page = self.question()
        page.tip = "Pending advice"
        page.save_revision()
        response = self.row({"id": page.pk, "short_answer_ru": "Different live answer"})
        self.assertEqual(response.status_code, 400)
        page.refresh_from_db()
        self.assertEqual(page.short_answer_ru, "Use lari. Exchange at a bank.")
        self.assertEqual(page.get_latest_revision_as_object().tip_ru, "Pending advice")
        response = self.row(
            {"id": page.pk, "short_answer_ru": "New draft answer", "live": 0}
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(page.get_latest_revision_as_object().tip_ru, "Pending advice")

    def test_csv_tags_round_trip_and_blank_clearing(self):
        page = self.question()
        response = self.row({"id": page.pk, "tags": "money, travel"})
        self.assertEqual(response.status_code, 200, response.content)
        page.refresh_from_db()
        self.assertEqual(set(page.tags.names()), {"money", "travel"})
        response = self.row({"id": page.pk, "tags": ""})
        self.assertEqual(response.status_code, 200, response.content)
        page.refresh_from_db()
        self.assertFalse(page.tags.exists())

    def test_optional_cta_and_unpublished_target(self):
        page = self.question(cta_page=self.category)
        context = page.get_context(self.request)
        self.assertEqual(context["cta_text"], self.category.title)
        self.category.live = False
        self.category.save()
        self.assertNotIn("cta_href", page.get_context(self.request))
        page.cta_page = None
        page.cta_url = "https://example.com/read-more"
        self.assertEqual(page.get_context(self.request)["cta_href"], page.cta_url)

    def test_common_translation_behavior(self):
        page = self.question(
            short_answer_en="English answer", title_en="English question"
        )
        with override("en"):
            loaded = FaqQuestionPage.objects.get(pk=page.pk)
            self.assertEqual(loaded.short_answer, "English answer")
            self.assertEqual(loaded.title, "English question")
        with override("ka"):
            loaded = FaqQuestionPage.objects.get(pk=page.pk)
            self.assertEqual(loaded.short_answer, "Use lari. Exchange at a bank.")

    def test_video_loads_only_after_click(self):
        page = self.question(video_url="https://youtu.be/abcdefghijk")
        html = page.serve(self.request).render().content.decode()
        self.assertIn('data-faq-video="abcdefghijk"', html)
        self.assertNotIn("<iframe", html)
        self.assertNotIn("youtube-nocookie.com", html)

    def test_category_uses_strict_pagination(self):
        self.question()
        for query in ["?page=0", "?page=2", "?page=abc", "?page=1&page=2"]:
            with self.subTest(query=query), self.assertRaises(Http404):
                request = self.factory.get("/faq/money/" + query)
                request.site = self.site
                self.category.get_context(request)

    def test_question_body_is_searchable_by_existing_backend(self):
        page = self.question(short_answer="Uniqueplatypus currency answer")
        backend = get_search_backend()
        backend.add(page)
        self.assertIn(
            page.pk,
            [result.pk for result in Page.objects.live().search("Uniqueplatypus")],
        )

    def test_block_renders_and_omits_empty_selection(self):
        page = self.question(is_popular=True)
        block = FaqQuestionsBlock()
        value = block.to_python(
            {"title": "Questions", "mode": "popular", "count": 6, "questions": []}
        )
        html = block.render(value, {"request": self.request})
        self.assertIn(page.title, html)
        self.assertIn("Questions", html)
        self.assertNotIn(page.title, block.render(value, {}))

    def test_block_excludes_private_and_other_site_questions(self):
        visible = self.question("visible")
        private = self.question("private")
        PageViewRestriction.objects.create(
            page=private, restriction_type="password", password="secret"
        )
        root = Page.get_first_root_node()
        other_home = root.add_child(
            instance=HomePage(title="Other site", slug="other-site")
        )
        other_index = other_home.add_child(
            instance=FaqIndexPage(title="Other FAQ", slug="faq")
        )
        other_category = other_index.add_child(
            instance=FaqCategoryPage(title="Other", slug="other")
        )
        other = other_category.add_child(
            instance=FaqQuestionPage(
                title="Other question",
                slug="question",
                short_answer="Other site",
                why_points=[("point", "One"), ("point", "Two")],
            )
        )
        block = FaqQuestionsBlock()
        value = block.to_python(
            {
                "title": "Questions",
                "mode": "manual",
                "count": 6,
                "questions": [private.pk, other.pk, visible.pk],
            }
        )
        self.assertEqual(
            [
                q.pk
                for q in block.get_context(value, {"request": self.request})[
                    "questions"
                ]
            ],
            [visible.pk],
        )

    def test_scoped_search_only_returns_public_questions_in_current_site(self) -> None:
        from search.views import search

        visible = self.question(title="Faqscopefixture public")
        draft = self.question(
            slug="draft-search", title="Faqscopefixture draft", live=False
        )
        private = self.question(slug="private-search", title="Faqscopefixture private")
        PageViewRestriction.objects.create(
            page=private, restriction_type="password", password="secret"
        )
        other = Page.get_first_root_node().add_child(
            instance=FaqQuestionPage(
                title="Faqscopefixture other site",
                slug="other-search",
                short_answer="Elsewhere",
                answered_at=date(2026, 9, 21),
                checked_at=date(2026, 9, 22),
            )
        )
        self.category.title = "Faqscopefixture category"
        self.category.save()
        backend = get_search_backend()
        for page in (visible, draft, private, other, self.category):
            backend.add(page)
        request = self.factory.get(
            "/search/", {"query": "Faqscopefixture", "scope": "faq"}
        )
        request.site = self.site
        response = search(request)
        self.assertEqual(
            [page.pk for page in response.context_data["search_results"]], [visible.pk]
        )
        request = self.factory.get("/search/", {"query": "Faqscopefixture"})
        response = search(request)
        self.assertIn(
            self.category.pk,
            [page.pk for page in response.context_data["search_results"]],
        )

    def test_scoped_search_preserves_scope_in_forms_and_pagination(self) -> None:
        from django.utils.translation import gettext

        backend = get_search_backend()
        for number in range(11):
            backend.add(
                self.question(
                    slug=f"scope-{number}", title=f"Faqpagingfixture {number}"
                )
            )
        with override("ru"):
            response = self.client.get(
                reverse("search"), {"query": "Faqpagingfixture", "scope": "faq"}
            )
            self.assertContains(response, gettext("Search questions and answers"))
            self.assertContains(
                response, '<input type="hidden" name="scope" value="faq">', html=True
            )
            self.assertContains(response, "scope=faq&amp;page=2")
            empty = self.client.get(reverse("search"), {"scope": "faq"})
            self.assertContains(empty, gettext("Enter a question or topic."))
            index = self.client.get(self.index.url)
            self.assertContains(
                index, '<input type="hidden" name="scope" value="faq">', html=True
            )

    def test_sidebar_categories_order_visibility_and_active_state(self) -> None:
        earlier = self.index.add_child(
            instance=FaqCategoryPage(
                title="Earlier", slug="earlier", group=self.group, sort_order=0
            )
        )
        self.category.sort_order = 2
        self.category.save()
        draft = self.index.add_child(
            instance=FaqCategoryPage(
                title="Draft category", slug="draft-category", live=False
            )
        )
        private = self.index.add_child(
            instance=FaqCategoryPage(title="Private category", slug="private-category")
        )
        PageViewRestriction.objects.create(
            page=private, restriction_type="password", password="secret"
        )
        question = self.question()
        for page in (self.category, question):
            context = page.get_context(self.request)
            self.assertEqual(
                [item.pk for item in context["sidebar_categories"]],
                [earlier.pk, self.category.pk],
            )
            self.assertEqual(context["sidebar_category"].pk, self.category.pk)
            response = self.client.get(page.url)
            self.assertContains(response, 'aria-current="page"')
            self.assertContains(response, 'class="faq-sidebar"')
            self.assertNotContains(response, draft.title)
            self.assertNotContains(response, private.title)

    def test_sidebar_related_links_inherit_category_and_exclude_private_pages(
        self,
    ) -> None:
        from blog.models import BlogCategoryPage, BlogIndexPage

        root = Page.get_first_root_node()
        blog = self.home.add_child(instance=BlogIndexPage(title="Blog", slug="blog"))
        public = blog.add_child(
            instance=BlogCategoryPage(title="Related blog", slug="related-blog")
        )
        self.category.blog_category = public
        self.category.save()
        question = self.question()
        for page in (self.category, question):
            self.assertEqual(
                [
                    item.pk
                    for item in page.get_context(self.request)["sidebar_related_pages"]
                ],
                [public.pk],
            )
        PageViewRestriction.objects.create(
            page=public, restriction_type="password", password="secret"
        )
        self.assertEqual(
            question.get_context(self.request)["sidebar_related_pages"], []
        )
        PageViewRestriction.objects.filter(page=public).delete()
        public.live = False
        public.save()
        self.assertEqual(
            question.get_context(self.request)["sidebar_related_pages"], []
        )
        public.live = True
        public.save()
        blog.move(root, pos="last-child")
        self.assertEqual(
            question.get_context(self.request)["sidebar_related_pages"], []
        )

    def test_index_counts_exclude_drafts_private_and_other_trees(self):
        self.question("public-one")
        self.question("public-two")
        self.question("unpublished", live=False)
        private = self.question("restricted")
        PageViewRestriction.objects.create(
            page=private, restriction_type="password", password="secret"
        )
        empty = self.index.add_child(
            instance=FaqCategoryPage(title="Empty", slug="empty")
        )
        root = Page.get_first_root_node()
        other_home = root.add_child(
            instance=HomePage(title="Elsewhere", slug="elsewhere")
        )
        other_index = other_home.add_child(
            instance=FaqIndexPage(title="FAQ", slug="faq")
        )
        other_category = other_index.add_child(
            instance=FaqCategoryPage(title="Other", slug="other")
        )
        other_category.add_child(
            instance=FaqQuestionPage(
                title="Other question",
                slug="other-question",
                short_answer="Elsewhere",
                why_points=[("point", "One"), ("point", "Two")],
            )
        )
        context = self.index.get_context(self.request)
        counts = {
            category.pk: category.question_count
            for _, categories in context["category_groups"]
            for category in categories
        }
        self.assertEqual(counts, {self.category.pk: 2, empty.pk: 0})

    def test_thousand_questions_return_one_count_row_and_bounded_lists(self):
        from faq.models import question_counts

        for number in range(1000):
            self.category.add_child(
                instance=FaqQuestionPage(
                    title=f"Scale question {number}",
                    slug=f"scale-{number}",
                    short_answer="Short answer. More information.",
                    is_popular=True,
                    why_points=[("point", "One"), ("point", "Two")],
                )
            )
        with CaptureQueriesContext(connection) as queries:
            counts = question_counts(self.index, self.site)
        self.assertEqual(len(queries), 2)
        aggregate_queries = [
            query["sql"] for query in queries if "COUNT(" in query["sql"]
        ]
        self.assertEqual(len(aggregate_queries), 1)
        self.assertIn("GROUP BY", aggregate_queries[0])
        self.assertEqual(counts, {self.category.path: 1000})
        context = self.index.get_context(self.request)
        self.assertEqual(len(context["popular_questions"]), 6)
        category_context = self.category.get_context(self.request)
        self.assertEqual(category_context["questions"].paginator.count, 1000)
        self.assertEqual(len(category_context["questions"]), 16)

    def test_question_summaries_defer_long_answers_without_lazy_card_queries(self):
        from faq.models import public_questions

        self.question(
            details_ru="<p>" + "Long answer " * 1000 + "</p>",
            tip_en="<p>English advice</p>",
            short_answer_en="English summary. Details.",
            title_en="English question",
        )
        for language, expected in (("en", "English summary."), ("ka", "Use lari.")):
            with self.subTest(language=language), override(language):
                with self.assertNumQueries(2):
                    questions = list(public_questions(self.site))
                deferred = questions[0].get_deferred_fields()
                for field in ("details_ru", "tip_en", "why_points_ru", "sources"):
                    self.assertIn(field, deferred)
                with self.assertNumQueries(0):
                    self.assertEqual(questions[0].answer_excerpt, expected)
                    self.assertTrue(questions[0].title)
                with CaptureQueriesContext(connection) as queries:
                    html = render_to_string(
                        "faq/includes/question_list.html",
                        {"questions": questions, "request": self.request},
                    )
                self.assertIn(expected, html)
                self.assertFalse(
                    any(
                        'FROM "faq_faqquestionpage"' in query["sql"]
                        for query in queries
                    )
                )

    def test_misconception_requires_both_parts_in_each_language(self):
        page = self.question()
        for language in ("ru", "en", "ka"):
            for missing in ("myth", "myth_truth"):
                with self.subTest(language=language, missing=missing):
                    page = FaqQuestionPage.objects.get(pk=page.pk)
                    present = "myth_truth" if missing == "myth" else "myth"
                    setattr(page, f"{present}_{language}", "<p>Text</p>")
                    with self.assertRaises(ValidationError) as error:
                        page.clean()
                    self.assertIn(f"{missing}_{language}", error.exception.message_dict)
        page = FaqQuestionPage.objects.get(pk=page.pk)
        page.myth_ru = "<p>Myth</p>"
        page.myth_truth_ru = "<p>Truth</p>"
        page.clean()

    def test_incomplete_misconception_import_preserves_live_and_revision(self):
        page = self.question()
        revision_id = page.latest_revision_id
        response = self.row({"id": page.pk, "myth_ru": "<p>Unpaired</p>", "live": "0"})
        self.assertEqual(response.status_code, 400)
        page.refresh_from_db()
        self.assertFalse(page.myth_ru)
        self.assertEqual(page.latest_revision_id, revision_id)

    def test_lone_advice_uses_full_column(self):
        for fields in ({"tip": "<p>Advice</p>"}, {"may_differ": "<p>Exception</p>"}):
            with self.subTest(fields=fields):
                page = self.question(slug="single-" + next(iter(fields)), **fields)
                html = page.serve(self.request).render().content.decode()
                self.assertNotIn('class="col-sm-6 col-12"', html)

    def test_admin_form_reports_missing_translated_correction(self):
        from wagtail.fields import StreamField

        page = self.question()
        form_class = FaqQuestionPage.get_edit_handler().get_form_class()
        data = {
            "title_ru": page.title_ru,
            "slug": page.slug,
            "short_answer_ru": page.short_answer_ru,
            "myth_en": json.dumps(
                {
                    "blocks": [
                        {
                            "key": "myth",
                            "text": "Misconception",
                            "type": "unstyled",
                            "depth": 0,
                            "inlineStyleRanges": [],
                            "entityRanges": [],
                        }
                    ],
                    "entityMap": {},
                }
            ),
            "answered_at": "2026-09-21",
            "checked_at": "2026-09-22",
        }
        for field in FaqQuestionPage._meta.fields:
            if isinstance(field, StreamField):
                data[f"{field.name}-count"] = "0"
        form = form_class(
            data=data, instance=page, for_user=self.user, parent_page=self.category
        )
        self.assertFalse(form.is_valid())
        self.assertIn("myth_truth_en", form.errors)
