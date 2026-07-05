from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
RESTAURANT_DATASET_PATH = RAW_DATA_DIR / "restaurant-dataset" / "Dataset .csv"
