from django.http import Http404, JsonResponse
from django.template.loader import render_to_string

from gallery.models import GalleryPostPage
from gallery.services import get_gallery_images_service


def load_more_images(request):
    page_number = request.GET.get("page")
    page_id = request.GET.get("page-id")

    if not page_id or not page_id.isdigit():
        raise Http404

    if not page_number or not page_id.isdigit():
        raise Http404

    try:
        page = GalleryPostPage.objects.get(pk=page_id)
    except GalleryPostPage.DoesNotExist:
        raise Http404

    images = get_gallery_images_service(page, 24, page_number)

    if not images:
        raise Http404

    response = []

    for image in images:
        image_html = render_to_string(
            "gallery/includes/image-item.html", {"image": image}
        )
        response.append(image_html)

    return JsonResponse(response, safe=False)
