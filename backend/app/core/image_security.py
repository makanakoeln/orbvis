"""Image content validation — magic-byte checks and SVG XML sandboxing.

These helpers reject uploads that lie about their Content-Type, and — for SVGs —
block the usual XXE / billion-laughs footguns by parsing with defusedxml.
"""

from __future__ import annotations

from defusedxml import ElementTree as DefusedET
from defusedxml.common import DefusedXmlException

# Icons are rendered as-is in the board. GIF is intentionally excluded — we
# don't want animated icons flickering in map overviews.
ICON_MIME_TYPES = frozenset({"image/png", "image/jpeg", "image/svg+xml", "image/webp"})
ICON_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".svg", ".webp"})

# Background images of static boards may include GIF — a common legacy
# asset format for imported maps.
BACKGROUND_MIME_TYPES = frozenset(
    {"image/png", "image/jpeg", "image/gif", "image/svg+xml", "image/webp"}
)
BACKGROUND_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"})

# Raster magic bytes
_PNG_MAGIC = b"\x89PNG"
_JPEG_MAGIC = b"\xff\xd8\xff"
_GIF_MAGIC = (b"GIF87a", b"GIF89a")
_WEBP_RIFF = b"RIFF"
_WEBP_MARK = b"WEBP"


# Real-world SVGs (Illustrator/Inkscape exports) often carry an XML
# declaration, a DOCTYPE, and licence comments before the root element, so the
# sniff window has to be generous — a 512-byte window missed those exports.
_SVG_SNIFF_BYTES = 65536


def _looks_like_svg_header(content: bytes) -> bool:
    """Quick byte-level sniff — presence of '<svg' in the leading bytes."""
    return b"<svg" in content[:_SVG_SNIFF_BYTES].lower()


# SVG elements / attributes that can execute scripts. Rejected even though
# defusedxml accepts them — once an SVG sits under /images and is opened with
# image/svg+xml, scripts run with the application's origin (XSS). ``use`` is
# *not* blanket-rejected (internal `#fragment` references are both safe and
# common); instead its href is constrained below.
_SVG_FORBIDDEN_TAGS = frozenset({"script", "foreignObject"})
_SVG_FORBIDDEN_ATTR_PREFIXES = ("on",)

# Schemes that can execute or read local resources — never allowed in any href.
_DANGEROUS_URI_SCHEMES = ("javascript:", "vbscript:", "file:")
# data: URIs are allowed only for embedded raster images. text/html and
# image/svg+xml data URIs can carry script, so they stay rejected.
_SAFE_DATA_URI_PREFIXES = (
    "data:image/png",
    "data:image/jpeg",
    "data:image/jpg",
    "data:image/gif",
    "data:image/webp",
)


def _href_is_safe(value: str, *, is_use: bool) -> bool:
    """Whether an href / xlink:href value is safe for a sandboxed SVG icon."""
    v = value.strip()
    low = v.lower()
    if low.startswith(_DANGEROUS_URI_SCHEMES):
        return False
    if low.startswith("data:"):
        # Only embedded rasters; svg+xml/text data URIs could carry script.
        return low.startswith(_SAFE_DATA_URI_PREFIXES)
    if is_use:
        # <use> may only reference local fragments — a remote target lets the
        # icon pull in (and run) external SVG content.
        return v.startswith("#")
    return True


def is_safe_svg(content: bytes) -> bool:
    """Parse *content* as SVG with defusedxml; reject script vectors.

    Must be called only after a byte-level ``<svg`` sniff — defusedxml parses any
    well-formed XML, but only a real ``<svg>`` root element is acceptable here.

    A DOCTYPE is permitted (the standard SVG DTD reference is ubiquitous in
    exported assets) but ``forbid_entities``/``forbid_external`` stay on, so
    billion-laughs entity expansion and XXE external entities are still blocked.
    The parsed tree is then walked to reject ``<script>``, on-event attributes,
    ``<foreignObject>``, remote ``<use>`` targets, and script-bearing URIs.
    """
    parser = DefusedET.DefusedXMLParser(
        forbid_dtd=False, forbid_entities=True, forbid_external=True
    )
    try:
        parser.feed(content)
        root = parser.close()
    except (DefusedXmlException, DefusedET.ParseError):
        return False
    if root.tag.rsplit("}", 1)[-1] != "svg":
        return False
    for elem in root.iter():
        local_tag = elem.tag.rsplit("}", 1)[-1]
        if local_tag in _SVG_FORBIDDEN_TAGS:
            return False
        is_use = local_tag == "use"
        for attr_name, attr_val in elem.attrib.items():
            local_attr = attr_name.rsplit("}", 1)[-1].lower()
            if local_attr.startswith(_SVG_FORBIDDEN_ATTR_PREFIXES):
                return False
            if local_attr in ("href", "xlink:href") and not _href_is_safe(attr_val, is_use=is_use):
                return False
    return True


def is_valid_image(content: bytes, *, allow_svg: bool = True, allow_gif: bool = True) -> bool:
    """True if *content* starts with a recognised raster header or is a safe SVG.

    ``allow_gif=False`` for icon uploads — ICON_MIME_TYPES excludes GIF (no
    animated icons), and without the flag a GIF body with a faked PNG
    Content-Type would slip through the magic-byte check.
    """
    if not content:
        return False
    head = content[:16]
    if head[:4] == _PNG_MAGIC:
        return True
    if head[:3] == _JPEG_MAGIC:
        return True
    if allow_gif and head[:6] in _GIF_MAGIC:
        return True
    if head[:4] == _WEBP_RIFF and content[8:12] == _WEBP_MARK:
        return True
    if allow_svg and _looks_like_svg_header(content):
        return is_safe_svg(content)
    return False
