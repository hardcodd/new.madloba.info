# FAQ application

FAQ uses the existing Wagtail page tree: Home → FAQ index → category → question.
Create the index with slug `faq`; category and question slugs use normal Wagtail
routing. Category groups are editable snippets with translated titles and order.
Only one FAQ index can be created under a home page.

## Editing

Questions contain a plain short answer, two to five reasons, optional rich-text
details, tips, exceptions, a misconception and its correction, alternative
question phrasings, dated sources, dates, images, related questions and a CTA.
Alternative phrasings share the short answer; they are not separate answers.
Empty optional sections are hidden. A misconception and its correction must be
filled together in each language; incomplete pairs produce a field error in the
editor and CSV import. A lone tip or exception occupies the full content width.
Question and category cards reuse native
site surfaces, theme colors, radii and shadows; grids collapse on small screens.
Related questions default to public siblings
when no manual choices are supplied, showing four questions ordered by check
date. Editors can replace that list with up to five manual selections and clear
the field to restore automatic selection. The native question editor groups
fields into Answer, Answer details, Sources (including dates), Links and media,
and Promote tabs. All translations use the existing language picker;
SEO, social images, tags and popularity are in Promote. Native Page settings are retained; Wagtail 7 hides the standalone Settings tab
when it contains only its native panels. Scheduling is available through the
status side panel and its Set schedule action.
Category images provide a cover fallback;
a question's social image can override its normal cover for link previews.

Introductions, details, tips, exceptions and misconception text use the same
full rich-text editor as existing site text blocks, including images and embeds.
Short answers and alternative question phrasings remain plain text for consistent
metadata and FAQ schema. Source names follow the existing admin language picker,
including newly added source blocks; their URL and check date stay shared.

Category and question pages share a category navigation panel with the current
category highlighted in a tinted outlined row. Navigation rows have visible
gaps; hover uses a white surface with a border and shadow, distinct from the
active state. Categories follow the configured group/category order. The FAQ index is reached
through the existing breadcrumb link; no duplicate sidebar action is shown.
Optional related blog/catalog links come from the current category and include
only live public pages within the current site. No additional editor fields are
required. Short desktop sidebars follow scrolling below the fixed header. Panels taller
than the available viewport stay in normal page flow without internal scrolling.
Mobile sidebars always stay in normal flow.

YouTube URLs are validated. The iframe is created only after the visitor presses
Play. Actual playback depends on the video's availability and embedding policy.

Add the FAQ questions block manually to the home page. Choose latest publication,
editorially marked popular questions, latest check date, or manual ordered choices.
The block selects only live public questions within the current site and allows
1–24 results. Popular means an editorial flag, not an analytics counter.

Translation, fallback, search, permissions, drafts, publication and SEO follow
the engine's normal behavior. The FAQ index searches questions through the shared
search endpoint with `scope=faq`: only live public questions in the current site
are returned. The results form and pagination retain this scope; ordinary site
search remains unchanged. No advertising flag, external registry identifier,
question-type filter, collections or separate search service is introduced.

## Query cost

Category counters use [SQL aggregation](https://docs.djangoproject.com/en/5.2/topics/db/aggregation/)
over public questions in the current FAQ tree and site. The application receives
one count row per populated category; displayed empty categories get zero. It
does not load one path per question. Counts reflect current content without a
cache or denormalized counters. Counting still requires database work over the
qualifying rows.

Question cards defer StreamFields and long rich-text translations, and do not
join image records. All title/short-answer translations remain loaded so language
fallback does not add queries per card. Category navigation defers introductions;
related blog/catalog links use shared Page fields without fetching full specific
content. Question detail pages continue to load their full answer. The index
shows at most six popular questions, category pages paginate at 16, and the home
block remains capped at 24. Regression tests include 1,000 questions, aggregate
result cardinality, visibility and translation fallback. This is a local
correctness/query-volume check, not a production load benchmark.

## Existing CSV import/export

Use the existing page importer/exporter with `faq.models.FaqQuestionPage` (or the
index/category model). Existing pages use Wagtail `id`; new pages use `parent_id`.
Foreign keys and image/page references use existing IDs. Dates accept ISO
`YYYY-MM-DD` or `DD.MM.YYYY`; export emits ISO dates. Tags use comma-separated names.
Rich text exports native HTML and repeatable fields export Wagtail JSON, retaining
their structure and order. Prefer a native exported row as the import template.

Translated columns retain normal suffixes, such as `short_answer_ru`. Sources
share a URL/check date and have `name_<language>` values for configured languages.
Mapped empty optional FAQ fields are cleared; unmapped fields are left unchanged.
StreamField JSON is validated before saving. Each imported row is transactional.

`live=false` saves a draft revision; `live=true` publishes. Omitting `live` retains
the existing importer's publish default. Editing and publication require normal
Wagtail permissions. Locked pages, workflows, aliases, scheduled publication and
publication over an existing pending draft are rejected to prevent accidental
overwrites. Existing drafts can be updated with `live=false`.

## Deployment and verification

Apply the reviewed local migrations using `manage.py migrate` during deployment:
`faq.0001_initial`, `faq.0002_alter_faqcategorypage_intro_and_more` and `home.0006_alter_homepage_content_alter_homepage_content_en_and_more`.
The second FAQ migration wraps existing plain text safely as HTML, including
draft revisions. Its reverse conversion returns text and drops rich formatting.
Run the engine's normal `update_index` and sitemap generation when content is
introduced. Sitemap selectors include `faq_index`, `faq_categories` and
`faq_questions`. This app does not automatically create or publish site content.

Focused regression tests cover hierarchy, templates, selection, privacy, search,
translation fallback, JSON-LD safety, CSV round trips, references, dates, drafts
and import failures. Run `manage.py test faq.tests` or the full project suite.
