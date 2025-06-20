#!/usr/bin/env python3
"""Backup blockchain data."""

import os
import sys
import json
import tarfile
import hashlib
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))


def backup_blockchain(data_dir: str = "./blockchain_data", backup_dir: str = "./backups"):
    """Create a backup of blockchain data."""
    
    data_path = Path(data_dir)
    backup_path = Path(backup_dir)
    backup_path.mkdir(exist_ok=True)
    
    # Create backup filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_path / f"blockchain_backup_{timestamp}.tar.gz"
    
    print(f"Creating backup: {backup_file}")
    
    # Create tarball
    with tarfile.open(backup_file, "w:gz") as tar:
        tar.add(data_path, arcname="blockchain_data")
    
    # Calculate checksum
    sha256_hash = hashlib.sha256()
    with open(backup_file, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    
    checksum = sha256_hash.hexdigest()
    
    # Save backup metadata
    metadata = {
        "timestamp": timestamp,
        "backup_file": str(backup_file),
        "checksum": checksum,
        "size_bytes": backup_file.stat().st_size,
        "created_at": datetime.now().isoformat()
    }
    
    metadata_file = backup_path / f"blockchain_backup_{timestamp}.json"
    with open(metadata_file, "w") as f:
        json.dump(metadata, f, indent=2)
    
    print(f"✓ Backup created successfully")
    print(f"✓ Size: {metadata['size_bytes'] / 1024 / 1024:.2f} MB")
    print(f"✓ SHA256: {checksum}")
    
    # Clean old backups (keep last 5)
    backups = sorted(backup_path.glob("blockchain_backup_*.tar.gz"))
    if len(backups) > 5:
        for old_backup in backups[:-5]:
            print(f"Removing old backup: {old_backup}")
            old_backup.unlink()
            # Remove metadata too
            old_metadata = old_backup.with_suffix(".json")
            if old_metadata.exists():
                old_metadata.unlink()


def restore_blockchain(backup_file: str, data_dir: str = "./blockchain_data"):
    """Restore blockchain from backup."""
    
    backup_path = Path(backup_file)
    data_path = Path(data_dir)
    
    if not backup_path.exists():
        print(f"✗ Backup file not found: {backup_file}")
        return
    
    # Verify checksum
    metadata_file = backup_path.with_suffix(".json")
    if metadata_file.exists():
        with open(metadata_file, "r") as f:
            metadata = json.load(f)
        
        print("Verifying backup integrity...")
        sha256_hash = hashlib.sha256()
        with open(backup_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        
        if sha256_hash.hexdigest() != metadata["checksum"]:
            print("✗ Checksum verification failed!")
            return
        
        print("✓ Checksum verified")
    
    # Backup current data if it exists
    if data_path.exists():
        print("Backing up current data...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        data_path.rename(f"{data_path}_backup_{timestamp}")
    
    # Extract backup
    print(f"Restoring from: {backup_file}")
    with tarfile.open(backup_path, "r:gz") as tar:
        tar.extractall(path=data_path.parent)
    
    print("✓ Blockchain restored successfully")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Blockchain backup and restore utility")
    parser.add_argument("action", choices=["backup", "restore"], help="Action to perform")
    parser.add_argument("--data-dir", default="./blockchain_data", help="Blockchain data directory")
    parser.add_argument("--backup-dir", default="./backups", help="Backup directory")
    parser.add_argument("--backup-file", help="Backup file to restore from")
    
    args = parser.parse_args()
    
    if args.action == "backup":
        backup_blockchain(args.data_dir, args.backup_dir)
    elif args.action == "restore":
        if not args.backup_file:
            print("✗ Please specify --backup-file for restore")
            sys.exit(1)
        restore_blockchain(args.backup_file, args.data_dir)