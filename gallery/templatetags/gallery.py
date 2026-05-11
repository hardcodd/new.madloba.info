from django import template

from gallery.models import GalleryPostPage, GalleryCategoryPage
from gallery.services import (
    get_gallery_images_service,
    get_paginated_galleries_service,
    get_first_gallery_image_service,
    get_gallery_categories_service,
)

register = template.Library()


@register.simple_tag(takes_context=True)
def get_gallery_images(context, count=24):
    page = context["page"]
    request = context["request"]
    page_num = request.GET.get("page", 1)
    return get_gallery_images_service(page, count, page_num)


@register.simple_tag(takes_context=True)
def get_paginated_galleries(context, count=24):
    page = context["page"]
    request = context["request"]
    page_num = request.GET.get("page", 1)
    return get_paginated_galleries_service(page, count, page_num)


@register.simple_tag
def get_first_gallery_image(gallery: GalleryPostPage):
    return get_first_gallery_image_service(gallery)


@register.simple_tag
def get_gallery_categories(gallery_category: GalleryCategoryPage):
    return get_gallery_categories_service(gallery_category)
