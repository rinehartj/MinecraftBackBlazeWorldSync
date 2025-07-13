import os
import zipfile
import datetime
import shutil
from dotenv import load_dotenv
from b2sdk.v2 import InMemoryAccountInfo, B2Api
from pathlib import Path

# Load environment variables
load_dotenv()
B2_KEY_ID = os.getenv("B2_KEY_ID")
B2_APP_KEY = os.getenv("B2_APP_KEY")
B2_BUCKET_NAME = os.getenv("B2_BUCKET_NAME")
SERVER_PATH = os.getenv("SERVER_PATH")
BACKUP_DIR = Path(__file__).parent / "backups"

# Initialize B2
info = InMemoryAccountInfo()
b2_api = B2Api(info)
b2_api.authorize_account("production", B2_KEY_ID, B2_APP_KEY)
bucket = b2_api.get_bucket_by_name(B2_BUCKET_NAME)

# Define backup tags
BACKUP_TAGS = ["daily", "weekly", "monthly", "6month", "yearly", "2year"]

def get_backup_tag():
    """Determine which tag to upload based on current date."""
    today = datetime.date.today()
    weekday = today.weekday()
    day = today.day
    month = today.month
    year = today.year

    return {
        0: "daily",
        1: "weekly" if weekday == 6 else "daily",  # Sunday
        2: "monthly" if day <= 7 else "daily",
        3: "6month" if month in (1, 7) and day <= 7 else "daily",
        4: "yearly" if month == 1 and day <= 7 else "daily",
        5: "2year" if year % 2 == 0 and month == 1 and day <= 7 else "daily"
    }[min(5, len(BACKUP_TAGS)-1)]

def zip_worlds():
    """Create a ZIP archive of all world folders."""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_name = f"mc_backup_{timestamp}.zip"
    archive_path = BACKUP_DIR / archive_name

    print(f"[INFO] Creating archive: {archive_name}")
    with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for item in os.listdir(SERVER_PATH):
            full_path = os.path.join(SERVER_PATH, item)
            if os.path.isdir(full_path) and item.startswith("world"):
                for foldername, subfolders, filenames in os.walk(full_path):
                    for filename in filenames:
                        file_path = os.path.join(foldername, filename)
                        arcname = os.path.relpath(file_path, SERVER_PATH)
                        zipf.write(file_path, arcname)
    return archive_path

def upload_backup(archive_path, tag):
    """Upload the backup to B2 under the correct tag, ensuring only one file per tag."""
    # Clean up existing files with the same tag
    print(f"[INFO] Uploading to B2 with tag '{tag}'...")
    for file_version, _ in bucket.ls():
        if file_version.file_name.startswith(f"{tag}_"):
            print(f"[INFO] Deleting old backup: {file_version.file_name}")
            bucket.delete_file_version(file_version.id_, file_version.file_name)

    # Upload new file
    file_name = f"{tag}_{archive_path.name}"
    bucket.upload_local_file(local_file=archive_path, file_name=file_name)
    print(f"[SUCCESS] Uploaded: {file_name}")

def cleanup_local_backups():
    """Optionally clean up old local backups (keep last 10)."""
    backups = sorted(BACKUP_DIR.glob("mc_backup_*.zip"), key=os.path.getmtime)
    while len(backups) > 10:
        old = backups.pop(0)
        print(f"[INFO] Deleting old local backup: {old.name}")
        old.unlink()

def main():
    print("[START] Minecraft Backup Script Running...")

    # Create backup dir if missing
    BACKUP_DIR.mkdir(exist_ok=True)

    tag = get_backup_tag()
    archive_path = zip_worlds()
    upload_backup(archive_path, tag)
    cleanup_local_backups()

    print("[DONE] Backup complete.")

if __name__ == "__main__":
    main()
