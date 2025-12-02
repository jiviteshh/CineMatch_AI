import os
import pickle
import logging
import numpy as np
from flask import Flask, render_template, request, jsonify
from werkzeug.middleware.proxy_fix import ProxyFix
import re
import hashlib
import textwrap
from pathlib import Path
import math
import time
import os

# Pillow imports will be attempted lazily in the generator to avoid import errors

# ===========================
# Logging
# ===========================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===========================
# Flask App
# ===========================
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# ===========================
# Load Model
# ===========================
model_data = None

def load_model():
    global model_data
    if model_data is None:
        if not os.path.exists("model.pkl"):
            raise FileNotFoundError("Model not found. Run train_model.py first.")
        with open("model.pkl", "rb") as f:
            raw = pickle.load(f)
        
        # Normalize keys
        movies = raw.get("movies") or raw.get("df")
        similarity = raw.get("similarity") or raw.get("cosine_sim") or raw.get("similar")
        index = raw.get("index") or raw.get("indices") or {t: i for i, t in enumerate(movies["title"])}
        
        model_data = {
            "movies": movies,
            "similarity": similarity,
            "index": index
        }
        logger.info(f"Model loaded. Total movies: {len(movies)}")
    return model_data

def normalize_title(title):
    return title.strip().lower()


def safe_int(val):
    """Safely convert a value to int, returning None if it's missing or NaN."""
    try:
        if val is None:
            return None
        # handle pandas NaN (float)
        if isinstance(val, float) and math.isnan(val):
            return None
        # try direct int
        return int(val)
    except Exception:
        try:
            s = str(val).strip()
            if s == '' or s.lower() == 'nan':
                return None
            return int(float(s))
        except Exception:
            return None


# ===========================
# Poster handling (frontend-only placeholders)
# ===========================

# simple in-memory cache for poster URL health checks: url -> bool (True if reachable image)
POSTER_CHECK_CACHE = {}


def resolve_poster_url(poster: str, title_fallback: str = '', industry: str = None, rating: float = None) -> str:
    """Return a usable poster URL or empty string.

    Rules:
    - If `poster` is an absolute HTTP(S) URL, return it if a lightweight HEAD check succeeds (optional).
    - If `poster` is a local static path (starts with '/static/'), return as-is.
    - If `poster` is a relative path, prefix with TMDB base and return if HEAD check succeeds.
    - If poster missing or unreachable, return an empty string so the frontend shows a placeholder.
    """
    if poster and isinstance(poster, str) and poster.strip():
        poster = poster.strip()
        # local static path -> return as-is
        if poster.startswith('/static/'):
            return poster

        # build full URL if relative
        if poster.startswith('http://') or poster.startswith('https://'):
            full_url = poster
        else:
            full_url = f"https://image.tmdb.org/t/p/w342/{poster.lstrip('/')}"

        # lightweight HEAD check (optional): skip if network blocked
        cached = POSTER_CHECK_CACHE.get(full_url)
        if cached is not None:
            return full_url if cached else ''

        try:
            try:
                import requests
                resp = requests.head(full_url, timeout=3, allow_redirects=True)
                ok = (resp.status_code == 200 and 'image' in (resp.headers.get('content-type') or '').lower())
            except Exception:
                # fallback to urllib; HEAD may not be supported everywhere
                from urllib.request import Request, urlopen
                req = Request(full_url, method='HEAD')
                with urlopen(req, timeout=3) as resp:
                    info = resp.info()
                    ok = ('image' in (info.get_content_type() or ''))
        except Exception:
            ok = False

        POSTER_CHECK_CACHE[full_url] = bool(ok)
        return full_url if ok else ''

    # missing poster -> empty string for frontend placeholder
    return ''

# ===========================
# Utility: Random / Featured / Filters
# ===========================
def get_random_movies(count=10):
    data = load_model()
    movies = data["movies"]
    idxs = np.random.choice(len(movies), min(count, len(movies)), replace=False)
    results = []
    for i in idxs:
        m = movies.iloc[i]
        poster = resolve_poster_url(
            m.get("poster_url", ""),
            m.get('title', ''),
            industry=m.get('industry', None),
            rating=m.get('vote_average', None)
        )
        results.append({
            "title": m["title"],
            "overview": m["overview"],
            "genres": m["genres"],
            "poster_url": poster,
            "industry": m.get("industry", "Hollywood"),
            "languages": m.get("languages", "English"),
            "rating": float(m.get("vote_average", 0)),
            "year": safe_int(m.get("release_year", None)),
            "id": safe_int(m.get("id", None))
        })
    return results

