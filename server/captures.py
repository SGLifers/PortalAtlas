"""Save browser-generated batches locally without relying on browser downloads."""
import json
from pathlib import Path
import re
import tempfile
import uuid
import zipfile

MAX_CAPTURE_BYTES=384*1024*1024


def save_capture(stream,size,directory):
    if not 22<=size<=MAX_CAPTURE_BYTES:raise ValueError('Capture ZIP must fit within 384 MiB.')
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True,mode=0o700)
    path=None
    try:
        with tempfile.NamedTemporaryFile(dir=directory,suffix='.tmp',delete=False) as output:
            path=Path(output.name);left=size
            while left:
                part=stream.read(min(left,1024*1024))
                if not part:raise ValueError('Capture upload was incomplete.')
                output.write(part);left-=len(part)
        with zipfile.ZipFile(path) as archive:
            rows=archive.infolist();names=[row.filename for row in rows]
            if len(rows)>4096 or len(names)!=len(set(names)) or 'manifest.json' not in names:
                raise ValueError('Invalid capture ZIP entries.')
            if any(name!='manifest.json' and not re.fullmatch(r'[A-Za-z0-9_-]+/clue-0[1-6]\.png',name) for name in names):
                raise ValueError('Invalid capture ZIP paths.')
            if sum(row.file_size for row in rows)>MAX_CAPTURE_BYTES or archive.getinfo('manifest.json').file_size>2*1024*1024:
                raise ValueError('Capture ZIP content is too large.')
            manifest=json.loads(archive.read('manifest.json'))
            if not isinstance(manifest,dict) or manifest.get('format')!='portal-atlas-clue-batch' or manifest.get('version')!=1:
                raise ValueError('Unsupported capture ZIP.')
        final=directory/('capture-'+uuid.uuid4().hex+'.zip');path.replace(final);path=None
        return final
    except (zipfile.BadZipFile,UnicodeError,json.JSONDecodeError) as exc:
        raise ValueError('Invalid capture ZIP.') from exc
    finally:
        if path is not None:path.unlink(missing_ok=True)
