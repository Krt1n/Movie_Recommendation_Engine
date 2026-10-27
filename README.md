# Movie Recommendation Engine (V2 - Massive Scale)

This project is a high-performance, content-based movie recommendation system built from scratch. Version 2 has been completely re-architected to handle a massive dataset of nearly **1.5 Million movies** while maintaining millisecond response times and sub-700 MB memory consumption.

The backend is powered by Python and Flask, utilizing Scikit-Learn for text vectorization and cosine similarity mathematics, Apache Parquet and SciPy NPZ for rapid binary caching, and a background daemon file watcher for zero-downtime hot-reloading. The frontend is a vanilla JavaScript and CSS application that queries the API, automatically handles retries during live catalog updates, and dynamically renders movie posters.

## Project Structure

```text
.
├── app.py
├── dataset_sync.py
├── download_dataset.py
├── movies_dataset_1M.csv
├── movies_cache.parquet
├── count_matrix.npz
├── requirements.txt
└── static/
    ├── index.html
    ├── script.js
    └── style.css
```

* [`app.py`](./app.py): Entry point for the Flask server, holding the $O(N)$ dynamic recommendation engine, background file watcher, and API routes.
* [`dataset_sync.py`](./dataset_sync.py): Dedicated synchronization and caching module handling Kaggle auto-sync, binary serialization (Parquet + NPZ), and sub-5-second dataset hydration.
* [`download_dataset.py`](./download_dataset.py): Standalone script for one-off manual dataset retrieval via Kaggle.
* [`static/`](./static/): Frontend assets for the web application served directly by Flask.

---

## Getting Started

### 1. Prerequisites & Installation

Ensure you have Python 3.9+ installed. Install project dependencies into your active environment:

```powershell
pip install -r requirements.txt
```

> [!NOTE]
> **About `kagglehub` Authentication & Sync:**  
> The [`kagglehub`](https://github.com/Kaggle/kagglehub) integration automatically checks Kaggle in the background for fresh daily TMDB snapshots. 
> * **Authentication:** Provide your Kaggle API token by setting the `KAGGLE_API_TOKEN` environment variable or saving your token to `~/.kaggle/access_token` (or `~/.kaggle/kaggle.json`).
> * **Smart Fallback:** If Kaggle's automated daily bot is currently processing a new version tag (returning a temporary 404), the engine automatically falls back to the latest verified snapshot. If completely offline or unauthenticated, it seamlessly serves all 1.46M movies from your high-speed local binary cache.

### 2. Running the Server

Start the Flask application:

```powershell
python app.py
```

* **First Run (Cold Build):** If binary cache files are missing or out of date, the engine automatically parses `movies_dataset_1M.csv`, vectorizes the text features, and compiles `movies_cache.parquet` and `count_matrix.npz` (~25–35s).
* **Subsequent Runs (Warm Boot):** The engine hydrates the entire 1.46 Million movies and sparse matrix in **~4.8 seconds** with a RAM footprint of **~688 MB**.

Visit **`http://localhost:5000`** in your browser to interact with the UI.

---

## API Reference

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/` | `GET` | Serves the frontend web interface. |
| `/api/recommend?movie=<name>` | `GET` | Returns top 10 recommended movies and poster URLs. Returns `503` if an in-memory Drain & Swap is in progress. |
| `/api/dataset/status` | `GET` | Returns JSON status including movie count, last reload timestamp, and reload state. |
| `/api/dataset/sync` | `POST` | Triggers a background Kaggle update check and live reload on demand. |

---

## Techniques & Engineering Decisions

* **Pre-Computed Binary Serialization:** Rather than re-parsing 645 MB of raw CSV text and re-vectorizing 1.46 Million text overviews on every startup (~60–80s), the engine serializes the cleaned lookup DataFrame to [Apache Parquet](https://parquet.apache.org/) and the word-frequency matrix to [SciPy NPZ](https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.save_npz.html). This drops cold boot time down to **~4.8 seconds**.
* **Method 1 "Drain & Swap" (Low-RAM Architecture):** When a dataset update occurs, instead of doubling RAM by holding both matrices in memory simultaneously, the engine prepares cache files on disk first, drops active references via explicit garbage collection (`gc.collect()`), and streams the new binary cache in ~1.2s. Total memory usage remains capped under **~700 MB – 1.2 GB** at all times.
* **Non-Blocking Kaggle Auto-Sync with Smart Fallback:** On server startup, a background worker checks Kaggle via [kagglehub](https://github.com/Kaggle/kagglehub) for new snapshot releases without blocking immediate server availability. It authenticates with `KAGGLE_API_TOKEN` / `~/.kaggle/access_token`, automatically falls back to the latest verified snapshot if a daily tag is in mid-publish on Kaggle, and seamlessly defaults to the local cache if offline.
* **Background Live File-Watcher:** A background daemon thread continuously monitors `movies_dataset_1M.csv`. If modifications are detected, it re-indexes and triggers an in-memory hot-swap without restarting the Flask server process.
* **Dynamic $O(N)$ Similarity:** Instead of pre-computing a massive $1,500,000 \times 1,500,000$ matrix (which would require petabytes of RAM), the engine computes the `cosine_similarity` dynamically on the fly between the user's queried movie vector and the pre-computed sparse feature matrix.
* **CSS Custom Properties (Variables):** The frontend relies on [CSS Variables](https://developer.mozilla.org/en-US/docs/Web/CSS/Using_CSS_custom_properties) to manage themes and global colors efficiently across the application.
* **Asynchronous Fetch with 503 Retry:** The client application uses the [Fetch API](https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API/Using_Fetch) with `async/await` syntax to make non-blocking HTTP requests, automatically displaying a catalog update spinner and retrying if a search coincides with a 1.2-second Drain & Swap reload.

---

## Libraries and Technologies

* **[Flask](https://flask.palletsprojects.com/):** A lightweight WSGI web application framework used to handle routing and serve the JSON API endpoint.
* **[Pandas](https://pandas.pydata.org/):** Used for loading and sanitizing the 1.46M row movie dataset.
* **[PyArrow](https://arrow.apache.org/docs/python/):** Columnar data serialization engine used to read and write high-performance Parquet cache files.
* **[SciPy](https://scipy.org/):** Provides sparse matrix persistence and serialization (`scipy.sparse.save_npz` and `scipy.sparse.load_npz`).
* **[Kagglehub](https://github.com/Kaggle/kagglehub):** A library used to programmatically check and download TMDB Movies Dataset updates directly from Kaggle.
* **[Scikit-learn (CountVectorizer)](https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.CountVectorizer.html):** Converts the raw text of movie features (genres, keywords, overview) into a sparse matrix of word counts, optimized with `max_features=10000` to save memory.
* **[Scikit-learn (cosine_similarity)](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.pairwise.cosine_similarity.html):** Calculates the cosine angle between feature vectors dynamically to find mathematically similar movies.
* **[Outfit Font](https://fonts.google.com/specimen/Outfit):** UI typography loaded via Google Fonts.
