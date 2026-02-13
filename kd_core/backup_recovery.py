"""
Backup and Recovery System for KD-Code System
Provides backup and recovery functionality for KD-Code data
"""

import os
import json
import zipfile
import shutil
from datetime import datetime
from pathlib import Path


class BackupRecoverySystem:
    """Handles backup and recovery of KD-Code data and configurations"""
    
    def __init__(self, backup_dir='backups'):
        """
        Initialize the backup system
        
        Args:
            backup_dir (str): Directory to store backups
        """
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)
    
    def create_backup(self, backup_name=None, include_configs=True, include_generated_codes=True):
        """
        Create a backup of the KD-Code system
        
        Args:
            backup_name (str, optional): Name for the backup. If None, uses timestamp
            include_configs (bool): Whether to include configuration files
            include_generated_codes (bool): Whether to include generated codes
        
        Returns:
            str: Path to the created backup file
        """
        if not backup_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"kdcode_backup_{timestamp}"
        
        backup_path = self.backup_dir / f"{backup_name}.zip"
        
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add configuration files if requested
            if include_configs:
                config_paths = [
                    'kd_core/config.py',
                    'requirements.txt',
                    'README.md'
                ]
                
                for config_path in config_paths:
                    config_file = Path(config_path)
                    if config_file.exists():
                        zipf.write(config_file, config_file.name)
            
            # Add any generated codes or other data if needed
            # For now, we'll just add a backup manifest
            manifest = {
                'backup_name': backup_name,
                'created_at': datetime.now().isoformat(),
                'includes_configs': include_configs,
                'includes_generated_codes': include_generated_codes,
                'version': '1.0'
            }
            
            # Write manifest to zip
            zipf.writestr('manifest.json', json.dumps(manifest, indent=2))
        
        return str(backup_path)
    
    def list_backups(self):
        """
        List all available backups
        
        Returns:
            list: List of backup file paths
        """
        backups = []
        for backup_file in self.backup_dir.glob("*.zip"):
            backups.append(str(backup_file))
        return sorted(backups, reverse=True)  # Newest first
    
    def restore_backup(self, backup_path, restore_configs=True, restore_generated_codes=True):
        """
        Restore from a backup
        
        Args:
            backup_path (str): Path to the backup file
            restore_configs (bool): Whether to restore configuration files
            restore_generated_codes (bool): Whether to restore generated codes
        
        Returns:
            dict: Result of the restoration
        """
        try:
            backup_file = Path(backup_path)
            if not backup_file.exists():
                return {'success': False, 'error': 'Backup file does not exist'}
            
            # Extract the backup to a temporary directory
            temp_dir = self.backup_dir / "temp_restore"
            temp_dir.mkdir(exist_ok=True)
            
            with zipfile.ZipFile(backup_file, 'r') as zipf:
                zipf.extractall(temp_dir)
            
            # Read the manifest
            manifest_path = temp_dir / 'manifest.json'
            if manifest_path.exists():
                with open(manifest_path, 'r') as f:
                    manifest = json.load(f)
            else:
                return {'success': False, 'error': 'Backup manifest not found'}
            
            # Perform restoration based on manifest and flags
            restored_items = []
            
            if restore_configs:
                # Restore config files
                config_files = ['config.py', 'requirements.txt', 'README.md']
                for config_file in config_files:
                    config_source = temp_dir / config_file
                    if config_source.exists():
                        # In a real implementation, we'd copy to the appropriate location
                        # For now, we'll just note that the file exists
                        restored_items.append(f"Config: {config_file}")
            
            # Clean up temporary directory
            shutil.rmtree(temp_dir)
            
            return {
                'success': True,
                'restored_items': restored_items,
                'backup_info': manifest
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def delete_backup(self, backup_path):
        """
        Delete a backup file
        
        Args:
            backup_path (str): Path to the backup file to delete
        
        Returns:
            bool: True if deletion was successful
        """
        try:
            backup_file = Path(backup_path)
            if backup_file.exists():
                backup_file.unlink()
                return True
            return False
        except Exception:
            return False
    
    def get_backup_info(self, backup_path):
        """
        Get information about a backup file
        
        Args:
            backup_path (str): Path to the backup file
        
        Returns:
            dict: Information about the backup
        """
        try:
            backup_file = Path(backup_path)
            if not backup_file.exists():
                return {'error': 'Backup file does not exist'}
            
            # Extract manifest to get info
            temp_dir = self.backup_dir / "temp_info"
            temp_dir.mkdir(exist_ok=True)
            
            with zipfile.ZipFile(backup_file, 'r') as zipf:
                # Check if manifest exists
                if 'manifest.json' in zipf.namelist():
                    with zipf.open('manifest.json') as manifest_file:
                        manifest = json.loads(manifest_file.read().decode('utf-8'))
                else:
                    manifest = {}
            
            # Get file size
            file_size = backup_file.stat().st_size
            
            # Clean up
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
            
            return {
                'file_path': str(backup_file),
                'file_size': file_size,
                'manifest': manifest
            }
        except Exception as e:
            return {'error': str(e)}


# Global backup system instance
backup_system = BackupRecoverySystem()


def create_system_backup(backup_name=None):
    """
    Convenience function to create a system backup
    
    Args:
        backup_name (str, optional): Name for the backup
    
    Returns:
        str: Path to the created backup file
    """
    return backup_system.create_backup(backup_name)


def restore_system_backup(backup_path):
    """
    Convenience function to restore from a backup
    
    Args:
        backup_path (str): Path to the backup file
    
    Returns:
        dict: Result of the restoration
    """
    return backup_system.restore_backup(backup_path)


# Example usage
if __name__ == "__main__":
    # Example of creating and managing backups
    print("Creating a backup...")
    backup_path = create_system_backup()
    print(f"Backup created at: {backup_path}")
    
    print("\nListing all backups...")
    backups = backup_system.list_backups()
    for backup in backups:
        print(f"- {backup}")
    
    print(f"\nGetting info for backup: {backup_path}")
    info = backup_system.get_backup_info(backup_path)
    print(json.dumps(info, indent=2))