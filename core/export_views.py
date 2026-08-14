from django.shortcuts import render


def export_pages(request):
    return render(request, "core/export_pages.html", {})