def get_all_genres():
    movies = load_model()["movies"]
    gset = set()
    for val in movies["genres"]:
        gset.update(val.split())
    return sorted(gset)

def get_featured_picks():
    """Return a varied set of featured picks from a RANDOM language.

    Strategy:
    - Pick a random language from the dataset.
    - Filter movies by that language.
    - Choose up to 6 movies from the top 100 rated in that language.
    - Choose 4 random movies from the remaining list.
    - Combine and shuffle.
    """
    movies = load_model()["movies"]
    
    # Extract all unique languages
    all_langs = set()
    for val in movies["languages"].dropna():
        all_langs.update(val.split())
    all_langs = sorted(list(all_langs))
    
    if not all_langs:
        return []

    # Pick one random language
    selected_lang = np.random.choice(all_langs)
    
    # Filter movies by this language
    # We check if the selected language is in the 'languages' string column
    lang_movies = movies[movies["languages"].apply(lambda x: selected_lang in x.split() if isinstance(x, str) else False)]
    
    n_total = min(10, len(lang_movies))
    if n_total == 0:
        return []

    # top pool and random picks from the filtered list
    top_pool = lang_movies.sort_values("vote_average", ascending=False).head(100 if len(lang_movies) >= 100 else len(lang_movies))
    try:
        pick_top = top_pool.sample(min(6, len(top_pool)))
    except Exception:
        pick_top = top_pool.head(min(6, len(top_pool)))

    # ensure we don't sample the same movies
    remaining = lang_movies.drop(pick_top.index, errors='ignore')
    try:
        pick_random = remaining.sample(n_total - len(pick_top))
    except Exception:
        pick_random = remaining.head(max(0, n_total - len(pick_top)))

    combined = list(pick_top.iterrows()) + list(pick_random.iterrows())

    # shuffle order for variety
    np.random.shuffle(combined)

    featured_list = []
    for _, m in combined:
        poster = resolve_poster_url(
            m.get("poster_url", ""),
            m.get('title', ''),
            rating=m.get('vote_average', None)
        )
        featured_list.append({
            "title": m["title"],
            "overview": m["overview"],
            "genres": m["genres"],
            "poster_url": poster,
            "languages": m.get("languages", "English"),
            "rating": float(m.get("vote_average", 0)),
            "year": safe_int(m.get("release_year", None)),
            "id": safe_int(m.get("id", None))
        })

    return featured_list

# ===========================
# Recommendation
# ===========================
def get_recommendations(movie_titles, genres=None, languages=None, top_n=10):
    data = load_model()
    movies = data["movies"]
    sim = data["similarity"]
    index = data["index"]

    if not movie_titles:
        return []

    seed = normalize_title(movie_titles[0])
    base_idx = None
    for title, idx in index.items():
        if normalize_title(title) == seed:
            base_idx = idx
            break
    if base_idx is None:
        return []

    row = sim[base_idx]
    scores = list(enumerate(row))
    scores = sorted(scores, key=lambda x: x[1], reverse=True)

    # Take top 50 then pick random top_n
    slice_for_random = scores[:50] if len(scores) > 50 else scores
    chosen = np.random.choice(len(slice_for_random), min(top_n, len(slice_for_random)), replace=False)
    final_sim = [slice_for_random[i] for i in chosen]

    max_score = max([s for _, s in final_sim], default=1.0)
    recommendations = []
    for idx, score in final_sim:
        if idx == base_idx or score <= 0:
            continue
        m = movies.iloc[idx]

        # Filters
        if genres:
            movie_genres = set((m.get("genres") or "").split())
            if not any(g in movie_genres for g in genres):
                continue
        if languages:
            movie_langs = set((m.get("languages") or "").split())
            if not any(l in movie_langs for l in languages):
                continue

        poster = resolve_poster_url(
            m.get("poster_url", ""),
            m.get('title', ''),
            rating=m.get('vote_average', None)
        )

        recommendations.append({
            "title": m["title"],
            "overview": m["overview"],
            "genres": m["genres"],
            "languages": m.get("languages", "English"),
            "similarity": round((float(score) / max_score) * 100, 1),
            "poster_url": poster,
            "id": safe_int(m.get("id", None)),
            "year": safe_int(m.get("release_year", None)),
            "rating": float(m.get("vote_average", 0))
        })

    return recommendations

