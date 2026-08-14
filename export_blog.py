import csv
import os

from django.conf import settings

from blog.models import BlogPostPage

CSV_FILE = "blog_posts.csv"
OUTPUT_DIR = os.path.join(settings.BASE_DIR, "_exports")

posts = BlogPostPage.objects.live()
post_count = posts.count()

with open(os.path.join(OUTPUT_DIR, CSV_FILE), "w", newline="") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(["Title", "URL", "Category"])
    for i, post in enumerate(posts):
        writer.writerow([post.title, post.full_url, post.get_parent().title])
        print(f"Exported post {i + 1} of {post_count}", end="\r")
