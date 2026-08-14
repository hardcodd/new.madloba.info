from django.urls import path

from core.views import import_page

app_name = "core"
urlpatterns = [
    path("import-page/", import_page, name="import_page"),
]
