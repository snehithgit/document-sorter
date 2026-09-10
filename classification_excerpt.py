"""Select compact classification evidence without sending Docling metadata."""
import re


def clip(text, limit):
    text = str(text or "")[:limit]
    if len(text) == limit and " " in text:
        text = text.rsplit(" ", 1)[0]
    return text


def build_excerpt(result, limit=1600):
    """Return compact evidence, or empty string when Docling extracted nothing."""
    document = result.get("document", {})
    structured = document.get("json_content") or {}
    headings, body, rows = [], [], []
    seen = set()

    def add(target, value):
        text = re.sub(r"\s+", " ", str(value or "")).strip()
        if text and text.casefold() not in seen:
            seen.add(text.casefold())
            target.append(text)

    for item in structured.get("texts", []):
        label = item.get("label", "")
        if label in ("page_footer", "footnote"):
            continue
        target = headings if label in ("title", "section_header", "page_header", "caption") else body
        add(target, item.get("text"))

    for table in structured.get("tables", []):
        grouped, header_rows = {}, set()
        for cell in table.get("data", {}).get("table_cells", []):
            row = cell.get("start_row_offset_idx", 0)
            grouped.setdefault(row, []).append(cell.get("text", ""))
            if cell.get("column_header"):
                header_rows.add(row)
        for row in sorted(grouped):
            add(rows, ("Header: " if row in header_rows else "") + " | ".join(grouped[row]))

    if not headings and not body and not rows:
        return clip((document.get("text_content") or document.get("md_content") or "").strip(), limit)
    full = "\n".join(headings + body + rows)
    if len(full) <= limit:
        return full

    selected, budget = [], limit
    for title, lines, cap in (("Headings", headings, 500), ("Table sample", rows, 500), ("Opening text", body, 600)):
        if not lines or budget <= len(title) + 3:
            continue
        text = clip("\n".join(lines), min(cap, budget - len(title) - 3))
        block = title + ":\n" + text
        selected.append(block)
        budget -= len(block) + 1
    return clip("\n".join(selected), limit)
