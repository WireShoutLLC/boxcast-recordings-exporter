BoxCast Broadcast Downloader
-----------------------------
Downloads historical broadcasts from the BoxCast API and organizes them locally
into folders by YYYY/MM, with files named YYYY-MM-DD-HH-MM.mp4.

## Prerequisites

- Python 3
- Git

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/your-username/boxcast-downloader.git
cd boxcast-downloader
```

### 2. Set up a Python Virtual Environment

It is recommended to use a virtual environment to manage dependencies.

**On Linux/macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**On Windows:**
```cmd
python -m venv venv
venv\Scripts\activate
```

### 3. Install dependencies

With the virtual environment activated, install the required packages:

```bash
pip install -r requirements.txt
```

## Configuration

1. Copy the sample environment file to `.env`:

   **On Linux/macOS:**
   ```bash
   cp .env.sample .env
   ```

   **On Windows:**
   ```cmd
   copy .env.sample .env
   ```

2. Open the newly created `.env` file in your preferred text editor and fill in your BoxCast credentials:

   - `BOXCAST_CLIENT_ID`: Your BoxCast API client ID
   - `BOXCAST_CLIENT_SECRET`: Your BoxCast API client secret
   - `BOXCAST_ACCOUNT_ID`: Your BoxCast Account ID
   - `BOXCAST_OUTPUT_DIR`: (Optional) The directory where broadcasts will be downloaded. Defaults to `./broadcasts`.

   *Note: You need a BoxCast API client_id and client_secret. Contact BoxCast support if you don't have them yet.*

## Usage

Once installed and configured, run the downloader script:

```bash
python boxcast_downloader.py
```

## Notes

- The download process is asynchronous: BoxCast must first transcode the recording to MP4, which can take several minutes per broadcast.
- Already-downloaded files are skipped automatically.
