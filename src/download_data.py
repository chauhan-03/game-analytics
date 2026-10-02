"""python src/download_data.py  ->  data/raw/*.csv (about 190 MB)."""

from data import RAW, download

if __name__ == "__main__":
    print(f"Downloading into {RAW}")
    download()
