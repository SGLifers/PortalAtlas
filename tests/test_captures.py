from io import BytesIO
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from server.captures import MAX_CAPTURE_BYTES,save_capture


def batch(extra=None):
    stream=BytesIO()
    with zipfile.ZipFile(stream,'w') as archive:
        archive.writestr('manifest.json',json.dumps({'format':'portal-atlas-clue-batch','version':1}))
        archive.writestr(extra or 'Academy-MAP_Academy/clue-01.png',b'fixture')
    return stream.getvalue()


class CaptureTests(unittest.TestCase):
    def test_local_save_preserves_bytes_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as directory:
            content=batch();one=save_capture(BytesIO(content),len(content),directory)
            two=save_capture(BytesIO(content),len(content),directory)
            self.assertNotEqual(one,two);self.assertEqual(one.read_bytes(),content)
            self.assertEqual(one.stat().st_mode&0o777,0o600)
    def test_bad_archives_paths_and_incomplete_uploads_leave_no_files(self):
        with tempfile.TemporaryDirectory() as directory:
            for content,declared in [(b'not a zip'*8,72),(batch('../escape.png'),None),(batch(),len(batch())+1)]:
                with self.subTest(size=declared):
                    with self.assertRaises(ValueError):save_capture(BytesIO(content),declared or len(content),directory)
                    self.assertEqual(list(Path(directory).iterdir()),[])
            with self.assertRaises(ValueError):save_capture(BytesIO(b''),MAX_CAPTURE_BYTES+1,directory)
