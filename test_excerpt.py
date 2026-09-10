import unittest
from classification_excerpt import build_excerpt


class ExcerptTests(unittest.TestCase):
    def test_deduplicate_and_remove_footer(self):
        result = {'document': {'json_content': {'texts': [
            {'label': 'section_header', 'text': 'Invoice'},
            {'label': 'text', 'text': 'Invoice'},
            {'label': 'text', 'text': 'Amount due 100'},
            {'label': 'page_footer', 'text': 'Page 1'},
        ]}}}
        self.assertEqual(build_excerpt(result), 'Invoice\nAmount due 100')

    def test_long_document_keeps_heading_and_table(self):
        result = {'document': {'json_content': {
            'texts': [{'label': 'text', 'text': 'Introduction ' * 2000},
                      {'label': 'section_header', 'text': 'Maintenance report'}],
            'tables': [{'data': {'table_cells': [
                {'start_row_offset_idx': 0, 'text': 'Equipment'},
                {'start_row_offset_idx': 0, 'text': 'Condition'},
            ]}}],
        }}}
        excerpt = build_excerpt(result)
        self.assertLessEqual(len(excerpt), 1600)
        self.assertIn('Maintenance report', excerpt)
        self.assertIn('Equipment | Condition', excerpt)

    def test_fallback_and_empty(self):
        self.assertEqual(build_excerpt({}), '')
        self.assertEqual(build_excerpt({'document': {'md_content': 'abc' * 1000}}), ('abc' * 1000)[:1600])

    def test_table_only(self):
        result = {'document': {'json_content': {'tables': [
            {'data': {'table_cells': [{'text': 'Account balance'}]}}
        ]}}}
        self.assertEqual(build_excerpt(result), 'Account balance')

    def test_caption_is_identity_evidence(self):
        result = {'document': {'json_content': {'texts': [
            {'label': 'caption', 'text': 'Medical fitness certificate'},
            {'label': 'text', 'text': 'This certifies the person was examined.'},
        ]}}}
        self.assertIn('Medical fitness certificate', build_excerpt(result))
