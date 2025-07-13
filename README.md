# MinecraftBackBlazeWorldSync

This script was developed to keep a perpetual minecraft world backed up daily, weekly, monthly, 6-monthly, and yearly. This repository consists of a Python virtual environment (venv) that contains a primary Python script `MinecraftBackBlazeWorldSync.py` and environmental parameters file `.env`.

This script backs up to the cloud provider Backblaze. A (private) bucket needs to be created and an Application Key needs to be generated for that bucket. Lifecycle Settings needs to be set to "Keep only the last version of the file". Bucket and key information is stored in the file `.env`.

Minecraft RCON needs to be enabled on the server for this script to work correctly, because commands `save-off`, `save-all flush`, and `save-on` are issued by the server to prevent corruption during folder zipping.

To set up Python virtual environment, Python must be installed and accessible via command prompt.
1. `python -m venv venv`
2. `.\venv\Scripts\activate` for PowerShell
3. `pip install -r requirements.txt`