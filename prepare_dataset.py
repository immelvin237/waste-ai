from pathlib import Path
import random
import shutil

SOURCE_DIR = Path("dataset-resized")
OUTPUT_DIR = Path("dataset")

TRAIN_RATIO = 0.70
VAL_RATIO = 0.15
TEST_RATIO = 0.15
SEED = 42

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

if not SOURCE_DIR.exists():
    raise FileNotFoundError(
        f"Cannot find source folder: {SOURCE_DIR.resolve()}\n"
        "Make sure 'dataset-resized' is in the same folder as prepare_dataset.py."
    )

if abs((TRAIN_RATIO + VAL_RATIO + TEST_RATIO) - 1.0) > 0.0001:
    raise ValueError("Train, validation, and test ratios must add up to 1.0.")

random.seed(SEED)

for split in ("train", "val", "test"):
    (OUTPUT_DIR / split).mkdir(parents=True, exist_ok=True)

for class_dir in sorted(SOURCE_DIR.iterdir()):
    if not class_dir.is_dir():
        continue

    images = [
        path for path in class_dir.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    ]

    if not images:
        print(f"Skipping '{class_dir.name}': no supported images found.")
        continue

    random.shuffle(images)

    total = len(images)
    train_end = int(total * TRAIN_RATIO)
    val_end = train_end + int(total * VAL_RATIO)

    split_images = {
        "train": images[:train_end],
        "val": images[train_end:val_end],
        "test": images[val_end:],
    }

    for split_name, image_list in split_images.items():
        destination = OUTPUT_DIR / split_name / class_dir.name
        destination.mkdir(parents=True, exist_ok=True)

        for image_path in image_list:
            shutil.copy2(image_path, destination / image_path.name)

    print(
        f"{class_dir.name}: "
        f"total={total}, "
        f"train={len(split_images['train'])}, "
        f"val={len(split_images['val'])}, "
        f"test={len(split_images['test'])}"
    )

print("\nDataset split completed successfully.")