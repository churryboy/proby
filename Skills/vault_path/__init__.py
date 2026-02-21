#!/usr/bin/env python3
"""
Path Abstraction Layer for Obsidian Vault
Provides logical name-based file access and metadata-based search.
"""

import os
import json
import re
from pathlib import Path
from typing import Optional, List, Dict, Any
from functools import lru_cache
from datetime import datetime

# Get vault root from environment
VAULT_ROOT = Path(os.getenv("OBSIDIAN_VAULT_PATH", "/Users/churryboy/Desktop/proby-sync"))

# Load configuration
_CONFIG_PATH = Path(__file__).parent / "vault_paths.json"
_CONFIG = None


def _load_config() -> dict:
    """Load vault_paths.json configuration."""
    global _CONFIG
    if _CONFIG is None:
        if _CONFIG_PATH.exists():
            with open(_CONFIG_PATH, 'r', encoding='utf-8') as f:
                _CONFIG = json.load(f)
        else:
            _CONFIG = {"logical_paths": {}, "fallback_paths": {}, "search_patterns": {}}
    return _CONFIG


def get_vault_root() -> Path:
    """Get the Obsidian vault root path."""
    return VAULT_ROOT


def get_file_path(logical_name: str, must_exist: bool = False) -> Optional[Path]:
    """
    Get file or folder path by logical name.
    
    Args:
        logical_name: Logical name from vault_paths.json
        must_exist: If True, returns None if path doesn't exist
    
    Returns:
        Path object or None if not found
    """
    config = _load_config()
    logical_paths = config.get("logical_paths", {})
    fallback_paths = config.get("fallback_paths", {})
    
    # Try primary path first
    if logical_name in logical_paths:
        primary_path = VAULT_ROOT / logical_paths[logical_name]
        if not must_exist or primary_path.exists():
            return primary_path
    
    # Try fallback paths
    if logical_name in fallback_paths:
        for fallback in fallback_paths[logical_name]:
            fallback_path = VAULT_ROOT / fallback
            if fallback_path.exists():
                return fallback_path
    
    # If must_exist is False, return primary path anyway
    if logical_name in logical_paths:
        return VAULT_ROOT / logical_paths[logical_name]
    
    return None


def parse_frontmatter(file_path: Path) -> Dict[str, Any]:
    """
    Parse frontmatter from markdown file.
    
    Returns:
        Dictionary of frontmatter metadata, empty dict if no frontmatter
    """
    if not file_path.exists():
        return {}
    
    try:
        content = file_path.read_text(encoding='utf-8')
    except Exception:
        return {}
    
    # Match frontmatter (--- ... ---)
    frontmatter_pattern = re.compile(
        r'^---\s*\n(.*?)\n---\s*\n',
        re.DOTALL | re.MULTILINE
    )
    
    match = frontmatter_pattern.match(content)
    if not match:
        return {}
    
    frontmatter_text = match.group(1)
    metadata = {}
    
    # Simple YAML parsing (key: value)
    for line in frontmatter_text.split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        
        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            metadata[key] = value
    
    return metadata


def find_files_by_metadata(
    metadata_filter: Dict[str, Any],
    folder: Optional[str] = None,
    glob_pattern: str = "*.md",
    recursive: bool = True
) -> List[Path]:
    """
    Find files by frontmatter metadata.
    
    Args:
        metadata_filter: Dictionary of metadata to match (e.g., {"type": "revenue"})
        folder: Logical folder name (optional, searches entire vault if None)
        glob_pattern: File pattern to search (default: "*.md")
        recursive: Search recursively (default: True)
    
    Returns:
        List of matching file paths
    """
    if folder:
        search_root = get_file_path(folder)
        if not search_root or not search_root.exists():
            return []
    else:
        search_root = VAULT_ROOT
    
    if not search_root:
        return []
    
    # Find all matching files
    if recursive:
        files = list(search_root.rglob(glob_pattern))
    else:
        files = list(search_root.glob(glob_pattern))
    
    matching_files = []
    for file_path in files:
        metadata = parse_frontmatter(file_path)
        
        # Check if all filter conditions match
        matches = True
        for key, value in metadata_filter.items():
            if metadata.get(key) != value:
                matches = False
                break
        
        if matches:
            matching_files.append(file_path)
    
    return matching_files


def get_file_by_metadata(
    metadata_filter: Dict[str, Any],
    folder: Optional[str] = None,
    glob_pattern: str = "*.md"
) -> Optional[Path]:
    """
    Get single file by metadata (returns first match).
    
    Args:
        metadata_filter: Dictionary of metadata to match
        folder: Logical folder name (optional)
        glob_pattern: File pattern to search
    
    Returns:
        First matching file path or None
    """
    files = find_files_by_metadata(metadata_filter, folder, glob_pattern)
    return files[0] if files else None


def extract_date_from_path(file_path: Path) -> Optional[datetime]:
    """
    Extract date from filename (YYYY-MM-DD pattern).
    
    Returns:
        datetime object or None if no date found
    """
    date_pattern = re.compile(r'(\d{4}-\d{2}-\d{2})')
    match = date_pattern.search(file_path.name)
    if match:
        try:
            return datetime.strptime(match.group(1), "%Y-%m-%d")
        except ValueError:
            pass
    return None


def get_latest_file_by_date(files: List[Path]) -> Optional[Path]:
    """
    Get the latest file based on date in filename.
    
    Args:
        files: List of file paths
    
    Returns:
        Latest file path or None
    """
    if not files:
        return None
    
    dated_files = []
    for f in files:
        file_date = extract_date_from_path(f)
        if file_date:
            dated_files.append((file_date, f))
    
    if dated_files:
        dated_files.sort(key=lambda x: x[0], reverse=True)
        return dated_files[0][1]
    
    # Fallback to modification time
    return max(files, key=lambda p: p.stat().st_mtime)


def find_vault_file(relative_path: str) -> Optional[Path]:
    """
    Find file in vault, checking multiple possible locations.
    Legacy function for backward compatibility.
    
    Args:
        relative_path: Relative path from vault root
    
    Returns:
        Path if found, None otherwise
    """
    possible_bases = [
        VAULT_ROOT,
        VAULT_ROOT / "Laptop",
        VAULT_ROOT / "Mobile",
        VAULT_ROOT / "iMAC",
    ]
    
    for base in possible_bases:
        full_path = base / relative_path
        if full_path.exists():
            return full_path
    
    return None


# Cache frequently accessed paths
@lru_cache(maxsize=50)
def _cached_get_file_path(logical_name: str) -> Optional[Path]:
    """Cached version of get_file_path."""
    return get_file_path(logical_name, must_exist=True)


def clear_cache():
    """Clear the path cache (useful after config changes)."""
    _cached_get_file_path.cache_clear()
