BoxCast Broadcast Downloader
-----------------------------
Downloads historical broadcasts from the BoxCast API and organizes them locally
into folders by YYYY/MM, with files named YYYY-MM-DD-HH-MM.mp4.

Usage:
    1. Set your credentials and account ID in the CONFIG section below
       (or use environment variables).
    2. Run:  python boxcast_downloader.py

Notes:
    - You need a BoxCast API client_id and client_secret. Contact BoxCast
      support if you don't have them yet.
    - The download process is asynchronous: BoxCast must first transcode the
      recording to MP4, which can take several minutes per broadcast.
    - Already-downloaded files are skipped automatically.
