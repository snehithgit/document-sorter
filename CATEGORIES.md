# Approved classification categories

The authoritative list of 70 categories (69 document types plus `other`) is
`classification_categories.py`. Both classification prompts use this same list.
The content pipeline still sends only compact Docling evidence, without the filename.

Responses must contain exactly `category` and numeric `confidence` (0–1).
Unknown categories, extra/missing fields and invalid confidence values fail the file
instead of creating an arbitrary folder. The failure is logged; originals remain intact.
This is client-side validation, not a claim of grammar-constrained server decoding.

`protected` is reserved for locally detected encrypted PDFs and is not a model category.
The protection check runs before hashing, resume lookup, or either server queue; slow
PDF reads are logged as `PDF PROTECTION CHECK START/COMPLETE`, and a check error keeps
the file off both servers.
Existing verified sorted files are not moved or reclassified automatically. Pending
cached labels outside the approved schema are reclassified, reusing saved Docling
output when available. Existing valid cached labels continue to be reusable.

The private category-review files and source documents are not required at runtime
and must not be published with the application.

## Recategorise with OnePlus

Use the dashboard button while processing is stopped. It runs `--retry-saved`
for current input files, bypassing previous labels and verified-manifest skips.
Byte-identical input duplicates remain skipped. Original files must still be in
input; this does not scan sorted folders for missing originals.

Saved successful Docling output is matched by source hash/state or the existing
hash-derived snapshot filename, never basename alone. Previously saved preview
pages are reused even if the page selector has changed. Missing saved output is
logged as a failure; no new conversion request is sent to Docling.

OnePlus still processes one request at a time. New results are saved and copies
are hash-verified. Old sorted copies are retained, so changed categories can leave
a copy in both folders for manual review. The latest result appears in the table.
