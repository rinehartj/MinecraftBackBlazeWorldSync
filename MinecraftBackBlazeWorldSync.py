import os
import zipfile
import datetime
from pathlib import Path
from dotenv import load_dotenv
from b2sdk.v2 import InMemoryAccountInfo, B2Api
from mcrcon import MCRcon
from time import sleep
import shutil

# Load environment variables
load_dotenv()
B2_KEY_ID = os.getenv("B2_KEY_ID")
B2_APP_KEY = os.getenv("B2_APP_KEY")
B2_BUCKET_NAME = os.getenv("B2_BUCKET_NAME")
SERVER_PATH = os.getenv("SERVER_PATH")
RCON_HOST = os.getenv("RCON_HOST", "localhost")
RCON_PORT = int(os.getenv("RCON_PORT", 25575))
RCON_PASSWORD = os.getenv("RCON_PASSWORD")

BACKUP_DIR = Path(__file__).parent / "backups"
BACKUP_TAGS = ["daily", "weekly", "monthly", "6month", "yearly", "2year"]

# Initialize B2
info = InMemoryAccountInfo()
b2_api = B2Api(info)
b2_api.authorize_account("production", B2_KEY_ID, B2_APP_KEY)
bucket = b2_api.get_bucket_by_name(B2_BUCKET_NAME)

def get_backup_tag():
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

def rcon_backup_prepare():
    print("[INFO] Connecting to RCON to freeze world saves...")
    with MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT) as mcr:
        mcr.command("save-off")
        mcr.command("save-all flush")
    print("[INFO] World saving disabled and flushed.")
    sleep(5)

def rcon_backup_complete():
    print("[INFO] Re-enabling world saving via RCON...")
    with MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT) as mcr:
        mcr.command("save-on")
    print("[INFO] World saving re-enabled.")

def zip_worlds():
    """Create a ZIP archive of all 'world*' folders, excluding session.lock"""
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
                        if filename == "session.lock":
                            continue
                        file_path = os.path.join(foldername, filename)
                        arcname = os.path.relpath(file_path, SERVER_PATH)
                        zipf.write(file_path, arcname)
    return archive_path

def upload_backup(archive_path, tag):
    print(f"[INFO] Uploading to B2 with tag '{tag}'...")
    for file_version, _ in bucket.ls():
        if file_version.file_name.startswith(f"{tag}_"):
            print(f"[INFO] Deleting old backup: {file_version.file_name}")
            bucket.delete_file_version(file_version.id_, file_version.file_name)

    file_name = f"{tag}_{archive_path.name}"
    bucket.upload_local_file(local_file=archive_path, file_name=file_name)
    print(f"[SUCCESS] Uploaded: {file_name}")

def cleanup_local_backups():
    backups = sorted(BACKUP_DIR.glob("mc_backup_*.zip"), key=os.path.getmtime)
    while len(backups) > 10:
        old = backups.pop(0)
        print(f"[INFO] Deleting old local backup: {old.name}")
        old.unlink()

def main():
    print("[START] Minecraft Backup Script Running...")

    BACKUP_DIR.mkdir(exist_ok=True)
    tag = get_backup_tag()

    try:
        rcon_backup_prepare()
        archive_path = zip_worlds()
    finally:
        rcon_backup_complete()

    upload_backup(archive_path, tag)
    cleanup_local_backups()
    print("[DONE] Backup complete.")

if __name__ == "__main__":
    main()
