import pandas as pd
import pickle
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

TOP_K = 50  # store only top 50 recommendations per movie

def load_and_merge():
    df1 = pd.read_csv("movies.csv")
    df2 = pd.read_csv("final_movies.csv")
    
    df = pd.concat([df1, df2], ignore_index=True)
    df.drop_duplicates(subset=["title"], inplace=True)
    print(f"📌 Total movies loaded = {len(df)}")
    return df

def preprocess(df):
    df['title'] = df['title'].fillna("Unknown Movie").astype(str)  # <-- FIX

    df["genres"] = df["genres"].fillna("")
    df["overview"] = df["overview"].fillna("")
    df["industry"] = df["industry"].fillna("Hollywood")
    df["languages"] = df["languages"].fillna("English")
    df["cast"] = df["cast"].fillna("unknown")
    df["poster_url"] = df["poster_url"].fillna("https://i.ibb.co/7z6mLQp/no-image.jpg")

    df["combined_features"] = (
        df["overview"] + " "
        + df["genres"] + " "
        + df["cast"] + " "
        + df["industry"]
    )
    return df


def train():
    df = preprocess(load_and_merge())
    print("🔍 Creating TF-IDF matrix...")
    
    vectorizer = TfidfVectorizer(stop_words="english", max_features=20000)
    mat = vectorizer.fit_transform(df["combined_features"])

    print("⚡ Building Top-K Similarity Index...")
    top_similar = {}

    for i in range(len(df)):
        sims = cosine_similarity(mat[i], mat).flatten()
        best = sims.argsort()[-TOP_K-1:-1][::-1]  # top K movies
        top_similar[i] = best.tolist()

        if i % 2000 == 0:
            print(f"Processed {i}/{len(df)} movies...")

    with open("model.pkl", "wb") as f:
        pickle.dump({
            "df": df,
            "similar": top_similar,
            "index": {t.lower(): i for i, t in enumerate(df['title'])}
        }, f)

    print("\n🎉 MODEL READY — No memory issues!")
    print(f"Stored TOP-{TOP_K} recommendations for each movie.")
    print("File saved → model.pkl")

if __name__ == "__main__":
    train()
