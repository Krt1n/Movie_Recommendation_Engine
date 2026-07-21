# Movie Recommendation Engine (V1)

A custom content-based movie recommendation engine built entirely from scratch using Python, Pandas, and Scikit-Learn. The system is wrapped in a lightweight Flask web server, providing a clean API to interact with the engine.

## Overview

This project (Version 1) analyzes a dataset of 5,000 movies to find similarities based on multiple features:
- **Keywords**
- **Cast**
- **Genres**
- **Director**

Instead of relying on external API recommendation engines, this project implements its own mathematical engine using **Cosine Similarity**. 

## How It Works

1. **Data Ingestion:** The engine loads a local `movie_dataset.csv`.
2. **Feature Engineering:** Missing `NaN` values are sanitized, and the selected text features (cast, crew, keywords, genres) are concatenated into a single "combined_features" string for every movie.
3. **Vectorization:** A `CountVectorizer` converts these massive text strings into a mathematical sparse matrix of word frequencies.
4. **Similarity Pre-calculation:** The Flask server uses `cosine_similarity` to pre-calculate a massive $5000 \times 5000$ similarity matrix the moment the server boots up. This caches the math in RAM.
5. **API Lookups:** When a user searches for a movie via the web interface, the server performs an $O(1)$ lookup in the pre-calculated matrix and returns the top 10 most similar titles instantly via a JSON API.

## Project Structure

* `app.py`: The Flask web server and API routes. Contains the core logic for the recommendation engine.
* `recommender.ipynb` & `consine_similarity.ipynb`: Jupyter notebooks used for prototyping the math and logic before moving it to production in the server.
* `app_explanation.md`: Detailed documentation explaining the Python syntax and Flask routing logic used in the server.
* `static/`: Contains the frontend web UI (HTML, CSS, JS) that interacts with the Flask API.

## Running the Project locally

1. Ensure you have Python installed.
2. Install the required dependencies: `pip install -r requirements.txt` (Make sure pandas, scikit-learn, and flask are installed).
3. Run the server: `python app.py`
4. Open your web browser and navigate to `http://localhost:5000` to interact with the UI.
