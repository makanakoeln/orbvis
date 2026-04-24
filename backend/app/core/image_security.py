"""Image content validation — magic-byte checks and SVG XML sandboxing.

These helpers reject uploads that lie about their Content-Type, and — for SVGs —
block the usual XXE / billion-laughs footguns by parsing with defusedxml.
"""

from __future__ import annotations

from defusedxml import ElementTree as DefusedET
from defusedxml.common import DefusedXmlException

# Raster magic bytes
_PNG_MAGIC = b"\x89PNG"
_JPEG_MAGIC = b"\xff\xd8\xff"
_GIF_MAGIC = (b"GIF87a", b"GIF89a")
_WEBP_RIFF = b"RIFF"
_WEBP_MARK = b"WEBP"


def _looks_like_svg_header(content: bytes) -> bool:
    """Quick byte-level sniff — presence of '<svg' in the first 512 bytes."""
    return b"<svg" in content[:512].lower()


def is_safe_svg(content: bytes) -> bool:
    """Parse *content* as SVG with defusedxml; reject DTDs and external entities.

    Must be called only after a byte-level ``<svg`` sniff — defusedxml parses any
    well-formed XML, but only a real ``<svg>`` root element is acceptable here.

    DTDs are rejected outright (even benign ones) so that a future DefinedET
    upgrade that loosens entity handling cannot silently open a hole.
    """
    parser = DefusedET.DefusedXMLParser(forbid_dtd=True, forbid_entities=True)
    try:
        parser.feed(content)
        root = parser.close()
    except (DefusedXmlException, DefusedET.ParseError):
        return False
    # SVG root is either 'svg' or '{http://www.w3.org/2000/svg}svg'.
    local = root.tag.rsplit("}", 1)[-1]
    return local == "svg"


def is_valid_image(content: bytes, *, allow_svg: bool = True) -> bool:
    """True if *content* starts with a recognised raster header or is a safe SVG."""
    if not content:
        return False
    head = content[:16]
    if head[:4] == _PNG_MAGIC:
        return True
    if head[:3] == _JPEG_MAGIC:
        return True
    if head[:6] in _GIF_MAGIC:
        return True
    if head[:4] == _WEBP_RIFF and content[8:12] == _WEBP_MARK:
        return True
    if allow_svg and _looks_like_svg_header(content):
        return is_safe_svg(content)
    return False
