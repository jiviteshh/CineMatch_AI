import pandas as pd

# Load both datasets
df1 = pd.read_csv("movies.csv")          # Your original file
df2 = pd.read_csv("final_movies.csv")    # Kaggle + credits merged file

# Combine and remove duplicates (based on movie title or id)
merged = pd.concat([df1, df2], ignore_index=True)

# Optional — drop duplicate movies (keeping best data)
merged.drop_duplicates(subset=["title"], inplace=True)  # or ["id"]

# Save final unified dataset
merged.to_csv("merged_movies.csv", index=False)

print("🎉 FINAL MERGED DATASET CREATED → merged_movies.csv")
print("Total Movies:", len(merged))
