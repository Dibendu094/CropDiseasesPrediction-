"""Fetch model checkpoints that aren't in the repo.

The two checkpoints total ~1.1 GB, well past GitHub's 100 MB per-file limit, so
they are git-ignored. Locally you just keep them in `backend/models/`. On a
host like Render the directory starts empty, so each file is downloaded once at
boot from a URL supplied via the environment:

    MODEL_URL_EFFICIENTNET=https://.../best_epoch_4_acc_98.70.pth
    MODEL_URL_VIT=https://.../vit_b16_epoch_02%20(2).pth

Any direct-download host works — a GitHub Release asset, S3, R2, or Supabase
Storage. If a file is already present it is left alone, so restarts are fast.
"""

import os
import shutil
import tempfile
import urllib.request

MODELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")

# filename -> environment variable holding its download URL
CHECKPOINTS = {
    "best_epoch_4_acc_98.70.pth": "MODEL_URL_EFFICIENTNET",
    "vit_b16_epoch_02 (2).pth": "MODEL_URL_VIT",
}

# A truncated download is worse than a missing one — it fails deep inside torch
# with a confusing error. Anything smaller than this is treated as garbage.
MIN_BYTES = 5 * 1024 * 1024


def _download(url, dest):
    """Download to a temp file first, then move into place, so an interrupted
    transfer can never leave a half-written checkpoint behind."""
    name = os.path.basename(dest)
    print(f"[models] downloading {name} ...")
    os.makedirs(os.path.dirname(dest), exist_ok=True)

    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(dest), suffix=".part")
    os.close(fd)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AgriCare/1.0"})
        with urllib.request.urlopen(req, timeout=120) as r, open(tmp, "wb") as f:
            total = int(r.headers.get("Content-Length") or 0)
            done = 0
            step = max(total // 10, 1) if total else None
            next_mark = step
            while True:
                chunk = r.read(1024 * 256)
                if not chunk:
                    break
                f.write(chunk)
                done += len(chunk)
                if step and done >= next_mark:
                    print(f"[models]   {name}: {done * 100 // total}%")
                    next_mark += step

        size = os.path.getsize(tmp)
        if size < MIN_BYTES:
            raise IOError(f"downloaded only {size} bytes — looks like an error page, not a checkpoint")

        shutil.move(tmp, dest)
        print(f"[models] {name} ready ({size / 1e6:.0f} MB)")
        return True
    except Exception as e:
        print(f"[models] FAILED to download {name}: {e}")
        return False
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


def ensure_models():
    """Make sure every checkpoint is on disk. Returns True if all are present.

    Never raises — a missing model is reported so the caller can decide whether
    to degrade or stop, rather than crashing the whole process at import time.
    """
    os.makedirs(MODELS_DIR, exist_ok=True)
    all_ok = True

    for filename, env_var in CHECKPOINTS.items():
        path = os.path.join(MODELS_DIR, filename)

        if os.path.exists(path) and os.path.getsize(path) >= MIN_BYTES:
            continue

        url = os.environ.get(env_var, "").strip()
        if not url:
            print(f"[models] MISSING: {filename}  (set {env_var} to download it, "
                  f"or copy the file into backend/models/)")
            all_ok = False
            continue

        if not _download(url, path):
            all_ok = False

    return all_ok


if __name__ == "__main__":
    ok = ensure_models()
    print("all checkpoints present" if ok else "some checkpoints are missing")
