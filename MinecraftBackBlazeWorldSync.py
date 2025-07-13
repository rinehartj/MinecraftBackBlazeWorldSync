import os
import sys
import zipfile
import datetime
from pathlib import Path
from dotenv import load_dotenv
from b2sdk.v2 import InMemoryAccountInfo, B2Api

# Load .env file
load_dotenv()

B2_KEY_ID = os.getenv("B2_KEY_ID")
B2_APP_KEY = os.getenv("B2_APP_KEY")
B2_BUCKET_NAME = os.getenv("B2_BUCKET_NAME")
WORLD_PATH = Path(os.getenv("WORLD_PATH"))

BACKUP_LABELS = {
    'daily': lambda now: True,
    'weekly': lambda now: now.weekday() == 6,  # Sunday
    'monthly': lambda now: now.day == 1,
    '6months': lambda now: now.day == 1 and now.month in [1, 7],
    'yearly': lambda now: now.day == 1 and now.month == 1,
    '2years': lambda now: now.day == 1 and now.month == 1 and now.year % 2 == 0,
}

def get_backup_types():
    now = datetime.datetime.now()
    return [label for label, condition in BACKUP_LABELS.items() if condition(now)]

def zip_world(output_dir: Path) -> Path:
    timestamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    zip_name = f"world-{timestamp}.zip"
    zip_path = output_dir / zip_name

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(WORLD_PATH):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(WORLD_PATH.parent)
                zipf.write(file_path, arcname)
    return zip_path

def upload_backup(b2, bucket, zip_path: Path, backup_types: list):
    for btype in backup_types:
        b2_file_name = f"{btype}/world.zip"
        print(f"Uploading {zip_path.name} to B2 as {b2_file_name}")
        bucket.upload_local_file(
            local_file=zip_path,
            file_name=b2_file_name,
            file_infos={'backup-type': btype}
        )

def main():
    temp_dir = Path("./temp_backups")
    temp_dir.mkdir(exist_ok=True)

    print("Zipping world...")
    zip_path = zip_world(temp_dir)

    print("Connecting to B2...")
    info = InMemoryAccountInfo()
    b2_api = B2Api(info)
    b2_api.authorize_account("production", B2_KEY_ID, B2_APP_KEY)
    bucket = b2_api.get_bucket_by_name(B2_BUCKET_NAME)

    backup_types = get_backup_types()
    if not backup_types:
        print("No backup type matches today's date. Exiting.")
        zip_path.unlink()
        return

    print(f"Backup types for today: {backup_types}")
    upload_backup(b2_api, bucket, zip_path, backup_types)

    zip_path.unlink()
    print("Backup completed and temp file deleted.")

if __name__ == "__main__":
    main()
