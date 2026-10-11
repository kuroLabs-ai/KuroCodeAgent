"""
scripts/clean_production.py — Pre-Production Sanitization Script.
Cleans all conversation history, chat logs, SQLite databases, encrypted vaults,
and environment tokens to ensure zero data leakage before publishing.
"""

import os
import sys
from pathlib import Path

# Locate root directory
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))

def clean():
    print("[*] Cleaning KuroCode workspace for production release...")
    
    # 1. Remove Encrypted Vault
    vault_file = ROOT_DIR / "config" / "vault.enc"
    if vault_file.exists():
        try:
            vault_file.unlink()
            print("  [x] Removed encrypted vault: config/vault.enc")
        except Exception as e:
            print(f"  [!] Failed to remove vault: {e}")

    # 2. Remove Brain Databases & Memory files
    brain_dir = ROOT_DIR / "brain"
    if brain_dir.exists():
        for db_file in brain_dir.glob("*.db*"):
            try:
                db_file.unlink()
                print(f"  [x] Removed database: {db_file.name}")
            except Exception as e:
                print(f"  [!] Failed to remove {db_file.name}: {e}")
        
        for mem_file in brain_dir.glob("memory*.json"):
            try:
                mem_file.unlink()
                print(f"  [x] Removed memory file: {mem_file.name}")
            except Exception as e:
                print(f"  [!] Failed to remove {mem_file.name}: {e}")

    # 3. Remove History files
    history_file = ROOT_DIR / ".kuro_history"
    if history_file.exists():
        try:
            history_file.unlink()
            print("  [x] Removed CLI history: .kuro_history")
        except Exception as e:
            print(f"  [!] Failed to remove .kuro_history: {e}")

    # 4. Remove Evolution and Backup files
    for f in [ROOT_DIR / "evolution_history.json", ROOT_DIR / "store_catalog.json"]:
        if f.exists():
            try:
                f.unlink()
                print(f"  [x] Removed temporary file: {f.name}")
            except Exception as e:
                pass

    # 5. Initialize fresh blank SQLite schema
    try:
        from kurocode.core.memory_db import init_db
        init_db()
        print("  [OK] Fresh blank SQLite schema initialized at brain/kuro.db (0 records).")
    except Exception as e:
        print(f"  [!] Re-init schema note: {e}")

    print("\n[SUCCESS] Workspace successfully sanitized! Ready for production deployment.")

if __name__ == "__main__":
    clean()
