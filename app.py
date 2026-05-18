# app.py
from flask import Flask, request, jsonify, send_from_directory, session, redirect, url_for, send_file
import pandas as pd
import sqlite3
import io, base64
import os
import math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from flask_cors import CORS
import datetime

from Scraper import DB_NAME, TABLE_NAME
from components.recommendation_engine import add_better_alternatives, get_top_recommendations, add_similar_products
from components.value_scorer import calculate_value_score
from components.sentiment import add_sentiment_scores
from components.alerts import add_user_alert
from components.data_cleaner import remove_outliers
from components.caching_service import get_cached_or_scrape

frontend_folder = os.path.join(os.getcwd(), "frontend", "dist")
app = Flask(__name__, static_folder=frontend_folder, static_url_path="/")
app.secret_key = "product_analysis_super_secret_key"
CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)

_search_cache = {}

def load_data_from_db():
    conn = sqlite3.connect(DB_NAME)
    try:
        df = pd.read_sql(f"SELECT * FROM {TABLE_NAME}", conn)
        df["Price"] = pd.to_numeric(df["Price"], errors="coerce")
        df["Rating"] = pd.to_numeric(df["Rating"], errors="coerce")
        df = df.dropna(subset=["Price"])
    except Exception:
        df = pd.DataFrame(columns=["Source", "Title", "Price", "Rating", "Link"])
    conn.close()
    return df

def fig_to_base64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)
    return b64

def clean_nans(obj):
    if isinstance(obj, dict):
        return {k: clean_nans(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_nans(i) for i in obj]
    elif isinstance(obj, float) and math.isnan(obj):
        return None
    return obj

@app.route("/api/recents", methods=["GET"])
def get_recents():
    return jsonify({"searches": session.get("searches", [])})

@app.route("/api/clear_history", methods=["POST"])
def clear_history():
    if "searches" in session:
        session["searches"] = []
        session.modified = True
    return jsonify({"status": "cleared"})

@app.route("/api/search", methods=["POST", "GET"])
def api_search():
    if request.method == "POST":
        data = request.json or {}
        query = data.get("query", "").strip()
        use_amazon = data.get("amazon", True)
        use_myntra = data.get("myntra", True)
        use_flipkart = data.get("flipkart", True)
        use_ajio = data.get("ajio", True)
        use_nykaa = data.get("nykaa", True)
        use_tatacliq = data.get("tatacliq", True)
        use_meesho = data.get("meesho", True)
        pages = data.get("pages", 1)
        headless = data.get("headless", True)
        origin = data.get("origin", None)
    else:
        query = request.args.get("q", "").strip()
        use_amazon = request.args.get("amazon", "true").lower() == "true"
        use_myntra = request.args.get("myntra", "true").lower() == "true"
        use_flipkart = request.args.get("flipkart", "true").lower() == "true"
        use_ajio = request.args.get("ajio", "true").lower() == "true"
        use_nykaa = request.args.get("nykaa", "true").lower() == "true"
        use_tatacliq = request.args.get("tatacliq", "true").lower() == "true"
        use_meesho = request.args.get("meesho", "true").lower() == "true"
        pages = 1
        headless = True
        origin = request.args.get("origin", None)

        now = datetime.datetime.utcnow()
        if query in _search_cache:
            cached_at, cached_data = _search_cache[query]
            if (now - cached_at).total_seconds() < 600:
                cached_data["from_cache"] = True
                return jsonify(cached_data)

    if not query:
        return jsonify({"error": "Missing query parameter"}), 400

    # Clear stale cache entry for this query so new searches always get fresh data
    if query in _search_cache:
        del _search_cache[query]

    try:
        from fast_scraper import run_with_fallback
        results = run_with_fallback(
            query,
            use_amazon=use_amazon, use_flipkart=use_flipkart, use_myntra=use_myntra,
            use_meesho=use_meesho, use_nykaa=use_nykaa, use_tatacliq=use_tatacliq, use_ajio=use_ajio
        )
        # Update session
        if "searches" not in session:
            session["searches"] = []
        if query not in session["searches"]:
            session["searches"].append(query)
            session.modified = True

        now = datetime.datetime.utcnow()
        priced = [r for r in results if r.get("price")]
        response = {
            "query": query,
            "count": len(results),
            "results": results,
            "cheapest": priced[0] if priced else None,
            "status": "success"
        }
        _search_cache[query] = (now, response)
        
        # We also trigger the backend cache/DB update if POST (for products view)
        if request.method == "POST":
            get_cached_or_scrape(query, use_amazon, use_myntra, use_flipkart, use_ajio, use_nykaa, use_tatacliq, use_meesho, pages, headless, origin=origin)

        return jsonify(response)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/products")
def api_products():
    try:
        df = load_data_from_db()
        if df.empty:
            return jsonify({"products": [], "message": "No products found. Please try a different search."})

        df = remove_outliers(df)
        df = calculate_value_score(df)
        top_recommendations = get_top_recommendations(df)
        df = add_better_alternatives(df)
        df = add_similar_products(df)
        df = add_sentiment_scores(df)

        if "ValueScore" in df.columns:
            df = df.sort_values(by="ValueScore", ascending=False)

        cheapest = df.nsmallest(5, "Price").to_dict(orient="records")
        expensive = df.nlargest(5, "Price").to_dict(orient="records")
        products_dict = df.to_dict(orient="records")

        return jsonify(clean_nans({
            "products": products_dict,
            "cheapest": cheapest,
            "expensive": expensive,
            "top_recs": top_recommendations
        }))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/download_csv")
def download_csv():
    df = load_data_from_db()
    file_path = os.path.join(os.getcwd(), "scraped_data.csv")
    df.to_csv(file_path, index=False, encoding="utf-8-sig")
    return send_file(file_path, as_attachment=True)

@app.route("/api/visuals")
def api_visuals():
    df = load_data_from_db()
    if df.empty:
        return jsonify({"plots": {}, "message": "No data available."})

    plots = {}
    try:
        fig, ax = plt.subplots(figsize=(10,5))
        sns.histplot(data=df, x="Price", hue="Source", bins=30, kde=True, element="step", ax=ax)
        plots["price_dist"] = fig_to_base64(fig)

        fig, ax = plt.subplots(figsize=(8,5))
        sns.boxplot(x="Source", y="Price", data=df, ax=ax)
        plots["boxplot"] = fig_to_base64(fig)

        avg_price = df.groupby("Source")["Price"].mean()
        fig, ax = plt.subplots(figsize=(6,4))
        avg_price.plot(kind="bar", color=["#FF9900","#E91E63"], ax=ax)
        plots["avg_price"] = fig_to_base64(fig)

        amazon_only = df[df["Source"] == "Amazon"].dropna(subset=["Rating"])
        if not amazon_only.empty:
            fig, ax = plt.subplots(figsize=(6,4))
            sns.histplot(amazon_only, x="Rating", bins=10, kde=True, ax=ax, color="#FF9900")
            plots["amazon_ratings"] = fig_to_base64(fig)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"plots": plots})

