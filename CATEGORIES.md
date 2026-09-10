# Approved classification categories

The authoritative list of 70 categories (69 document types plus `other`) is
`classification_categories.py`. Both classification prompts use this same list.
The content pipeline still sends only compact Docling evidence, without the filename.

Responses must contain exactly `category` and numeric `confidence` (0–1).
Unknown categories, extra/missing fields and invalid confidence values fail the file
instead of creating an arbitrary folder. The failure is logged; originals remain intact.
This is client-side validation, not a claim of grammar-constrained server decoding.

`protected` is reserved for locally detected encrypted PDFs and is not a model category.
Existing verified sorted files are not moved or reclassified automatically. Pending
cached labels outside the approved schema are reclassified, reusing saved Docling
output when available. Existing valid cached labels continue to be reusable.

The private category-review files and source documents are not required at runtime
and must not be published with the application.
