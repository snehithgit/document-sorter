import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from durable_state import StateStore, atomic_json
from automate_docling_oneplus_sort import verified_copy


class RecoveryTests(unittest.TestCase):
    def test_atomic_json_preserves_previous_on_publish_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'result.json'
            atomic_json(path, {'old': True})
            with patch('durable_state.os.replace', side_effect=OSError('interrupted')):
                with self.assertRaises(OSError):
                    atomic_json(path, {'new': True})
            self.assertEqual(json.loads(path.read_text()), {'old': True})

    def test_saved_classification_survives_reopen_and_copy_repeats_safely(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            db = StateStore(root / 'state.db')
            db.put('job', status='classified', label={'category': 'book'})
            self.assertEqual(StateStore(root / 'state.db').get('job')['status'], 'classified')
            source = root / 'source.pdf'
            source.write_bytes(b'full original')
            target = root / 'sorted' / 'source.pdf'
            first = verified_copy(source, target)
            self.assertEqual(verified_copy(source, target), first)
            self.assertEqual(source.read_bytes(), target.read_bytes())

    def test_failed_copy_never_publishes_destination(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / 'source.pdf'
            source.write_bytes(b'original')
            target = root / 'sorted' / 'file.pdf'
            with patch('automate_docling_oneplus_sort.shutil.copyfileobj', side_effect=OSError('disk full')):
                with self.assertRaises(OSError):
                    verified_copy(source, target)
            self.assertFalse(target.exists())
            self.assertTrue(source.exists())


if __name__ == '__main__':
    unittest.main()
