import shutil
import os
from datetime import datetime

def backup_nexus():
    # 1. Define the project name and the new backup folder name
    project_dir = os.getcwd()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"nexus_genesis_backup_{timestamp}"
    
    # 2. Go one level up to save the backup outside the active project folder
    parent_dir = os.path.dirname(project_dir)
    backup_path = os.path.join(parent_dir, backup_name)
    
    print(f"--- [ ARCHITECT: INITIATING SYSTEM BACKUP ] ---")
    print(f"Source: {project_dir}")
    print(f"Destination: {backup_path}.zip")
    
    try:
        # 3. Create a ZIP archive of the entire folder
        # We use 'zip' format and ignore the 'data' folder if it's too large (optional)
        shutil.make_archive(backup_path, 'zip', project_dir)
        
        print(f"--- [ BACKUP COMPLETE: {backup_name}.zip ] ---")
    except Exception as e:
        print(f"[ERROR]: Backup failed: {e}")

if __name__ == "__main__":
    backup_nexus()