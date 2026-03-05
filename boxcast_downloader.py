#!/usr/bin/env python3

import base64
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from dotenv import load_dotenv

load_dotenv()
try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG  –  edit these or set them as environment variables
# ─────────────────────────────────────────────────────────────────────────────
CLIENT_ID     = os.getenv("BOXCAST_CLIENT_ID",     "YOUR_CLIENT_ID")
CLIENT_SECRET = os.getenv("BOXCAST_CLIENT_SECRET", "YOUR_CLIENT_SECRET")
ACCOUNT_ID    = os.getenv("BOXCAST_ACCOUNT_ID",    "YOUR_ACCOUNT_ID")
OUTPUT_DIR    = os.getenv("BOXCAST_OUTPUT_DIR",    "./broadcasts")
MAX_WORKERS   = os.getenv("BOXCAST_MAX_WORKERS",   "1")

# How many broadcasts to fetch per page (max 100)
PAGE_SIZE = 50

# Seconds between polling attempts while waiting for MP4 generation
POLL_INTERVAL = 15

# Maximum total seconds to wait for a single broadcast to finish transcoding
MAX_WAIT = 3600   # 1 hour – increase if you have very long broadcasts

try:
    MAX_WORKERS = int(MAX_WORKERS)
except ValueError:
    MAX_WORKERS = 1

# Hard limit max workers to 10
if MAX_WORKERS > 10:
    MAX_WORKERS = 10
elif MAX_WORKERS < 1:
    MAX_WORKERS = 1

# ─────────────────────────────────────────────────────────────────────────────
AUTH_URL = "https://auth.boxcast.com/oauth2/token"
API_BASE = "https://rest.boxcast.com"

# Thread lock for console prints to avoid interleaved text
PRINT_LOCK = threading.Lock()
# ─────────────────────────────────────────────────────────────────────────────