@app.route("/api/history")
def api_history():
    title = request.args.get("title")
    if not title: 
        return jsonify({"error": "Missing title"}), 400
    
    conn = sqlite3.connect(DB_NAME)
    try:
        df = pd.read_sql("SELECT Source, Price, Timestamp FROM price_history WHERE Title = ?", conn, params=(title,))
    except Exception as e:
        df = pd.DataFrame()

    if df.empty: 
        try:
            # Fallback to current snapshot in 'products' table if history missing
            df = pd.read_sql("SELECT Source, Price FROM products WHERE Title = ?", conn, params=(title,))
            if not df.empty:
                import datetime
                df["Timestamp"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            pass
    conn.close()

    if df.empty: 
        return jsonify({"data": []}), 200
    
    return jsonify(clean_nans({"data": df.to_dict(orient="records")})), 200

@app.route("/api/compare")
def api_compare():
    link = request.args.get("link")
    if not link:
        return jsonify({"error": "No link provided"}), 400
        
    df_raw = load_data_from_db()
    if df_raw.empty:
        return jsonify({"error": "No data available in DB"}), 404
        
    target_item = df_raw[df_raw["Link"] == link]
    if target_item.empty:
        return jsonify({"error": "Item not found"}), 404
        
    target_row = target_item.iloc[0]
    from components.recommendation_engine import get_similar_products_knn
    similar = get_similar_products_knn(df_raw, target_row, n_neighbors=2)
    
    return jsonify(clean_nans({"items": [target_row.to_dict()] + similar}))

@app.route("/api/alert", methods=["POST"])
def alert():
    data = request.json or {}
    email = data.get("email")
    link = data.get("link")
    target_price = data.get("target_price")
    title = data.get("title")
    if email and link:
        add_user_alert(email, link, target_price, title)
        return jsonify({"status": "success", "message": f"Alert set for {email}!"})
    return jsonify({"error": "Invalid data"}), 400

@app.route("/api/status")
def api_status():
    return jsonify({"status": "ok", "version": "REACT_API_1.0"})

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_react(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
         return send_from_directory(app.static_folder, path)
    if os.path.exists(os.path.join(app.static_folder, "index.html")):
         return send_from_directory(app.static_folder, "index.html")
    return jsonify({"error": "Frontend build not found"}), 404

if __name__ == "__main__":
    app.run(debug=True, port=5000, threaded=True)