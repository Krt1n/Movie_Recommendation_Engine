# Movie Recommendation Engine

This project is a content-based movie recommendation system. It processes a dataset of 5,000 movies and recommends similar titles based on shared features like cast, crew, keywords, and genres. The backend is built with Python and serves an API using Flask, while the frontend is a vanilla JavaScript and CSS application that queries the API.

## Project Structure

```text
.
├── app.py
├── app_explanation.md
├── movie_dataset.csv
├── requirements.txt
└── static/
    ├── index.html
    ├── script.js
    └── style.css
```

The [`static/`](./static/) directory contains the frontend assets for the web application. The backend serves these files directly. The [`app.py`](./app.py) file serves as the entry point for the Flask server and holds the recommendation engine logic.

## Techniques

* **CSS Custom Properties (Variables):** The frontend relies on [CSS Variables](https://developer.mozilla.org/en-US/docs/Web/CSS/Using_CSS_custom_properties) to manage themes and global colors efficiently across the application.
* **Asynchronous Fetch:** The client application uses the [Fetch API](https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API/Using_Fetch) with `async/await` syntax to make non-blocking HTTP GET requests to the Flask backend. 
* **Pre-computed Similarity Matrix:** To optimize response times, the backend calculates the mathematical similarities between all movies during server startup rather than on each request. The API endpoint performs a direct $O(1)$ lookup against this matrix in memory.

## Libraries and Technologies

* **[Flask](https://flask.palletsprojects.com/):** A lightweight WSGI web application framework used to handle routing and serve the JSON API endpoint.
* **[Pandas](https://pandas.pydata.org/):** Used for loading and sanitizing the CSV dataset. It handles missing `NaN` values and concatenates the text features efficiently.
* **[Scikit-learn (CountVectorizer)](https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.CountVectorizer.html):** Converts the raw text of movie features into a sparse matrix of word counts, turning unstructured text into structured data.
* **[Scikit-learn (cosine_similarity)](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.pairwise.cosine_similarity.html):** Calculates the cosine angle between the feature vectors. This measures how similar two movies are regardless of the total amount of text in their descriptions.
* **[Outfit Font](https://fonts.google.com/specimen/Outfit):** The UI typography utilizes the Outfit font family loaded via Google Fonts.
