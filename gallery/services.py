from django.core.paginator import Paginator

from gallery.models import GalleryPostPage, GalleryCategoryPage, GalleryIndexPage


def get_gallery_images_service(page: GalleryPostPage, count=24, page_num=1):
    images = page.specific.images.all()
    paginator = Paginator(images, count)
    return paginator.get_page(page_num)


def get_paginated_galleries_service(page: GalleryCategoryPage, count=24, page_num=1):
    galleries = page.get_children().type(GalleryPostPage)
    paginator = Paginator(galleries, count)
    return paginator.get_page(page_num)


def get_first_gallery_image_service(gallery: GalleryPostPage):
    return gallery.specific.images.first()


def get_gallery_categories_service(page: GalleryIndexPage | GalleryCategoryPage):
    return page.get_children().type(GalleryCategoryPage)
