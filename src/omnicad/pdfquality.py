"""Independent checks and a narrow repair for a known AutoCAD PDF catalog issue."""
import io
import re

def strict_reader(content):
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(content), strict=True)
    if reader.is_encrypted:
        raise ValueError("Encrypted PDFs require a separate review")
    _ = reader.root_object, reader.metadata
    for page in reader.pages:
        _ = page.mediabox, page.cropbox
        streams = page.get_contents()
        if streams is not None:
            _ = streams.operations
    return reader


def repair_plot(source, output):
    """Keep the first PageMode and preserve all byte offsets. Write only on repair."""
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError

    original = source.read_bytes()
    try:
        strict_reader(original)
    except PdfReadError as exc:
        if not re.search(r"Multiple definitions.* /PageMode(?:\s|$)", str(exc)):
            raise ValueError(f"Unsupported PDF structure error: {exc}") from exc
    else:
        return {"state": "unchanged"}
    if re.search(rb"/(?:Sig|ByteRange)\b", original):
        raise ValueError("Signed or signature-bearing PDFs cannot be repaired")

    reader = PdfReader(io.BytesIO(original))
    if reader.is_encrypted:
        raise ValueError("Encrypted PDFs cannot be repaired")
    root = reader.trailer.raw_get("/Root")
    offset = reader.xref.get(root.generation, {}).get(root.idnum)
    if offset is None:
        raise ValueError("PDF catalog must be a plain indirect object")
    header = re.match(rb"\d+\s+\d+\s+obj\s*", original[offset:offset+128])
    if not header:
        raise ValueError("Unexpected PDF catalog offset")
    start = offset + header.end()
    end = original.find(b"endobj", start, start+65536)
    if end < 0:
        raise ValueError("PDF catalog boundary is unavailable")
    modes = _catalog_modes(original[start:end])
    if len(modes) != 2:
        raise ValueError("Expected exactly two top-level PageMode entries")
    first, second = modes
    a, b, removed = second
    normalized = original[:start+a] + b" "*(b-a) + original[start+b:]
    strict_reader(normalized)
    with output.open("xb") as f:
        f.write(normalized)
    return {"state": "repaired", "kept": first[2], "removed": removed}


def _catalog_modes(data):
    # Accept the plain, name-based catalogs produced by the tested driver.
    # Parenthesized strings and comments are outside this restricted lexer.
    if not data.startswith(b"<<") or b"(" in data or b"%" in data:
        raise ValueError("Unsupported PDF catalog syntax")
    tokens = list(re.finditer(rb"<<|>>|<[^<>]*>|/[^\s<>\[\]/]+|[^\s<>\[\]/]+|[\[\]]", data))
    depth = arrays = 0
    modes = []
    allowed = {b"/UseNone", b"/UseOutlines", b"/UseThumbs", b"/FullScreen", b"/UseOC", b"/UseAttachments"}
    for i, token in enumerate(tokens):
        key = token.group()
        if key == b"<<":
            depth += 1
        elif key == b">>":
            depth -= 1
        elif key == b"[":
            arrays += 1
        elif key == b"]":
            arrays -= 1
        elif depth == 1 and arrays == 0 and key == b"/PageMode":
            value = tokens[i+1]
            if value.group() not in allowed:
                raise ValueError("Unsupported PageMode value")
            modes.append((token.start(), value.end(), value.group().decode("ascii")))
        if min(depth, arrays) < 0:
            raise ValueError("Malformed PDF catalog nesting")
    if depth or arrays:
        raise ValueError("Unclosed PDF catalog")
    return modes
