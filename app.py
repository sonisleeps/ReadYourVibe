# app.py - the "brain" of the website.
# Run it with:  python app.py   then open http://127.0.0.1:5000

from flask import Flask, render_template, request, abort
import pandas as pd
import requests  # lets Python talk to websites / APIs

app = Flask(__name__)

MAX_SHOWN = 60  # the dataset is big, so show only the first 60 matches

# 1) LOAD THE DATA (once, when the server starts)
books = pd.read_csv("books.csv", dtype={"isbn": str})

# Make sure every column we use exists (so old/simple CSVs still work)
for col, default in [("isbn", ""), ("genre", "Unknown"),
                     ("ratings_count", 0), ("cover", "")]:
    if col not in books.columns:
        books[col] = default
books["isbn"] = books["isbn"].fillna("")
books["cover"] = books["cover"].fillna("")

books["id"] = books.index  # a number for every book, used in /book/<id>


def get_genres():
    """Sorted list of unique genres."""
    return sorted(books["genre"].unique())


def filter_books(genres, min_rating, search, sort_by):
    """Apply the user's choices. Returns (first 60 matches, total matches)."""
    result = books.copy()

    if genres:  # list of ticked genres; empty = no genre filter
        result = result[result["genre"].isin(genres)]

    result = result[result["rating"] >= min_rating]

    if search:
        s = search.lower()
        match_title = result["title"].str.lower().str.contains(s, regex=False)
        match_author = result["author"].str.lower().str.contains(s, regex=False)
        result = result[match_title | match_author]

    if sort_by == "rating":
        result = result.sort_values("rating", ascending=False)
    elif sort_by == "popular":
        result = result.sort_values("ratings_count", ascending=False)
    elif sort_by == "newest":
        result = result.sort_values("year", ascending=False)
    elif sort_by == "title":
        result = result.sort_values("title")

    total = len(result)
    return result.head(MAX_SHOWN).to_dict("records"), total


# 2) OPEN LIBRARY: fetch extra details from the internet

details_cache = {}  # remembers GOOD results so we never fetch a book twice
HEADERS = {"User-Agent": "BookFinderStudentProject/1.0 (college project)"}


def get_json(url, params=None):
    """Download JSON from a URL. Returns None if the page doesn't exist."""
    r = requests.get(url, params=params, headers=HEADERS, timeout=15)
    print("GET", r.status_code, r.url)  # debug line: watch your terminal
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()


def clean_description(desc):
    """Descriptions are sometimes a string, sometimes {"value": "..."}."""
    if isinstance(desc, dict):
        desc = desc.get("value")
    return desc[:700] if desc else None


def fetch_details(isbn, title, author):
    """Ask Open Library about one book. Always returns a dictionary."""
    key = (isbn, title, author)
    if key in details_cache:
        return details_cache[key]

    info = {"cover": None, "description": None, "pages": None,
            "first_year": None, "subjects": []}
    failed = False

    try:
        work_key = None

        # Step A: look the book up by ISBN (most accurate)
        if isbn:
            edition = get_json(f"https://openlibrary.org/isbn/{isbn}.json")
            if edition:
                info["pages"] = edition.get("number_of_pages")
                if edition.get("covers"):
                    info["cover"] = f"https://covers.openlibrary.org/b/id/{edition['covers'][0]}-L.jpg"
                if edition.get("works"):
                    work_key = edition["works"][0]["key"]   # e.g. /works/OL123W

        # Step B: if the ISBN wasn't found, search by title + author
        if not work_key:
            data = get_json("https://openlibrary.org/search.json",
                            {"title": title, "author": author, "limit": 1})
            docs = data.get("docs", []) if data else []
            if docs:
                doc = docs[0]
                work_key = doc.get("key")
                info["pages"] = info["pages"] or doc.get("number_of_pages_median")
                info["first_year"] = doc.get("first_publish_year")
                if not info["cover"] and doc.get("cover_i"):
                    info["cover"] = f"https://covers.openlibrary.org/b/id/{doc['cover_i']}-L.jpg"

        # Step C: the description and subjects live on the "work" page
        if work_key:
            work = get_json(f"https://openlibrary.org{work_key}.json")
            if work:
                info["description"] = clean_description(work.get("description"))
                info["subjects"] = work.get("subjects", [])[:8]
        print("DESCRIPTION found:", bool(info["description"]))

    except Exception as e:
        failed = True
        print("Open Library error:", e)

    if not failed:  # only remember it if the internet calls worked
        details_cache[key] = info
    return info


# 3) ROUTES

def page(books_list, total, title, genres, selected, min_rating, search, sort_by):
    return render_template(
        "index.html", books=books_list, total=total, genres=genres,
        selected_genres=selected, min_rating=min_rating,
        search=search, sort_by=sort_by, title=title,
    )


@app.route("/")
def home():
    selected = request.args.getlist("genre")        # all ticked genre boxes
    min_rating = float(request.args.get("min_rating", 0))
    search = request.args.get("search", "").strip()
    sort_by = request.args.get("sort", "rating")

    results, total = filter_books(selected, min_rating, search, sort_by)
    return page(results, total, "Browse books", get_genres(),
                selected, min_rating, search, sort_by)


@app.route("/random")
def random_book():
    # pick a random book that matches the current filters
    selected = request.args.getlist("genre")
    min_rating = float(request.args.get("min_rating", 0))
    search = request.args.get("search", "").strip()

    pool = books[books["rating"] >= min_rating]
    if selected:
        pool = pool[pool["genre"].isin(selected)]
    if search:
        s = search.lower()
        pool = pool[pool["title"].str.lower().str.contains(s, regex=False) |
                    pool["author"].str.lower().str.contains(s, regex=False)]

    pick = pool.sample(1).to_dict("records") if len(pool) else []
    return page(pick, len(pick), "Your random pick", get_genres(),
                selected, min_rating, search, "rating")


@app.route("/book/<int:book_id>")
def book_details(book_id):
    # <int:book_id> grabs the number from the URL, e.g. /book/5
    match = books[books["id"] == book_id]
    if match.empty:
        abort(404)
    book = match.iloc[0].to_dict()
    info = fetch_details(book["isbn"], book["title"], book["author"])
    return render_template("book.html", book=book, info=info)


if __name__ == "__main__":
    app.run(debug=True)
