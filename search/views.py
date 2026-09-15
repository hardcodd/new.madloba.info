from django.http import HttpRequest
from django.template.response import TemplateResponse
from wagtail.contrib.search_promotions.models import Query
from wagtail.models import Page

from core.pagination import paginate

# To enable logging of search queries for use with the "Promoted search results" module
# <https://docs.wagtail.org/en/stable/reference/contrib/searchpromotions.html>
# uncomment the following line and the lines indicated in the search function
# (after adding wagtail.contrib.search_promotions to INSTALLED_APPS):

# from wagtail.contrib.search_promotions.models import Query


def search(request: HttpRequest) -> TemplateResponse:
    """Return search results with strict public pagination."""
    search_query = request.GET.get("query", None)

    # Search
    if search_query:
        search_results = Page.objects.live().defer_streamfields().search(search_query)

        # To log this query for use with the "Promoted search results" module:

        query = Query.get(search_query)
        query.add_hit()

    else:
        search_results = Page.objects.none()

    # Pagination
    search_results = paginate(request, search_results, 10)

    return TemplateResponse(
        request,
        "search/search.html",
        {
            "search_query": search_query,
            "search_results": search_results,
        },
    )
