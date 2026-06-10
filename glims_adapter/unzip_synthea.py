"""Safe extraction of locally downloaded Synthea archives."""

import logging
import os
from pathlib import Path
from typing import List
from zipfile import BadZipFile, ZipFile

LOGGER = logging.getLogger(__name__)


def _safe_destination(base_dir: Path, member_name: str) -> Path:
    destination = (base_dir / member_name).resolve()
    if os.path.commonpath([str(base_dir.resolve()), str(destination)]) != str(base_dir.resolve()):
        raise ValueError("Unsafe archive member path: {}".format(member_name))
    return destination


def extract_synthea_zips(zip_dir: Path, extraction_dir: Path) -> List[Path]:
    """Extract every Synthea ZIP into a dedicated subdirectory."""
    if not zip_dir.is_dir():
        raise FileNotFoundError("Synthea ZIP directory does not exist: {}".format(zip_dir))

    archives = sorted(zip_dir.glob("*.zip"))
    if not archives:
        raise FileNotFoundError("No ZIP files found in {}".format(zip_dir))

    extraction_dir.mkdir(parents=True, exist_ok=True)
    extracted_roots = []

    for archive in archives:
        archive_root = extraction_dir / archive.stem
        archive_root.mkdir(parents=True, exist_ok=True)
        try:
            with ZipFile(str(archive)) as zip_file:
                for member in zip_file.infolist():
                    _safe_destination(archive_root, member.filename)
                zip_file.extractall(str(archive_root))
        except BadZipFile as exc:
            raise ValueError("Invalid ZIP archive: {}".format(archive)) from exc

        extracted_roots.append(archive_root)
        LOGGER.info("Extracted %s to %s", archive.name, archive_root)

    return extracted_roots
