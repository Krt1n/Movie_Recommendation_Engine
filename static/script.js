document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('movie-input');
    const searchBtn = document.getElementById('search-btn');
    const errorMessage = document.getElementById('error-message');
    const resultsSection = document.getElementById('results-section');
    const searchedMovieSpan = document.getElementById('searched-movie');
    const recommendationsGrid = document.getElementById('recommendations-grid');
    const loading = document.getElementById('loading');
    const loadingText = loading ? loading.querySelector('p') : null;

    const searchMovie = async (retryCount = 0) => {
        const query = searchInput.value.trim();
        if (!query) {
            showError('Please enter a movie name.');
            return;
        }

        // Hide old results/errors and show loading
        hideError();
        resultsSection.classList.add('hidden');
        loading.classList.remove('hidden');
        if (loadingText) loadingText.textContent = 'Analyzing movies...';
        recommendationsGrid.innerHTML = '';

        try {
            const response = await fetch(`/api/recommend?movie=${encodeURIComponent(query)}`);
            const data = await response.json();

            // Handle live catalog update during Drain & Swap (HTTP 503)
            if (response.status === 503 && data.status === 'updating' && retryCount < 3) {
                if (loadingText) loadingText.textContent = 'Updating movie catalog with latest releases...';
                await new Promise(resolve => setTimeout(resolve, 1500));
                return searchMovie(retryCount + 1);
            }

            if (!response.ok) {
                throw new Error(data.error || data.message || 'Failed to fetch recommendations.');
            }

            displayRecommendations(data.movie, data.recommendations);
        } catch (err) {
            showError(err.message);
        } finally {
            loading.classList.add('hidden');
            if (loadingText) loadingText.textContent = 'Analyzing movies...';
        }
    };

    const displayRecommendations = (movieName, recommendations) => {
        searchedMovieSpan.textContent = movieName;
        
        recommendations.forEach((movieObj, index) => {
            const card = document.createElement('div');
            card.className = 'movie-card';
            card.style.animationDelay = `${index * 0.05}s`;
            
            if (movieObj.poster_path) {
                const img = document.createElement('img');
                img.src = `https://image.tmdb.org/t/p/w500${movieObj.poster_path}`;
                img.alt = `${movieObj.title} Poster`;
                img.className = 'movie-poster';
                card.appendChild(img);
            }
            
            const title = document.createElement('span');
            title.className = 'movie-title';
            title.textContent = movieObj.title;
            
            card.appendChild(title);
            recommendationsGrid.appendChild(card);
            
            // Add click listener to search this recommendation
            card.addEventListener('click', () => {
                searchInput.value = movieObj.title;
                searchMovie();
            });
        });

        resultsSection.classList.remove('hidden');
    };

    const showError = (msg) => {
        errorMessage.textContent = msg;
        errorMessage.classList.remove('hidden');
    };

    const hideError = () => {
        errorMessage.classList.add('hidden');
    };

    // Event listeners
    searchBtn.addEventListener('click', () => searchMovie());
    
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            searchMovie();
        }
    });
});
