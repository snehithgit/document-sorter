import json
import tempfile
import unittest
import threading
import urllib.request
import urllib.error
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import Mock, patch

import dashboard
import automate_docling_oneplus_sort as sorter


class RecategoriseTests(unittest.TestCase):
    def test_permission_only_pdf_is_readable_but_password_pdf_is_protected(self):
        with tempfile.TemporaryDirectory() as folder:
            for password in ('', 'opening-password'):
                path = Path(folder) / ('open.pdf' if not password else 'locked.pdf')
                writer = sorter.PdfWriter()
                writer.add_blank_page(width=100, height=100)
                writer.encrypt(user_password=password, owner_password='owner-password')
                with path.open('wb') as stream:
                    writer.write(stream)
                self.assertEqual(sorter.is_protected_pdf(path), bool(password))
                if not password:
                    preview, sent, total = sorter.pdf_preview(path, 2)
                    self.assertEqual((sent, total), (1, 1))
                    self.assertFalse(sorter.PdfReader(preview).is_encrypted)

    def test_protection_check_is_before_hashing(self):
        order = []
        with patch.object(sorter, 'is_protected_pdf', side_effect=lambda path: order.append('protect') or True), \
                patch.object(sorter, 'file_digest', side_effect=lambda path: order.append('hash') or 'digest'):
            self.assertTrue(sorter.is_protected_pdf(Path('slow.pdf')))
            self.assertEqual(order, ['protect'])

    def test_http_recategorise_and_origin_guard(self):
        server = ThreadingHTTPServer(('127.0.0.1', 0), dashboard.Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        url = f'http://127.0.0.1:{server.server_port}'
        try:
            with patch.object(dashboard, 'runner') as runner:
                request = urllib.request.Request(url + '/api/recategorise',
                    data=b'{"pages":2}', headers={'Origin': url, 'Content-Type': 'application/json'})
                with urllib.request.urlopen(request, timeout=3) as response:
                    self.assertEqual(response.status, 200)
                runner.start.assert_called_once_with(2, inference='oneplus', recategorise=True)
                request = urllib.request.Request(url + '/api/recategorise',
                    data=b'{"pages":2}', headers={'Origin': 'http://untrusted.example'})
                with self.assertRaises(urllib.error.HTTPError) as error:
                    urllib.request.urlopen(request, timeout=3)
                self.assertEqual(error.exception.code, 403)
                self.assertEqual(runner.start.call_count, 1)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_button_launches_saved_only_mode(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(dashboard, 'ROOT', Path(folder)), \
                patch.object(dashboard, '_find_existing_run', return_value=False), \
                patch.object(dashboard.subprocess, 'Popen') as popen, \
                patch.object(dashboard.threading, 'Thread'):
            runner = dashboard.ProcessRunner()
            runner.start(2, recategorise=True)
            self.assertIn('--retry-saved', popen.call_args.args[0])
            popen.return_value.poll.return_value = None
            with self.assertRaises(ValueError):
                runner.start(2, recategorise=True)
            self.assertEqual(popen.call_count, 1)

    def test_same_filename_different_hash_is_not_reused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            saved = root / 'old.json'
            sorter.atomic_json(saved, {'status': 'success', '_local_file_id': 'scan.jpg'})
            path, result = sorter.saved_docling_for(root / 'scan.jpg', 'new-hash', root,
                                                    [{'sha256': 'old-hash', 'docling_json': str(saved)}])
            self.assertEqual(path, saved)
            self.assertEqual(result['status'], 'success')

    def test_recovers_by_basename_when_database_link_is_missing(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / 'scan.jpg'
            source.write_bytes(b'current bytes')
            saved = root / 'saved.json'
            sorter.atomic_json(saved, {'status': 'success', '_local_file_id': 'scan.jpg',
                                       'document': {'text_content': 'recovered'}})
            path, result = sorter.saved_docling_for(source, 'new-hash', root, [])
            self.assertEqual(path, saved)
            self.assertEqual(result['document']['text_content'], 'recovered')

    def test_reclassifies_completed_input_without_docling(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            inputs, output, snapshots = (root / name for name in ('input', 'sorted', 'json'))
            inputs.mkdir()
            source = inputs / 'scan.jpg'
            source.write_bytes(b'test original bytes')
            digest = sorter.file_digest(source)
            saved = snapshots / 'saved.json'
            sorter.atomic_json(saved, {'status': 'success', 'document': {'text_content': 'Invoice'}})
            old_copy, _ = sorter.verified_copy(source, output / 'other' / source.name)
            sorter.atomic_json(output / 'unused.json', {})
            db = sorter.StateStore(output / 'state.sqlite3')
            db.put('previous-page-setting', sha256=digest, docling_json=str(saved),
                   label={'category': 'other', 'confidence': 0}, status='complete')
            # A previously verified manifest must not make recategorisation skip this input.
            (output / 'manifest.jsonl').write_text(json.dumps({
                'source': str(source), 'sha256': digest, 'sorted_to': str(old_copy),
                'copy_verified': True}) + '\n', encoding='utf-8')
            args = ['sorter', '--input', str(inputs), '--output', str(output),
                    '--json-output', str(snapshots), '--retry-saved']
            with patch('sys.argv', args), patch.object(sorter, 'docling_convert') as docling, \
                    patch.object(sorter, 'stream_oneplus', return_value='{"category":"custom_invoice","confidence":0.9}') as classify:
                sorter.main()
            docling.assert_not_called()
            classify.assert_called_once()
            self.assertEqual((output / 'custom_invoice' / source.name).read_bytes(), source.read_bytes())
            latest = json.loads((output / 'manifest.jsonl').read_text(encoding='utf-8').splitlines()[-1])
            self.assertEqual(latest['category'], 'custom_invoice')
            self.assertFalse(latest['in_taxonomy'])
            self.assertTrue(old_copy.exists())
            self.assertTrue(source.exists())
