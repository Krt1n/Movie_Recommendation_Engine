from flask import Flask, request, jsonify, send_from_directory
import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import os
import time
import threading
import gc
import dataset_sync

app = Flask(__name__, static_folder='static', static_url_path='/')

# Global state and thread safety
df = None
count_matrix = None
data_lock = threading.Lock()
is_reloading = False
dataset_stats = {
    "movie_count": 0,
    "last_reloaded": None,
    "source": "uninitialized"
}
watcher_thread = None

def drain_and_swap(source="cache"):
    """
    Method 1: Drain & Swap (Low-RAM Optimization)
    Frees existing dataset from memory first (RAM drops to ~50MB),
    then streams the new binary cache in ~1.2s (capping RAM at ~1.0-1.2 GB).
    """
    global df, count_matrix, is_reloading, dataset_stats
    with data_lock:
        is_reloading = True
        print("[MemoryManager] Draining old dataset from RAM...")
        # 1. Immediately drop references to existing large dataset
        df = None
        count_matrix = None
        gc.collect()  # Forces immediate garbage collection

        # 2. Fast binary load from Parquet and NPZ (~1.2s)
        new_df, new_count_matrix = dataset_sync.load_from_cache()
        df = new_df
        count_matrix = new_count_matrix
        
        dataset_stats["movie_count"] = len(df)
        dataset_stats["last_reloaded"] = time.strftime('%Y-%m-%d %H:%M:%S')
        dataset_stats["source"] = source
        is_reloading = False
        print(f"[Recommender] Ready! Serving {len(df):,} movies (source: {source}).")

def file_watcher_loop(csv_path=dataset_sync.TARGET_CSV, interval=10):
    """
    Background daemon thread that monitors the dataset CSV file for changes.
    When updated, it builds new cache on disk first, then executes drain_and_swap().
    """
    if not os.path.exists(csv_path):
        return
    last_mtime = os.path.getmtime(csv_path)
    print(f"[Watcher] Started background monitor on {csv_path} (polling every {interval}s).")
    
    while True:
        time.sleep(interval)
        try:
            if not os.path.exists(csv_path):
                continue
            current_mtime = os.path.getmtime(csv_path)
            # Check if file has been modified (with 2s buffer for write completion)
            if current_mtime > last_mtime + 2:
                print(f"[Watcher] Change detected in {csv_path}! Starting live reload...")
                last_mtime = current_mtime
                # 1. Build cache files to disk first (without touching active server data)
                dataset_sync.build_disk_cache()
                # 2. Fast 1.2s Drain & Swap
                drain_and_swap(source="live_watcher")
                print("[Watcher] Live reload completed successfully.")
        except Exception as e:
            print(f"[Watcher] Error monitoring file: {e}")

def start_file_watcher():
    global watcher_thread
    if watcher_thread is None or not watcher_thread.is_alive():
        watcher_thread = threading.Thread(target=file_watcher_loop, daemon=True)
        watcher_thread.start()

def init_recommender():
    """
    Initializes the engine:
    1. Loads dataset instantly from binary cache (< 5s).
    2. Runs Kaggle auto-sync check in the background (non-blocking).
    3. Launches background file watcher.
    """
    # 1. Fast boot from cache if valid
    if dataset_sync.is_cache_valid():
        drain_and_swap(source="startup_cache")
    else:
        print("[Init] Binary cache not found or outdated. Building from CSV...")
        if not os.path.exists(dataset_sync.TARGET_CSV):
            print(f"Error: {dataset_sync.TARGET_CSV} not found.")
            return False
        dataset_sync.build_disk_cache()
        drain_and_swap(source="startup_build")

    # 2. Check Kaggle for remote dataset updates in background (non-blocking)
    def startup_kaggle_check():
        try:
            updated = dataset_sync.check_and_sync_kaggle()
            if updated:
                dataset_sync.build_disk_cache()
                drain_and_swap(source="kaggle_sync")
        except Exception as e:
            print(f"[KaggleHub] Startup check error: {e}")

    threading.Thread(target=startup_kaggle_check, daemon=True).start()
    
    # 3. Start background file watcher
    start_file_watcher()
    return True

# Serve the main frontend UI
@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

# API endpoint for movie recommendations
@app.route('/api/recommend', methods=['GET'])
def recommend():
    # Check if the engine is currently performing a live swap
    if is_reloading or df is None or count_matrix is None:
        return jsonify({
            "status": "updating",
            "message": "Updating movie catalog with latest releases, please retry in a second."
        }), 503

    movie = request.args.get('movie', '').strip()
    if not movie:
        return jsonify({"error": "Please provide a movie name"}), 400

    # Thread-safe snapshot reference
    with data_lock:
        current_df = df
        current_matrix = count_matrix

    # 1. Instant search on pre-computed lowercase titles
    matches = current_df[current_df['title_lower'] == movie.lower()]
    if len(matches) == 0:
        # Fallback: check if the title contains the search query
        matches = current_df[current_df['title_lower'].str.contains(movie.lower(), regex=False, na=False)]
        if len(matches) == 0:
            return jsonify({"error": f"Movie '{movie}' not found in our database."}), 404

    # 2. Get the index of the found movie
    movie_index = matches.index[0]
    
    # 3. Fast O(N) Dynamic Cosine Similarity computation
    similarity_scores = cosine_similarity(current_matrix[movie_index], current_matrix).ravel()
    
    # 4. Top-10 extraction (skipping index 0 which is the movie itself)
    top_indices = np.argsort(similarity_scores)[::-1]
    top_indices = [idx for idx in top_indices if idx != movie_index][:10]

    # 5. Package titles and posters
    recommendations = []
    for idx in top_indices:
        movie_row = current_df.iloc[idx]
        poster = movie_row["poster_path"] if "poster_path" in movie_row and str(movie_row["poster_path"]).strip() not in ('', 'None', 'nan') else None
        
        recommendations.append({
            "title": movie_row["title_clean"],
            "poster_path": str(poster) if poster else None
        })

    return jsonify({"movie": matches.iloc[0]["title_clean"], "recommendations": recommendations})

# API endpoint for live dataset health & status
@app.route('/api/dataset/status', methods=['GET'])
def dataset_status():
    return jsonify({
        "movie_count": dataset_stats["movie_count"],
        "last_reloaded": dataset_stats["last_reloaded"],
        "is_reloading": is_reloading,
        "source": dataset_stats["source"]
    })

# API endpoint to trigger a manual Kaggle sync & live reload
@app.route('/api/dataset/sync', methods=['POST'])
def trigger_sync():
    def background_sync():
        updated = dataset_sync.check_and_sync_kaggle()
        if updated or not dataset_sync.is_cache_valid():
            dataset_sync.build_disk_cache()
            drain_and_swap(source="manual_sync")

    threading.Thread(target=background_sync, daemon=True).start()
    return jsonify({"status": "started", "message": "Kaggle dataset check initiated in the background."})

# Server Startup
if __name__ == '__main__':
    if init_recommender():
        # use_reloader=False prevents double-loading into memory
        app.run(debug=True, use_reloader=False, port=5000)
    else:
        print("Failed to start application due to initialization error.")
