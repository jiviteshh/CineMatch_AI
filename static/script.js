const form = document.getElementById('recommendForm');
const movieInput = document.getElementById('movieInput');
const genreSelect = document.getElementById('genreSelect');
const languageSelect = document.getElementById('languageSelect');
const loading = document.getElementById('loading');
const notFound = document.getElementById('notFound');
const results = document.getElementById('results');
const suggestionsGrid = document.getElementById('suggestionsGrid');
const resultsGrid = document.getElementById('resultsGrid');
const resultsTitle = document.getElementById('resultsTitle');
const featuredSection = document.getElementById('featuredSection');

form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const movieName = movieInput.value.trim();
    const genre = genreSelect.value;
    const language = languageSelect.value;

    if (!movieName) {
        alert('Please enter a movie name');
        return;
    }

    loading.style.display = 'flex';
    notFound.style.display = 'none';
    results.style.display = 'none';
    if (featuredSection) featuredSection.style.display = 'none';

    try {
        const response = await fetch('/recommend', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                movies: [movieName],
                genres: genre ? [genre] : [],
                languages: language ? [language] : [],
                keyword: ''
            })
        });

        const data = await response.json();

        if (data.not_found) {
            suggestionsGrid.innerHTML = '';
            data.suggestions.forEach(movie => {
                suggestionsGrid.appendChild(createCard(movie));
            });
            notFound.style.display = 'block';
            notFound.scrollIntoView({ behavior: 'smooth', block: 'start' });
        } else if (data.recommendations && data.recommendations.length > 0) {
            let title = `Movies similar to "${movieName}"`;
            if (genre) title += ` in ${genre}`;
            if (language) title += ` (${language})`;
            resultsTitle.textContent = title;

            resultsGrid.innerHTML = '';
            data.recommendations.forEach(movie => {
                resultsGrid.appendChild(createCard(movie));
            });
            results.style.display = 'block';
            results.scrollIntoView({ behavior: 'smooth', block: 'start' });
        } else {
            alert('No recommendations found');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Failed to get recommendations');
    } finally {
        loading.style.display = 'none';
    }
});

function createCard(movie) {
    const card = document.createElement('div');
    card.className = 'card';

    const genres = movie.genres ? movie.genres.split(' ').slice(0, 2) : [];
    const genreTags = genres.map(g => `<span class="genre-tag">${g}</span>`).join('');
    // Use movie.languages if available, otherwise default to English or empty
    const langList = movie.languages ? movie.languages.split(' ').join('/') : '';

    const posterHtml = movie.poster_url && movie.poster_url.trim() ?
        `<img src="${movie.poster_url}" alt="${movie.title}" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex'">
         <div class="card-placeholder" style="display:none;">${movie.title}</div>` :
        `<div class="card-placeholder">${movie.title}</div>`;

    card.innerHTML = `
        <div class="card-poster">
            ${posterHtml}
            <div class="card-overlay">
                <div class="card-info">
                    <h3>${movie.title}</h3>
                    <p>${(movie.overview || '').substring(0, 100)}...</p>
                    <div class="card-meta">
                        ${movie.year ? `<span class="badge"><i class="fas fa-calendar"></i> ${movie.year}</span>` : ''}
                        ${movie.rating ? `<span class="badge"><i class="fas fa-star"></i> ${movie.rating}</span>` : ''}
                        ${movie.similarity > 0 ? `<span class="badge"><i class="fas fa-bolt"></i> ${movie.similarity}%</span>` : ''}
                    </div>
                    <div class="card-genres">${genreTags}</div>
                </div>
            </div>
        </div>
        <div class="card-content">
            <h4 class="card-title">${movie.title}</h4>
            <div class="card-meta">
                 <span class="badge"><strong>${movie.genres ? movie.genres.split(' ')[0] : 'N/A'}</strong></span>
                 <span class="card-rating">⭐ ${movie.rating}/10</span>
                 <span class="card-rating">⭐ ${movie.rating}/10</span>
            </div>
            ${movie.similarity ? `<p class="card-match">Match: ${movie.similarity}%</p>` : ''}
            ${langList ? `<p class="card-languages"><strong>Available In:</strong> ${langList}</p>` : ''}
        </div>
    `;

    card.onclick = () => openModal(movie);
    return card;
}

async function toggleFav(event, movieId, title, overview, genres, year, rating, poster) {
    event.stopPropagation();
    const btn = event.currentTarget;

    try {
        const response = await fetch('/api/favorites', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                action: 'toggle',
                movie_id: movieId,
                movie_title: title,
                overview: overview,
                genres: genres,
                year: year,
                rating: rating,
                poster_url: poster
            })
        });

        const data = await response.json();
        if (data.success) {
            btn.classList.toggle('favorited');
        }
    } catch (error) {
        console.error('Error:', error);
    }
}

const modal = document.getElementById('modal');
const modalGallery = document.getElementById('modalGallery');

function openModal(movie) {
    modalGallery.innerHTML = `
        <div class="gallery-wrapper">
            <img src="${movie.poster_url}" alt="${movie.title}" class="gallery-img">
            <div class="gallery-info">
                <h2>${movie.title}</h2>
                <p><strong>Rating:</strong> ⭐ ${movie.rating || 'N/A'}/10</p>
                <p><strong>Year:</strong> ${movie.year || 'N/A'}</p>
                <p><strong>Languages:</strong> ${movie.languages || 'N/A'}</p>
                <p><strong>Genres:</strong> ${movie.genres || 'N/A'}</p>
                <p><strong>Plot:</strong> ${movie.overview || 'No overview available.'}</p>
            </div>
        </div>
    `;
    modal.style.display = 'flex';
}

function closeModal() {
    modal.style.display = 'none';
}

if (modal) {
    modal.addEventListener('click', (e) => {
        if (e.target === modal) closeModal();
    });
}

// Back to Top Button
const backToTopBtn = document.getElementById('backToTop');

window.addEventListener('scroll', () => {
    if (window.scrollY > 300) {
        backToTopBtn.classList.add('visible');
    } else {
        backToTopBtn.classList.remove('visible');
    }
});

backToTopBtn.addEventListener('click', () => {
    window.scrollTo({
        top: 0,
        behavior: 'smooth'
    });
});
