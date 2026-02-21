#!/usr/bin/env python3
"""
Simple terminal script to create a todo item in an Obsidian markdown file.
Uses the same logic as mcp_obsidian_server.py's create_todo function.

Usage:
    python3 create_todo.py "할 일 내용"
    python3 create_todo.py "할 일 내용" --file "path/to/file.md"
    python3 create_todo.py "할 일 내용" --checked
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional

# Import Path Abstraction Layer
import sys
from pathlib import Path
_skills_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_skills_root))
sys.path.insert(0, str(Path(__file__).resolve().parent))  # same folder for todo_from_today

# Import from todo_from_today for env loading
from todo_from_today import load_env_file

# Import Path Abstraction Layer
from vault_path import (
    get_vault_root,
    get_file_path,
    find_vault_file as vault_find_file
)

# Load .env file
script_dir = _skills_root  # Skills 폴더 (vault_path, .env 후보)
env_path = script_dir / ".env"
load_env_file(env_path)

def find_vault_file(relative_path: str) -> Optional[Path]:
    """Find file in vault, checking multiple possible locations.
    Uses vault_path module for path abstraction."""
    return vault_find_file(relative_path)

def find_todo_folder() -> Path:
    """Find the Todo folder in vault using logical name."""
    todo_folder = get_file_path("todo_folder")
    if todo_folder and todo_folder.exists():
        return todo_folder
    
    # Fallback to default
    vault_root = get_vault_root()
    return vault_root / "00. Todo"

def create_todo(todo_text: str, file_path: str = None, checked: bool = False, today: bool = False):
    """Create a todo item in a markdown file.
    Uses vault_path module for path abstraction."""
    vault_root = get_vault_root()
    
    # Determine target file
    if file_path:
        # Try to find existing file first
        target_file = find_vault_file(file_path)
        if not target_file:
            # If not found, create at specified path relative to vault root
            target_file = vault_root / file_path
    elif today:
        # Use today's date file in Todo folder
        todo_folder = find_todo_folder()
        today_str = datetime.now().strftime("%Y-%m-%d")
        target_file = todo_folder / f"{today_str}.md"
    else:
        # Use today's date file in Todo folder as default
        todo_folder = find_todo_folder()
        today_str = datetime.now().strftime("%Y-%m-%d")
        target_file = todo_folder / f"{today_str}.md"
    
    # Create parent directories if needed
    target_file.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        if target_file.exists():
            content = target_file.read_text(encoding='utf-8')
            checkbox = "[x]" if checked else "[ ]"
            new_todo = f"- {checkbox} {todo_text}\n"
            content += new_todo
        else:
            checkbox = "[x]" if checked else "[ ]"
            content = f"- {checkbox} {todo_text}\n"
        
        target_file.write_text(content, encoding='utf-8')
        
        # Print success message
        try:
            relative_path = target_file.relative_to(vault_root)
        except ValueError:
            relative_path = target_file
        print(f"✓ Todo added to: {relative_path}")
        print(f"  {checkbox} {todo_text}")
        
        return target_file
    except Exception as e:
        print(f"Error creating todo: {e}", file=sys.stderr)
        raise

def main():
    parser = argparse.ArgumentParser(
        description="Create a todo item in an Obsidian markdown file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "프로젝트 문서 작성"
  %(prog)s "회의 준비" --file "00. Todo/Actual/2025-02-15.md"
  %(prog)s "완료된 작업" --checked
  %(prog)s "오늘 할 일" --today
        """
    )
    
    parser.add_argument(
        "todo_text",
        help="The todo item text"
    )
    
    parser.add_argument(
        "--file", "-f",
        help="Path to the markdown file (relative to vault root). If not specified, uses today's date file in Todo folder."
    )
    
    parser.add_argument(
        "--checked", "-c",
        action="store_true",
        help="Mark the todo as checked (completed)"
    )
    
    parser.add_argument(
        "--today", "-t",
        action="store_true",
        help="Add to today's date file in Todo folder (default behavior)"
    )
    
    args = parser.parse_args()
    
    try:
        create_todo(
            todo_text=args.todo_text,
            file_path=args.file,
            checked=args.checked,
            today=args.today
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