def get_all_languages():
    movies = load_model()["movies"]
    lset = set()
    for val in movies["languages"].dropna():
        # Replace commas with spaces to handle joined languages
        cleaned = val.replace(',', ' ')
        parts = [p.strip() for p in cleaned.split()]
        for p in parts:
            # Filter out garbage: must be at least 2 chars, mostly letters, no question marks
            if len(p) > 1 and p.replace('-', '').isalpha() and '?' not in p:
                lset.add(p)
    return sorted(list(lset))

# ===========================
# Routes
# ===========================
@app.route("/")
def home():
    m = load_model()
    return render_template(
        "index.html",
        movies=sorted(m["movies"]["title"].tolist()),
        genres=get_all_genres(),
        languages=get_all_languages(),
        featured=get_featured_picks()
    )

@app.route("/recommend", methods=["POST"])
def recommend_route():
    data = request.get_json() or {}
    movies = data.get("movies", [])
    genres = data.get("genres", [])
    languages = data.get("languages", [])

    if not movies:
        return jsonify({"error": "No movie selected"}), 400

    rec = get_recommendations(movies, genres, languages=languages)
    if not rec:
        return jsonify({
            "not_found": True,
            "searched_movie": movies[0],
            "suggestions": get_featured_picks()
        })

    return jsonify({"recommendations": rec})

    return jsonify({"recommendations": rec})

def summarize_dataset(df):
    """
    Analyzes the movies DataFrame and returns high-level statistics.
    
    Returns a dictionary containing:
    - total_unique_languages
    - total_unique_genres
    - year_range (min, max)
    - industry_counts
    - language_counts
    - genre_counts
    """
    from collections import Counter
    
    # 1. Languages Analysis
    # Split comma/space separated languages and clean them
    all_langs = []
    for val in df["languages"].dropna():
        # Reuse the cleaning logic from get_all_languages for consistency
        cleaned = val.replace(',', ' ')
        parts = [p.strip() for p in cleaned.split()]
        for p in parts:
            if len(p) > 1 and p.replace('-', '').isalpha() and '?' not in p:
                all_langs.append(p)
    
    language_counts = dict(Counter(all_langs))
    
    # 2. Genres Analysis
    all_genres = []
    for val in df["genres"].dropna():
        # Genres are typically space separated in this dataset based on previous code
        parts = [p.strip() for p in val.split()]
        all_genres.extend(parts)
        
    genre_counts = dict(Counter(all_genres))
    
    # 3. Industry Analysis
    # Check if industry column exists
    if "industry" in df.columns:
        industry_counts = df["industry"].value_counts().to_dict()
    else:
        industry_counts = {}

    # 4. Year Range
    if "release_year" in df.columns:
        # Convert to numeric, coercing errors to NaN, then drop NaNs
        years = pd.to_numeric(df["release_year"], errors='coerce').dropna()
        if not years.empty:
            min_year = int(years.min())
            max_year = int(years.max())
            year_range = {"start": min_year, "end": max_year}
        else:
            year_range = {"start": None, "end": None}
    else:
        year_range = {"start": None, "end": None}

    return {
        "total_unique_languages": len(language_counts),
        "total_unique_genres": len(genre_counts),
        "year_range": year_range,
        "industry_counts": industry_counts,
        "language_counts": language_counts,
        "genre_counts": genre_counts
    }

@app.route("/summary")
def summary_route():
    import pandas as pd
    data = load_model()
    movies_df = data["movies"]
    summary = summarize_dataset(movies_df)
    return jsonify(summary)

# ===========================
# Run Server
# ===========================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

