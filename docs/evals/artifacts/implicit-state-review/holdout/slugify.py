"""URL slugs (sample under review)."""
import re


def slugify(title, max_len=40):
    """Lower-case, dash-separated slug of at most max_len characters."""
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    if len(slug) > max_len:
        slug = slug[: max_len + 1].rstrip("-")
    return slug
