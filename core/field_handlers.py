import json
from datetime import datetime
from typing import Any

from django.db.models import Model
from django.db.models.fields.related import ForeignKey
from django.utils.text import slugify
from django.utils.dateparse import parse_date
from django.utils.html import escape
from wagtail.fields import StreamField

from catalog.utils import get_start_end_day
from core.utils import get_weekday_number

RAW_TEXT_FIELD_NAME_PARTS = frozenset(
    {
        "search",
        "website",
        "social",
    }
)


def should_preserve_plain_text(field: str) -> bool:
    return any(part in field for part in RAW_TEXT_FIELD_NAME_PARTS)


def charfield_handler(obj: Model, field: str, value: Any) -> None:
    setattr(obj, field, value)


def slugfield_handler(obj: Model, field: str, value: Any) -> None:
    slug = slugify(str(value).strip(), allow_unicode=True)

    if not slug:
        return

    setattr(obj, field, slug)


def textfield_handler(obj: Model, field: str, value: Any) -> None:
    text = str(value)

    plain_fields = getattr(obj, "csv_plain_text_fields", set())
    if any(field == name or field.startswith(f"{name}_") for name in plain_fields):
        setattr(obj, field, text)
        return

    if should_preserve_plain_text(field):
        setattr(obj, field, text)
        return

    paragraphs = [
        paragraph.strip() for paragraph in text.split("\n\n") if paragraph.strip()
    ]

    if not paragraphs:
        return

    setattr(obj, field, "<p>" + "</p><p>".join(paragraphs) + "</p>")


def booleanfield_handler(obj: Model, field: str, value: Any) -> None:
    setattr(
        obj,
        field,
        value in [True, "true", "True", 1, "1", "yes", "on", "Yes", "On"],
    )


def working_hours_handler(obj: Model, field: str, value: Any) -> None:
    if not value:
        return

    try:
        working_hours = json.loads(value)
    except json.JSONDecodeError as error:
        raise ValueError("Invalid working hours JSON") from error

    if not isinstance(working_hours, dict):
        raise ValueError("Invalid working hours format")

    days = []

    for day, hours in working_hours.items():
        normalized_hours = str(hours).strip().lower()

        if normalized_hours == "closed":
            days.append(
                {
                    "type": "day",
                    "value": {
                        "day": get_weekday_number(day),
                        "end": None,
                        "start": None,
                        "holiday": True,
                        "last_client": False,
                    },
                }
            )
        elif normalized_hours == "open 24 hours":
            days.append(
                {
                    "type": "day",
                    "value": {
                        "day": get_weekday_number(day),
                        "end": "23:59",
                        "start": "00:00",
                        "holiday": False,
                        "last_client": False,
                    },
                }
            )
        else:
            try:
                start, end = get_start_end_day(hours)
            except ValueError as error:
                raise ValueError(f"Invalid working hours format for {day}") from error

            days.append(
                {
                    "type": "day",
                    "value": {
                        "day": get_weekday_number(day),
                        "end": end,
                        "start": start,
                        "holiday": False,
                        "last_client": False,
                    },
                }
            )

    setattr(obj, field, days)


def located_in_handler(obj: Model, field: str, value: Any) -> None:
    model_field = obj._meta.get_field(field)

    if not isinstance(model_field, ForeignKey):
        raise ValueError(f"{field!r} is not a ForeignKey field")

    related_model = model_field.related_model

    if related_model is None:
        raise ValueError(f"Could not resolve related model for {field!r}")

    try:
        related_id = int(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"Invalid {field} ID") from error

    try:
        related_obj = related_model.objects.get(id=related_id)
    except related_model.DoesNotExist as error:
        raise ValueError(f"Invalid {field} ID") from error

    setattr(obj, field, related_obj)


def foreignkey_handler(obj: Model, field: str, value: Any) -> None:
    """Resolve an existing relation by its database ID; never create targets."""
    located_in_handler(obj, field, value)


def datefield_handler(obj: Model, field: str, value: Any) -> None:
    """Read ISO dates and the engine's exported day.month.year dates."""
    text = str(value).strip()
    result = parse_date(text)
    if result is None:
        result = datetime.strptime(text, "%d.%m.%Y").date()
    setattr(obj, field, result)


def richtextfield_handler(obj: Model, field: str, value: Any) -> None:
    """Keep native rich text markup or escape plain text as one paragraph."""
    text = str(value)
    setattr(
        obj, field, text if text.lstrip().startswith("<") else f"<p>{escape(text)}</p>"
    )


def streamfield_handler(obj: Model, field: str, value: Any) -> None:
    """Validate native StreamField JSON, including chooser targets and block rules."""
    model_field = obj._meta.get_field(field)
    if not isinstance(model_field, StreamField):
        raise ValueError("Expected a StreamField")
    data = json.loads(value) if isinstance(value, str) else value
    if not isinstance(data, list):
        raise ValueError("Expected a JSON list of blocks")
    allowed = model_field.stream_block.child_blocks
    if any(
        not isinstance(item, dict)
        or item.get("type") not in allowed
        or "value" not in item
        for item in data
    ):
        raise ValueError("Unknown or malformed block")
    stream = model_field.to_python(data)
    # Resolving choosers may return None for deleted/nonexistent references;
    # block validation rejects required missing targets before any database write.
    model_field.stream_block.clean(stream)
    setattr(obj, field, stream)


def tags_handler(obj: Model, field: str, value: Any) -> None:
    """Import the existing comma-separated tag-name export format."""
    names = list(
        dict.fromkeys(name.strip() for name in str(value).split(",") if name.strip())
    )
    getattr(obj, field).set(names)
