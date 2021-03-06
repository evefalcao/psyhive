"""Tools for ingesting file from outsource vendors."""

from psyhive.utils import lprint, dev_mode

from .ing_utils import parse_basename, vendor_from_path, INGESTED_TOKEN
from .ing_vendor_file import is_vendor_file, VendorFile
from .ing_psy_asset import is_psy_asset, PsyAsset

try:  # This will fail for outsource vendors
    from .ing_utils_psy import (
        ICON, map_tag_to_shot, map_file_to_psy_asset, map_tag_to_asset)
except ImportError:
    lprint('FAILED TO IMPORT ing_utils_psy', verbose=dev_mode())

try:  # This will fail for outsource vendors
    from .ing_tools import ingest_seqs
except ImportError:
    lprint('FAILED TO IMPORT ing_tools', verbose=dev_mode())

try:  # This will fail for outsource vendors
    from .ing_ingestible import Ingestible
except ImportError:
    lprint('FAILED TO IMPORT ing_ingestible', verbose=dev_mode())
