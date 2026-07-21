from flask import Flask, request, jsonify, send_from_directory
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import os

app = Flask(__name__, static_folder='static', static_url_path='/')

# Global variables to store the dataframe and similarity matrix
df = None
cosine_sim = None

def init_recommender():
    global df, cosine_sim
    try:
        df = pd.read_csv("movie_dataset.csv")
    except FileNotFoundError:
        print("Error: movie_dataset.csv not found.")
        return False

    features = ['keywords', 'cast', 'genres', 'director']
    for feature in features:
        df[feature] = df[feature].fillna('')

    def combine_features(row):
        return row['keywords'] + " " + row['cast'] + " " + row['genres'] + " " + row['director']

    df["combined_features"] = df.apply(combine_features, axis=1)

    cv = CountVectorizer()
    count_matrix = cv.fit_transform(df["combined_features"])
    cosine_sim = cosine_similarity(count_matrix)
    print("Recommender initialized.")
    return True

# Serve the main frontend UI when users visit the home page (/)
@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

# API endpoint that the frontend calls to get recommendations
@app.route('/api/recommend', methods=['GET'])
def recommend():
    # 1. Grab the movie name the user typed in the search bar
    movie = request.args.get('movie', '')
    if not movie:
        return jsonify({"error": "Please provide a movie name"}), 400

    # 2. Safety check: make sure the math matrix was actually built
    if df is None or cosine_sim is None:
        return jsonify({"error": "Recommender engine is not initialized properly"}), 500

    # 3. Search the dataframe for the movie (case-insensitive)
    matches = df[df.title.str.lower() == movie.lower()]
    if len(matches) == 0:
        return jsonify({"error": f"Movie '{movie}' not found in our database."}), 404

    # 4. Get the index of the found movie and look up its similarity scores
    movie_index = matches.index[0]
    similar_movies = list(enumerate(cosine_sim[movie_index]))
    
    # 5. Sort the scores from highest to lowest and grab the top 10 (skipping the first one, which is the movie itself)
    sorted_similar_movies = sorted(similar_movies, key=lambda x: x[1], reverse=True)[1:11]

    # 6. Translate the math indices back into readable movie titles
    recommendations = []
    for element in sorted_similar_movies:
        movie_title = df[df.index == element[0]]["title"].values[0]
        recommendations.append(movie_title)

    # 7. Package the results as JSON and send them back to the frontend
    return jsonify({"movie": matches["title"].values[0], "recommendations": recommendations})

# Server Startup
if __name__ == '__main__':
    # Build the heavy math matrix BEFORE starting the server so it's super fast
    if init_recommender():
        app.run(debug=True, port=5000)
    else:
        print("Failed to start application due to initialization error.")
