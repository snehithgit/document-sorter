import json
import unittest
from pathlib import Path
from unittest.mock import patch

from classification_categories import CATEGORIES, SYSTEM_PROMPT, FILENAME_PROMPT, validate_label
from automate_docling_oneplus_sort import classify, parse_json


class CategoryTests(unittest.TestCase):
    def test_approved_list(self):
        self.assertEqual(len(CATEGORIES), 70)
        self.assertEqual(len(set(CATEGORIES)), 70)
        self.assertNotIn('protected', CATEGORIES)
        for category in CATEGORIES:
            self.assertIn(category, SYSTEM_PROMPT)
            self.assertIn(category, FILENAME_PROMPT)
            self.assertEqual(parse_json(json.dumps({'category': category, 'confidence': 0.9})),
                             {'category': category, 'confidence': 0.9})

    def test_reject_unknown_and_unsafe_categories(self):
        for category in ('novel', '../passport', 'protected', 'Bank Statement', '', None):
            with self.subTest(category=category), self.assertRaises(ValueError):
                validate_label({'category': category, 'confidence': 0.9})

    def test_reject_invalid_confidence(self):
        for confidence in (-0.1, 1.1, float('nan'), float('inf'), True, '0.9', None):
            with self.subTest(confidence=confidence), self.assertRaises(ValueError):
                validate_label({'category': 'book', 'confidence': confidence})

    def test_reject_missing_and_extra_keys(self):
        for result in ({}, [], {'category': 'book'},
                       {'category': 'book', 'confidence': 1, 'description': 'extra'}):
            with self.subTest(result=result), self.assertRaises(ValueError):
                validate_label(result)

    def test_content_request_uses_list_without_filename(self):
        result = {'document': {'json_content': {'texts': [
            {'label': 'section_header', 'text': 'Invoice'},
            {'label': 'text', 'text': 'Amount due 100'},
        ]}}}
        with patch('automate_docling_oneplus_sort.stream_oneplus',
                   return_value='{"category":"invoice","confidence":0.9}') as stream:
            label = classify(None, 'unused', 'test-model', result, Path('private-filename.pdf'), 10)
        payload = stream.call_args.args[2]
        self.assertEqual(label['category'], 'invoice')
        self.assertEqual(payload['messages'][0]['content'], SYSTEM_PROMPT)
        self.assertNotIn('private-filename', payload['messages'][1]['content'])
        self.assertIn('Invoice', payload['messages'][1]['content'])

    def test_invalid_model_answer_does_not_become_a_label(self):
        with patch('automate_docling_oneplus_sort.stream_oneplus',
                   return_value='{"category":"invented_folder","confidence":0.99}'):
            with self.assertRaises(ValueError):
                classify(None, 'unused', 'test-model',
                         {'document': {'text_content': 'some content'}}, Path('x.pdf'), 10)

    def test_book_rule_is_in_prompt(self):
        self.assertIn('book title', SYSTEM_PROMPT)
        self.assertIn('opening page', SYSTEM_PROMPT)
