document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('movie-input');
    const searchBtn = document.getElementById('search-btn');
    const errorMessage = document.getElementById('error-message');
    const resultsSection = document.getElementById('results-section');
    const searchedMovieSpan = document.getElementById('searched-movie');
    const recommendationsGrid = document.getElementById('recommendations-grid');
    const loading = document.getElementById('loading');

    const searchMovie = async () => {
        const query = searchInput.value.trim();
        if (!query) {
            showError('Please enter a movie name.');
            return;
        }

        // Hide old results/errors and show loading
        hideError();
        resultsSection.classList.add('hidden');
        loading.classList.remove('hidden');
        recommendationsGrid.innerHTML = '';

        try {
            const response = await fetch(`/api/recommend?movie=${encodeURIComponent(query)}`);
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Failed to fetch recommendations.');
            }

            displayRecommendations(data.movie, data.recommendations);
        } catch (err) {
            showError(err.message);
        } finally {
            loading.classList.add('hidden');
        }
    };

    const displayRecommendations = (movieName, recommendations) => {
        searchedMovieSpan.textContent = movieName;
        
        recommendations.forEach((movie, index) => {
            const card = document.createElement('div');
            card.className = 'movie-card';
            card.style.animationDelay = `${index * 0.05}s`;
            
            const title = document.createElement('span');
            title.className = 'movie-title';
            title.textContent = movie;
            
            card.appendChild(title);
            recommendationsGrid.appendChild(card);
            
            // Add click listener to search this recommendation
            card.addEventListener('click', () => {
                searchInput.value = movie;
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
    searchBtn.addEventListener('click', searchMovie);
    
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            searchMovie();
        }
    });
});