def get_access_token(client_id: str, client_secret: str) -> str:
    """Obtain a bearer token via the Client Credentials grant."""
    credentials = f"{client_id}:{client_secret}"
    encoded = base64.b64encode(credentials.encode()).decode()
    resp = requests.post(
        AUTH_URL,
        headers={
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={"grant_type": "client_credentials"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def api_get(path: str, token: str, params: dict = None) -> dict:
    """Authenticated GET against the BoxCast REST API."""
    resp = requests.get(
        f"{API_BASE}{path}",
        headers={"Authorization": f"Bearer {token}"},
        params=params,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def api_post(path: str, token: str, json_body: dict = None) -> dict:
    """Authenticated POST against the BoxCast REST API."""
    resp = requests.post(
        f"{API_BASE}{path}",
        headers={"Authorization": f"Bearer {token}"},
        json=json_body or {},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def list_past_broadcasts(account_id: str, token: str) -> list:
    """
    Fetch all past broadcasts for the account, handling pagination.
    Returns a list of broadcast summary dicts.
    """
    broadcasts = []
    page = 0
    print("Fetching broadcast list...")
    while True:
        data = api_get(
            f"/account/broadcasts",
            token,
            params={
                "q": "timeframe:past",
                "s": "-starts_at",   # newest first
                "l": PAGE_SIZE,
                "p": page,
            },
        )
        # The API returns a list directly
        if isinstance(data, list):
            batch = data
        else:
            batch = data.get("data", data)

        if not batch:
            break

        broadcasts.extend(batch)
        print(f"  fetched page {page + 1}: {len(batch)} broadcasts "
              f"(total so far: {len(broadcasts)})")

        if len(batch) < PAGE_SIZE:
            break   # last page
        page += 1

    return broadcasts


def build_filepath(broadcast: dict, output_dir: str) -> Path:
    """
    Derive the local path from the broadcast's start time.
    Format:  <output_dir>/YYYY/MM/YYYY-MM-DD-HH-MM.mp4
    """
    starts_at = broadcast.get("starts_at", "")
    try:
        dt = datetime.fromisoformat(starts_at.replace("Z", "+00:00"))
        dt = dt.astimezone(timezone.utc)
    except (ValueError, AttributeError):
        # Fallback: use broadcast id as filename
        dt = None

    if dt:
        folder = Path(output_dir) / dt.strftime("%Y") / dt.strftime("%m")
        filename = dt.strftime("%Y-%m-%d-%H-%M") + ".mp4"
    else:
        bcast_id = broadcast.get("id", "unknown")
        folder = Path(output_dir) / "unknown"
        filename = f"{bcast_id}.mp4"

    return folder / filename


def request_download(broadcast_id: str, recording_id: str, token: str) -> str:
    """
    Ask BoxCast to prepare an MP4 download for a recording.
    Returns the recording_id (same value, used for polling).
    """
    api_post(
        f"/account/recordings/{recording_id}/download",
        token,
    )
    return recording_id


def poll_for_download_url(recording_id: str, token: str) -> str | None:
    """
    Poll the recording resource until the download_url is available.
    Returns the URL string, or None if it times out or fails.
    """
    deadline = time.time() + MAX_WAIT
    attempt = 0
    while time.time() < deadline:
        attempt += 1
        try:
            data = api_get(f"/account/recordings/{recording_id}", token)
        except requests.HTTPError as exc:
            print(f"    [warn] HTTP error while polling: {exc}")
            time.sleep(POLL_INTERVAL)
            continue

        status = data.get("download_status", "")
        url    = data.get("download_url", "")

        if status == "ready" and url:
            return url
        elif status == "failed":
            print(f"    [error] Transcoding failed for recording {recording_id}")
            return None
        else:
            pct = ""
            if status.startswith("processing"):
                pct = f" ({status})"
            print(f"    [poll #{attempt}] status={status}{pct} – "
                  f"waiting {POLL_INTERVAL}s…")
            time.sleep(POLL_INTERVAL)

    print(f"    [error] Timed out waiting for recording {recording_id}")
    return None


def safe_print(*args, **kwargs):
    """Thread-safe print using either tqdm.write or standard print + lock."""
    with PRINT_LOCK:
        if HAS_TQDM:
            tqdm.write(" ".join(str(a) for a in args), **kwargs)
        else:
            print(*args, **kwargs)


def download_file(url: str, dest_path: Path, position: int = 0) -> bool:
    """Stream-download a file, showing a progress bar if tqdm is available."""
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = dest_path.with_suffix(".tmp")

    try:
        with requests.get(url, stream=True, timeout=60) as resp:
            resp.raise_for_status()
            total = int(resp.headers.get("content-length", 0))

            if HAS_TQDM:
                progress = tqdm(
                    total=total,
                    unit="B",
                    unit_scale=True,
                    unit_divisor=1024,
                    desc=dest_path.name,
                    position=position,
                    leave=False
                )
            else:
                progress = None

            with open(tmp_path, "wb") as fh:
                for chunk in resp.iter_content(chunk_size=1024 * 64):
                    fh.write(chunk)
                    if progress:
                        progress.update(len(chunk))

            if progress:
                progress.close()

        tmp_path.rename(dest_path)
        return True

    except Exception as exc:
        safe_print(f"    [error] Download failed: {exc}")
        if tmp_path.exists():
            tmp_path.unlink()
        return False


def process_broadcast(broadcast: dict, token: str, output_dir: str, worker_id: int) -> str:
    """
    Full pipeline for a single broadcast: request → poll → download.
    Returns a status string: "skipped", "success", or "failed".
    """
    bcast_id   = broadcast.get("id", "?")
    name       = broadcast.get("name", "(unnamed)")
    starts_at  = broadcast.get("starts_at", "")

    safe_print(f"\n[{worker_id}] {'─' * 50}\n[{worker_id}] Broadcast : {name}\n[{worker_id}] ID        : {bcast_id}\n[{worker_id}] Starts at : {starts_at}")

    dest_path = build_filepath(broadcast, output_dir)

    # Skip if already downloaded
    if dest_path.exists():
        safe_print(f"[{worker_id}]   ✓ Already exists at {dest_path} – skipping.")
        return "skipped"

    # We need the full broadcast detail to get recording_id
    try:
        detail = api_get(f"/account/broadcasts/{bcast_id}", token)
    except requests.HTTPError as exc:
        safe_print(f"[{worker_id}]   [error] Could not fetch broadcast detail: {exc}")
        return "failed"

    recording_id = detail.get("recording_id", "")
    if not recording_id:
        safe_print(f"[{worker_id}]   [skip] No recording_id – broadcast may not have a recording.")
        return "skipped"

    # Request MP4 generation
    safe_print(f"[{worker_id}]   Requesting MP4 generation (recording_id={recording_id})…")
    try:
        request_download(bcast_id, recording_id, token)
    except requests.HTTPError as exc:
        # 409 usually means a download was already requested; safe to continue
        if exc.response is not None and exc.response.status_code == 409:
            safe_print(f"[{worker_id}]   [info] Download already requested, continuing to poll…")
        else:
            safe_print(f"[{worker_id}]   [error] Could not request download: {exc}")
            return "failed"

    # Poll until ready
    safe_print(f"[{worker_id}]   Waiting for transcode to complete…")
    url = poll_for_download_url(recording_id, token)
    if not url:
        return "failed"

    # Download
    safe_print(f"[{worker_id}]   Downloading → {dest_path}")
    success = download_file(url, dest_path, position=worker_id)
    if success:
        safe_print(f"[{worker_id}]   ✓ Saved to {dest_path}")
        return "success"
    else:
        safe_print(f"[{worker_id}]   ✗ Download failed for {name}")
        return "failed"


def main():
    # ── Validate config ───────────────────────────────────────────────────────
    if "YOUR_" in CLIENT_ID or "YOUR_" in CLIENT_SECRET or "YOUR_" in ACCOUNT_ID:
        print(
            "ERROR: Please set your BoxCast credentials.\n"
            "  Edit the CONFIG section in this script, or export environment variables:\n"
            "    export BOXCAST_CLIENT_ID=...\n"
            "    export BOXCAST_CLIENT_SECRET=...\n"
            "    export BOXCAST_ACCOUNT_ID=...\n"
        )
        sys.exit(1)

    if not HAS_TQDM:
        print("[info] Install 'tqdm' for download progress bars:  pip install tqdm\n")

    # ── Authenticate ─────────────────────────────────────────────────────────
    print("Authenticating with BoxCast API…")
    token = get_access_token(CLIENT_ID, CLIENT_SECRET)
    print("  ✓ Authenticated.\n")

    # ── Fetch broadcast list ──────────────────────────────────────────────────
    broadcasts = list_past_broadcasts(ACCOUNT_ID, token)
    print(f"\nFound {len(broadcasts)} past broadcast(s).\n")

    if not broadcasts:
        print("Nothing to download.")
        return

    # ── Process each broadcast ────────────────────────────────────────────────
    succeeded = 0
    skipped   = 0
    failed    = 0

    print(f"Processing broadcasts with up to {MAX_WORKERS} concurrent worker(s)...")

    # We will pass a worker index to help organize output and progress bars
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_bcast = {
            executor.submit(process_broadcast, bcast, token, OUTPUT_DIR, i % MAX_WORKERS): bcast
            for i, bcast in enumerate(broadcasts)
        }

        for future in as_completed(future_to_bcast):
            bcast = future_to_bcast[future]
            try:
                status = future.result()
                if status == "success":
                    succeeded += 1
                elif status == "skipped":
                    skipped += 1
                else:
                    failed += 1
            except Exception as exc:
                safe_print(f"  [error] Unexpected error processing {bcast.get('name', '(unnamed)')}: {exc}")
                failed += 1

    # ── Summary ───────────────────────────────────────────────────────────────
    safe_print(f"\n{'═' * 60}")
    safe_print(f"Done.  Downloaded: {succeeded}  Skipped: {skipped}  Failed: {failed}")
    safe_print(f"Files saved to: {Path(OUTPUT_DIR).resolve()}")


if __name__ == "__main__":
    main()
