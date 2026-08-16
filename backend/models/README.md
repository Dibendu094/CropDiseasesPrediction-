# Model checkpoints

This directory is intentionally empty in git. The two checkpoints total **~1.1 GB**,
far past GitHub's 100 MB per-file limit, so they are excluded by `.gitignore`.

| File | Architecture | Classes | Size | Role |
|---|---|---|---|---|
| `best_epoch_4_acc_98.70.pth` | EfficientNet-B3 (timm) | 91 | ~131 MB | Backup model |
| `vit_b16_epoch_02 (2).pth` | ViT-B/16, 384px (timm) | 91 | ~1.0 GB | Primary model |

## Local development

Copy both `.pth` files into this directory. That's all — the app finds them
automatically.

```
backend/models/
├── best_epoch_4_acc_98.70.pth
└── vit_b16_epoch_02 (2).pth
```

## Deployed hosts (Render, Docker, a fresh clone)

Upload the checkpoints somewhere with direct-download links — a **GitHub
Release asset**, S3, Cloudflare R2, or Supabase Storage — then set:

```env
MODEL_URL_EFFICIENTNET=https://github.com/<you>/<repo>/releases/download/v1.0/best_epoch_4_acc_98.70.pth
MODEL_URL_VIT=https://github.com/<you>/<repo>/releases/download/v1.0/vit_b16_epoch_02.pth
```

`backend/model_store.py` downloads anything missing on first boot, writing to a
temp file and moving it into place so an interrupted transfer can't leave a
corrupt checkpoint behind. Files already present are skipped, so restarts are fast.

> **Publishing to a GitHub Release** is usually easiest — the 2 GB per-asset
> limit comfortably fits both files, and the download URL is stable and public.

## Label spaces

The two checkpoints were trained on **different datasets** and do not share a
label vocabulary:

- `best_epoch_4_acc_98.70.pth` → `backend/data/class_names.json`
- `vit_b16_epoch_02 (2).pth` → `backend/data/names (3).json`

`backend/ensemble.py` reconciles both onto a shared canonical `(crop, disease)`
vocabulary of 131 classes. Swapping a checkpoint means updating its label file too.
