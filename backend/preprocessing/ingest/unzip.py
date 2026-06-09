from __future__ import annotations

import zipfile
from pathlib import Path


def decode_zip_name(name: str) -> str:
    """Fix GBK Chinese filenames inside zip (misread as cp437)."""
    if not name:
        return name
    try:
        return name.encode("cp437").decode("gbk")
    except (UnicodeDecodeError, UnicodeEncodeError):
        return name


def extract_zip_member(
    zip_path: Path,
    member_name: str,
    dest_dir: Path,
    *,
    decoded_name: str | None = None,
) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    display = decoded_name or decode_zip_name(member_name)
    from ..utils.ids import parse_pdf_filename

    parsed = parse_pdf_filename(display)
    if parsed:
        out_name = f"{parsed.script_id}_{parsed.title}.pdf"
    else:
        out_name = Path(display).name

    out_path = dest_dir / out_name
    with zipfile.ZipFile(zip_path, "r") as zf:
        out_path.write_bytes(zf.read(member_name))
    return out_path
