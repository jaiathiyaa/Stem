from flask import Flask, render_template, request
import requests
from textblob import TextBlob
import matplotlib.pyplot as plt
import os

app = Flask(__name__)
app.secret_key = "super_secret_key"

# SerpApi configuration
API_KEY = "your_api_key"
SHOPPING_API_URL = "https://serpapi.com/search.json"
PRODUCT_API_URL = "https://serpapi.com/search.json"

# Helper function to fetch product_id by product name
def get_product_id(product_name):
    params = {
        "engine": "google_shopping",
        "q": product_name,
        "gl": "us",
        "hl": "en",
        "api_key": API_KEY
    }
    try:
        response = requests.get(SHOPPING_API_URL, params=params)
        if response.status_code != 200:
            return None, f"Shopping API error: {response.status_code}"
        results = response.json()
        shopping_results = results.get("shopping_results", [])
        if not shopping_results:
            return None, "No products found for this name."
        # Return the product_id of the first result (you can add logic to select a specific product)
        return shopping_results[0].get("product_id"), None
    except Exception as e:
        return None, f"Error fetching product ID: {str(e)}"

# Helper function to fetch and analyze reviews
def fetch_and_analyze_reviews(product_id):
    params = {
        "engine": "google_product",
        "product_id": product_id,
        "gl": "us",
        "hl": "en",
        "reviews": "1",
        "api_key": API_KEY
    }
    try:
        response = requests.get(PRODUCT_API_URL, params=params)
        if response.status_code != 200:
            return None, f"Product API error: {response.status_code}", None, None, None
        results = response.json()

        # Extract data
        product_results = results.get("product_results", {})
        reviews = results.get("reviews_results", {}).get("reviews", [])

        if not reviews:
            return product_results, "No reviews found.", None, None, None

        # Analyze reviews
        total_rating = 0
        review_count = len(reviews)
        sentiments = []
        ratings = []

        for review in reviews:
            rating = review.get("rating", 0)
            snippet = review.get("content", "") or review.get("snippet", "")
            total_rating += rating
            ratings.append(rating)

            # Sentiment analysis
            analysis = TextBlob(snippet)
            polarity = analysis.sentiment.polarity
            sentiment = "Positive" if polarity > 0 else "Negative" if polarity < 0 else "Neutral"
            sentiments.append({"snippet": snippet, "rating": rating, "sentiment": sentiment})

        average_rating = total_rating / review_count if review_count > 0 else 0
        sentiment_counts = {
            "Positive": sum(1 for s in sentiments if s["sentiment"] == "Positive"),
            "Negative": sum(1 for s in sentiments if s["sentiment"] == "Negative"),
            "Neutral": sum(1 for s in sentiments if s["sentiment"] == "Neutral")
        }

        # Generate rating distribution chart
        plt.figure(figsize=(6, 4))
        plt.hist(ratings, bins=[0.5, 1.5, 2.5, 3.5, 4.5, 5.5], edgecolor="black")
        plt.title("Rating Distribution")
        plt.xlabel("Rating")
        plt.ylabel("Count")
        chart_path = os.path.join("static", "images", "chart.png")
        plt.savefig(chart_path)
        plt.close()

        return product_results, None, average_rating, sentiments, sentiment_counts
    except Exception as e:
        return None, f"Error fetching reviews: {str(e)}", None, None, None

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        product_name = request.form.get("product_name")
        if not product_name:
            return render_template("index.html", error="Please enter a product name.")

        # Get product_id
        product_id, error = get_product_id(product_name)
        if error:
            return render_template("index.html", error=error)

        # Fetch and analyze reviews
        product_results, error, average_rating, sentiments, sentiment_counts = fetch_and_analyze_reviews(product_id)
        if error:
            return render_template("index.html", error=error)

        return render_template(
            "results.html",
            product_title=product_results.get("title", "Unknown"),
            average_rating=average_rating,
            review_count=len(sentiments),
            sentiments=sentiments,
            sentiment_counts=sentiment_counts,
            chart_path="images/chart.png"
        )

    return render_template("index.html")

if __name__ == "__main__":
    os.makedirs("static/images", exist_ok=True)
    app.run(debug=True)
