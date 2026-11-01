# prepare_data.py - run this ONCE to turn the Kaggle "Book Recommendation
# Dataset" (Books.csv + Ratings.csv) into the books.csv our website uses.
#
# Put Books.csv and Ratings.csv in the same folder as this file, then run:
#     python prepare_data.py

import pandas as pd

MIN_RATINGS = 20  # ignore books with fewer ratings than this

# 1) LOAD both files
books = pd.read_csv("Books.csv", encoding="latin-1", low_memory=False,
                    on_bad_lines="skip", dtype={"ISBN": str})
ratings = pd.read_csv("Ratings.csv", encoding="latin-1", low_memory=False,
                      dtype={"ISBN": str})
print("Books loaded:", len(books), "| Ratings loaded:", len(ratings))

# 2) KEEP only real ratings (0 means "user did not rate it")
ratings = ratings[ratings["Book-Rating"] > 0]

# 3) AVERAGE the ratings per book (grouped by ISBN) and count them
stats = ratings.groupby("ISBN")["Book-Rating"].agg(["mean", "count"]).reset_index()
stats = stats[stats["count"] >= MIN_RATINGS]

# 4) JOIN the averages onto the book details
df = books.merge(stats, on="ISBN")

# 5) CLEAN the year column (it has junk text in it) and rating scale
df["year"] = pd.to_numeric(df["Year-Of-Publication"], errors="coerce")
df = df[(df["year"] > 1000) & (df["year"] <= 2026)]
df["year"] = df["year"].astype(int)
df["rating"] = (df["mean"] / 2).round(2)  # 0-10 scale -> 0-5 scale like Goodreads

# 6) RENAME to the columns the website expects
df = df.rename(columns={"Book-Title": "title", "Book-Author": "author",
                        "ISBN": "isbn", "count": "ratings_count",
                        "Image-URL-L": "cover"})
df["genre"] = "Unknown"  # this dataset has no genre column

# one row per title+author (the same book can appear under many ISBNs)
df = df.sort_values("ratings_count", ascending=False)
df = df.drop_duplicates(subset=["title", "author"])

out = df[["isbn", "title", "author", "genre", "rating", "year",
          "ratings_count", "cover"]]
out.to_csv("books.csv", index=False)
print("Done! Saved", len(out), "books to books.csv")
