from pathlib import Path
import os
import shutil


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TARGET_DIR = PROJECT_ROOT / "data" / "raw" / "restaurant-dataset"
DATASET_ID = "mohdshahnawazaadil/restaurant-dataset"

os.environ.setdefault("KAGGLEHUB_CACHE", str(PROJECT_ROOT / ".kagglehub"))

import kagglehub


def copy_dataset(download_path: Path, target_dir: Path) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)

    for item in download_path.iterdir():
        destination = target_dir / item.name
        if item.is_dir():
            if destination.exists():
                shutil.rmtree(destination)
            shutil.copytree(item, destination)
        else:
            shutil.copy2(item, destination)


def main() -> None:
    download_path = Path(kagglehub.dataset_download(DATASET_ID))
    copy_dataset(download_path, TARGET_DIR)
    print(f"Dataset copied to: {TARGET_DIR}")


if __name__ == "__main__":
    main()
