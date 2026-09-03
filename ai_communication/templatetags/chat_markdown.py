import markdown as md
import bleach
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

ALLOWED_TAGS = [
    "p", "strong", "em", "ul", "ol", "li", "br",
    "code", "pre", "a", "blockquote", "h3", "h4",
]
ALLOWED_ATTRS = {"a": ["href", "title", "rel", "target"]}


@register.filter(name="render_markdown")
def render_markdown(text):
    """Convert the AI assistant's markdown reply into sanitized HTML.

    Only ever apply this to bot/assistant messages, never to raw user
    input, to avoid rendering unsanitized user-supplied HTML.
    """
    if not text:
        return ""
    html = md.markdown(text, extensions=["nl2br", "sane_lists"])
    clean_html = bleach.clean(html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS, strip=True)
    return mark_safe(clean_html)