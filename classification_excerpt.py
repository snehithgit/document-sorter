"""Select compact classification evidence without sending Docling metadata."""
import re


def build_excerpt(result, limit=1600):
    document = result.get('document', {})
    structured = document.get('json_content') or {}
    headings, body, rows = [], [], []
    seen = set()

    def add(target, value):
        text = re.sub(r'\s+', ' ', str(value or '')).strip()
        if text and text.casefold() not in seen:
            seen.add(text.casefold())
            target.append(text)

    for item in structured.get('texts', []):
        label = item.get('label', '')
        if label in ('page_footer', 'footnote'):
            continue
        add(headings if label in ('title', 'section_header', 'page_header', 'caption') else body, item.get('text'))
    for table in structured.get('tables', []):
        grouped = {}
        for cell in table.get('data', {}).get('table_cells', []):
            grouped.setdefault(cell.get('start_row_offset_idx', 0), []).append(cell.get('text', ''))
        for cells in grouped.values():
            add(rows, ' | '.join(cells))
    if not headings and not body and not rows:
        return (document.get('text_content') or document.get('md_content') or '').strip()[:limit]

    full = '\n'.join(headings + body + rows)
    if len(full) <= limit:
        return full
    # Give each evidence type a bounded share. This keeps a long introduction
    # from hiding the title or the table schema that identifies the document.
    selected = []
    budget = limit
    for title, lines, cap in [('Headings', headings, 500), ('Table sample', rows, 500), ('Opening text', body, 600)]:
        if not lines or budget <= len(title) + 3:
            continue
        text = '\n'.join(lines)[:min(cap, budget - len(title) - 3)]
        block = title + ':\n' + text
        selected.append(block)
        budget -= len(block) + 1
    return '\n'.join(selected)[:limit]
