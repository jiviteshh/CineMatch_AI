import pandas as pd
import ast

# ============================
# Load Raw Data Files
# ============================
movies = pd.read_csv("dataset/movies_metadata.csv", low_memory=False)
credits = pd.read_csv("dataset/credits.csv")

# ============================
# Convert ID to numeric for merging
# ============================
movies["id"] = pd.to_numeric(movies["id"], errors="coerce")
credits["id"] = pd.to_numeric(credits["id"], errors="coerce")

# ============================
# Merge datasets using movie ID
# ============================
df = movies.merge(credits, on="id", how="left")

# ============================
# Extract Top Cast Names
# ============================
def extract_cast(cast_column):
    try:
        cast_list = ast.literal_eval(cast_column)
        return ", ".join([actor["name"] for actor in cast_list[:5]])  # Top 5 actors
    except:
        return ""

df["cast"] = df["cast"].apply(extract_cast)

# ============================
# Convert Genres JSON → Pipe Format
# ============================
def convert_genres(g):
    try:
        genres = ast.literal_eval(g)
        return " | ".join([x["name"] for x in genres])
    except:
        return ""

df["genres"] = df["genres"].apply(convert_genres)

# ============================
# Release Year
# ============================
df["release_year"] = df["release_date"].str[:4]

# ============================
# Poster URL Convert
# ============================
df["poster_url"] = "https://image.tmdb.org/t/p/w500" + df["poster_path"].astype(str)

# ============================
# Spoken Languages Extract
# ============================
def extract_languages(val):
    try:
        languages = ast.literal_eval(val)
        return ", ".join([lang["name"] for lang in languages])
    except:
        return ""

df["languages"] = df["spoken_languages"].apply(extract_languages)

# ============================
# Identify Industry
# ============================
def get_industry(lang):
    if isinstance(lang, str):
        if "Telugu" in lang or "Hindi" in lang or "Malayalam" in lang or "Tamil" in lang or "Kannada" in lang:
            return "Indian Cinema"
        elif "English" in lang:
            return "Hollywood"
    return "Other"

df["industry"] = df["languages"].apply(get_industry)

# ============================
# Select Final Columns
# ============================
final = df[[
    "id","title","overview","genres","release_year",
    "vote_average","cast","poster_url","industry","languages"
]]

# ============================
# Save Final Dataset
# ============================
final.to_csv("final_movies.csv", index=False)

print("\n🎉 Dataset successfully created → final_movies.csv")
print("Rows:", len(final))
