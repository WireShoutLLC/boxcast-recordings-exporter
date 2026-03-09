# BoxCast Recordings Exporter

## Project Overview

A single-file Python CLI tool that downloads all historical broadcast recordings from the BoxCast API and organizes them locally into a timestamped folder hierarchy.

## Files

- `boxcast_exporter.py` — The entire application (no package structure)
- `README.md` — Brief user-facing documentation
- `.gitignore` — Standard Python ignores

## Running the Script

```bash
export BOXCAST_CLIENT_ID="your_id"
export BOXCAST_CLIENT_SECRET="your_secret"
export BOXCAST_ACCOUNT_ID="your_account"
python boxcast_exporter.py
```

## Environment Variables

| Variable | Purpose | Default |
|---|---|---|
| `BOXCAST_CLIENT_ID` | OAuth2 client ID | `"YOUR_CLIENT_ID"` |
| `BOXCAST_CLIENT_SECRET` | OAuth2 client secret | `"YOUR_CLIENT_SECRET"` |
| `BOXCAST_ACCOUNT_ID` | BoxCast account to query | `"YOUR_ACCOUNT_ID"` |
| `BOXCAST_OUTPUT_DIR` | Local download directory | `"./broadcasts"` |

## Dependencies

```bash
pip install requests tqdm
```

- `requests` — required
- `tqdm` — optional; script degrades gracefully without it

## Tunable Constants (top of `boxcast_exporter.py`)

- `PAGE_SIZE = 50` — Broadcasts per API page (max 100)
- `POLL_INTERVAL = 15` — Seconds between transcode status checks
- `MAX_WAIT = 3600` — Max seconds to wait for a single broadcast to transcode

## Output Structure

```
broadcasts/
  YYYY/
    MM/
      YYYY-MM-DD-HH-MM.mp4
```

## Data Flow

1. Authenticate via OAuth2 Client Credentials against `https://auth.boxcast.com`
2. Fetch all past broadcasts (paginated) from `https://rest.boxcast.com`
3. For each broadcast:
   - Skip if file already exists (idempotent)
   - Fetch full broadcast detail to get `recording_id`
   - POST to trigger MP4 transcode
   - Poll until `download_status` is `ready` or fails/times out
   - Stream download to `.tmp` file, rename on completion

## Key Design Notes

- **Idempotent**: Re-running is safe; existing files are skipped
- **Single file**: No package structure, no setup.py
- **Streaming downloads**: Handles large files without loading into memory
- **409 handling**: Resumes gracefully if a transcode was already requested
- **UTC normalization**: All timestamps converted to UTC before path construction
