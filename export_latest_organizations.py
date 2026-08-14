import csv

from catalog.models import Organization

DATE_FROM = "2026-07-14"

orgs = Organization.objects.filter(first_published_at__gte=DATE_FROM)

i = 0
with open(f"_ids/{DATE_FROM}_organizations.csv", "w") as f:
    writer = csv.writer(f)
    for org in orgs:
        i += 1
        writer.writerow([org.id])
        print(f"{i} of {orgs.count()}")
