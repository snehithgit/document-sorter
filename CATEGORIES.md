# Approved classification categories

The reference list of 70 categories (69 document types plus `other`) is
`classification_categories.py`. It is used for reporting `in_taxonomy`, not shown
to the inference model.
The content pipeline still sends only compact Docling evidence, without the filename.

Responses must contain exactly `category` and numeric `confidence` (0–1). The
model's chosen category is final; new categories are accepted and marked with
`in_taxonomy: false`; recurring new types can be reviewed later. Malformed
responses, the reserved `protected` category, extra/missing fields and invalid
confidence values fail the file. The failure is logged; originals remain intact.
This is client-side validation, not a claim of grammar-constrained server decoding.

`protected` is reserved for PDFs requiring an opening password and is not a model category.
PDFs encrypted with an empty opening password are readable and continue through classification.
The protection check runs before resume lookup or either server queue; slow
PDF reads are logged as `PDF PROTECTION CHECK START/COMPLETE`, and a check error keeps
the file off both servers.

Empty OCR is held as an error for review, without assigning a local category.
Use Recategorise to replace existing classifications from saved Docling output.
Legacy protected entries are rechecked on a normal run; old sorted copies are retained.

Inference can be selected in the dashboard or with `--inference oneplus|pi5`.
OnePlus uses `192.168.68.60:8080`; Pi 5 uses `192.168.68.55:8080` and its
`Qwen3.5-2B-Q8_0.gguf` model name. Both servers are treated as single-slot
inference workers.
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

If the state database was lost, successful snapshots containing `_local_file_id`
can be recovered by basename. This fallback is used only when there is exactly one
match; ambiguous basenames are refused for safety. Place the extracted JSON files
in the configured `docling_json` folder before using the button.

OnePlus still processes one request at a time. New results are saved and copies
are hash-verified. Old sorted copies are retained, so changed categories can leave
a copy in both folders for manual review. The latest result appears in the table.
