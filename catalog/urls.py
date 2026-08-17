from django.urls import path

from .views import (
    get_organizations_data,
    organizations,
    search_cities,
)

app_name = "catalog"
urlpatterns = [
    path("search-cities/", search_cities, name="search_cities"),
    path("organizations/", organizations, name="organizations"),
    path(
        "get-organizations-data/", get_organizations_data, name="get_organizations_data"
    ),
]
