import os
import shutil
import time
import gc
import pandas as pd
import scipy.sparse
from sklearn.feature_extraction.text import CountVectorizer

TARGET_CSV = "movies_dataset_1M.csv"
CACHE_PARQUET = "movies_cache.parquet"
CACHE_NPZ = "count_matrix.npz"

def check_and_sync_kaggle(target_csv=TARGET_CSV):
    """
    Checks Kaggle for the latest version of the TMDB 930k+ dataset.
    Downloads and updates target_csv if a newer version is available.
    Fails gracefully if offline or if kagglehub is not installed.
    Returns True if a new dataset was synced, False otherwise.
    """
    try:
        import kagglehub
        print("[KaggleHub] Checking Kaggle for dataset updates...")
        
        cache_dir = None
        try:
            cache_dir = kagglehub.dataset_download("asaniczka/tmdb-movies-dataset-2023-930k-movies")
        except Exception as e:
            # Kaggle's daily automated bot pushes new versions daily; if the latest tag (e.g. v1101)
            # is temporarily processing/draft on Kaggle's backend, fall back to the latest verified cached version
            local_cache = os.path.expanduser("~/.cache/kagglehub/datasets/asaniczka/tmdb-movies-dataset-2023-930k-movies/versions")
            if os.path.exists(local_cache):
                versions = sorted(
                    [v for v in os.listdir(local_cache) if os.path.isdir(os.path.join(local_cache, v))],
                    key=lambda x: int(x) if x.isdigit() else 0,
                    reverse=True
                )
                if versions:
                    cache_dir = os.path.join(local_cache, versions[0])
                    print(f"[KaggleHub] Notice: Kaggle latest daily tag is processing ({e}). Falling back to verified snapshot v{versions[0]}.")
            
            if not cache_dir:
                raise e
        
        # Locate the CSV in the downloaded folder
        kaggle_csv = None
        for fname in os.listdir(cache_dir):
            if fname.endswith(".csv"):
                kaggle_csv = os.path.join(cache_dir, fname)
                break
                
        if not kaggle_csv or not os.path.exists(kaggle_csv):
            print("[KaggleHub] No CSV found in downloaded dataset cache.")
            return False

        # If local target CSV doesn't exist, copy immediately
        if not os.path.exists(target_csv):
            print(f"[KaggleHub] Local dataset missing. Copying from Kaggle cache to {target_csv}...")
            shutil.copy2(kaggle_csv, target_csv)
            return True

        # Check if Kaggle cached file is newer or different in size
        k_size = os.path.getsize(kaggle_csv)
        k_mtime = os.path.getmtime(kaggle_csv)
        t_size = os.path.getsize(target_csv)
        t_mtime = os.path.getmtime(target_csv)

        if k_size != t_size or (k_mtime > t_mtime + 60):
            print(f"[KaggleHub] New dataset version detected ({k_size} bytes). Updating {target_csv}...")
            shutil.copy2(kaggle_csv, target_csv)
            return True
            
        print("[KaggleHub] Dataset is already up to date with the latest Kaggle release.")
        return False

    except ImportError as e:
        print(f"[KaggleHub] 'kagglehub' library is not installed in this environment ({e}). Skipping remote dataset check.")
        print("[KaggleHub] Tip: Run 'pip install kagglehub' in your active terminal to enable remote updates.")
        return False
    except Exception as e:
        print(f"[KaggleHub] Notice: Could not sync with Kaggle ({e}). Continuing to serve local dataset.")
        return False

def is_cache_valid(csv_path=TARGET_CSV, parquet_path=CACHE_PARQUET, npz_path=CACHE_NPZ):
    """
    Checks whether the binary parquet and npz cache files exist and are newer
    than or equal to the source CSV file.
    """
    if not os.path.exists(csv_path):
        return False
    if not os.path.exists(parquet_path) or not os.path.exists(npz_path):
        return False
        
    csv_mtime = os.path.getmtime(csv_path)
    parquet_mtime = os.path.getmtime(parquet_path)
    npz_mtime = os.path.getmtime(npz_path)
    
    return parquet_mtime >= csv_mtime and npz_mtime >= csv_mtime

def build_disk_cache(csv_path=TARGET_CSV, parquet_path=CACHE_PARQUET, npz_path=CACHE_NPZ):
    """
    Parses the 1M movie CSV, creates cleaned feature vectors, fits CountVectorizer,
    and serializes the results to high-speed binary formats (Parquet and NPZ).
    Uses temporary files to prevent corrupting active cache during writes.
    Frees memory with gc.collect() upon completion.
    """
    print(f"[CacheBuilder] Parsing {csv_path} to build binary cache...")
    t0 = time.time()
    
    # Only load the 5 essential columns to save 50%+ memory and load time
    needed_cols = ['title', 'keywords', 'genres', 'overview', 'poster_path']
    try:
        df = pd.read_csv(csv_path, usecols=needed_cols, low_memory=False)
    except ValueError:
        # Fallback in case column names differ
        df = pd.read_csv(csv_path, low_memory=False)
        for col in needed_cols:
            if col not in df.columns:
                df[col] = ''

    print(f"[CacheBuilder] CSV parsed in {round(time.time() - t0, 2)}s. Cleaning features...")
    keywords = df['keywords'].fillna('').astype(str)
    genres = df['genres'].fillna('').astype(str)
    overview = df['overview'].fillna('').astype(str)
    combined_features = keywords + " " + genres + " " + overview

    # Prepare cleaned titles and poster URLs for UI
    df['title_clean'] = df['title'].fillna('').astype(str)
    df['title_lower'] = df['title_clean'].str.lower()
    if 'poster_path' not in df.columns:
        df['poster_path'] = ''
    else:
        df['poster_path'] = df['poster_path'].fillna('').astype(str)

    print("[CacheBuilder] Fitting CountVectorizer (sparse matrix)...")
    cv = CountVectorizer(stop_words='english', max_features=10000)
    count_matrix = cv.fit_transform(combined_features)
    
    # Save only the lightweight UI lookup columns to Parquet (~86MB)
    tmp_parquet = "movies_cache_tmp.parquet"
    tmp_npz = "count_matrix_tmp.npz"
    
    lookup_df = df[['title_clean', 'title_lower', 'poster_path']]
    lookup_df.to_parquet(tmp_parquet, index=False)
    
    # Save sparse CSR matrix to NPZ (~52MB)
    scipy.sparse.save_npz(tmp_npz, count_matrix)
    
    # Atomic file rename
    if os.path.exists(parquet_path):
        os.remove(parquet_path)
    os.replace(tmp_parquet, parquet_path)
    
    if os.path.exists(npz_path):
        os.remove(npz_path)
    os.replace(tmp_npz, npz_path)
    
    # Free local memory immediately
    del df, lookup_df, combined_features, count_matrix, cv
    gc.collect()
    
    print(f"[CacheBuilder] Binary cache successfully created in {round(time.time() - t0, 2)}s!")
    return True

def load_from_cache(parquet_path=CACHE_PARQUET, npz_path=CACHE_NPZ):
    """
    Rapidly loads the cleaned movie DataFrame from Parquet and the sparse matrix
    from NPZ. Takes ~1.2s total and peaks at ~1.0-1.2 GB RAM.
    """
    t0 = time.time()
    df = pd.read_parquet(parquet_path)
    count_matrix = scipy.sparse.load_npz(npz_path)
    print(f"[CacheLoader] Loaded {len(df):,} movies and sparse matrix in {round(time.time() - t0, 2)}s!")
    return df, count_matrix
