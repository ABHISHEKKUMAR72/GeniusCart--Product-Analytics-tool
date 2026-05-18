import pandas as pd
import numpy as np
from sklearn.neighbors import NearestNeighbors

def get_similar_products_knn(df, target_row, n_neighbors=3):
    """
    Uses KNN to find similar products based on Price and Rating.
    """
    # Create feature matrix
    features_df = df[['Price', 'Rating']].copy()
    
    # Ensure KNN operates on valid numbers (replace NaNs with 0)
    features_df['Price'] = pd.to_numeric(features_df['Price'], errors='coerce').fillna(0)
    features_df['Rating'] = pd.to_numeric(features_df['Rating'], errors='coerce').fillna(0)
    
    max_price = features_df['Price'].max() if features_df['Price'].max() > 0 else 1
    features_df['Price_Scaled'] = features_df['Price'] / max_price
    features_df['Rating_Scaled'] = features_df['Rating'] / 5.0
    
    X = features_df[['Price_Scaled', 'Rating_Scaled']].values
    
    target_price_scaled = target_row['Price'] / max_price if max_price > 0 else 0
    target_rating_scaled = target_row['Rating'] / 5.0
    target_x = [[target_price_scaled, target_rating_scaled]]
    
    n = min(n_neighbors + 1, len(X))
    if n < 2:
        return []
        
    model = NearestNeighbors(n_neighbors=n)
    model.fit(X)
    
    distances, indices = model.kneighbors(target_x)
    
    similar_products = []
    for idx in indices[0]:
        sim_row = df.iloc[idx]
        if sim_row['Title'] != target_row['Title']:
            similar_products.append(sim_row.to_dict())
            
    return similar_products[:n_neighbors]


def add_better_alternatives(df):
    """
    Applies the rule-based "Better Alternative" logic to every product in the DataFrame.
    Returns the dataframe with a 'BetterAlternative' column containing dictionaries.
    """
    if df is None or df.empty:
        return df
        
    df = df.copy()
    df['Price'] = pd.to_numeric(df['Price'], errors='coerce')
    df['NumericRating'] = pd.to_numeric(df['Rating'], errors='coerce').fillna(0.0)
    
    alternatives = []
    valid_df = df.dropna(subset=['Price'])
    
    for _, row in df.iterrows():
        if pd.isna(row['Price']):
            alternatives.append(None)
            continue
            
        target_price = row['Price']
        target_rating = row['NumericRating']
        
        better_mask = (
            (valid_df['Price'] < target_price - 50) & 
            (valid_df['NumericRating'] >= target_rating) &
            (valid_df['Title'] != row['Title'])
        )
        better_options = valid_df[better_mask]
        
        if not better_options.empty:
            best_alt = better_options.sort_values(by=['Price', 'NumericRating'], ascending=[True, False]).iloc[0]
            savings = target_price - best_alt['Price']
            
            alternatives.append({
                "title": best_alt['Title'],
                "price": best_alt['Price'],
                "rating": best_alt['Rating'],
                "source": best_alt['Source'],
                "link": best_alt['Link'],
                "savings": int(savings)
            })
        else:
            alternatives.append(None)
            
    df['BetterAlternative'] = alternatives
    df = df.drop(columns=['NumericRating'])
    return df

def get_top_recommendations(df):
    """
    Generate 3 "Top Smart Recommendations" for the dashboard.
    Uses multi-parameter scoring:
      - Price competitiveness (lower = better)
      - Rating quality (higher = better)
      - Source reliability weighting (platforms with more listed products are weighted)
      - Value efficiency (rating-to-price ratio)
    """
    if df is None or df.empty:
        return []
        
    df = df.copy()
    df['Price'] = pd.to_numeric(df['Price'], errors='coerce')
    df['NumericRating'] = pd.to_numeric(df['Rating'], errors='coerce').fillna(0.0)
    valid_df = df.dropna(subset=['Price'])
    
    if len(valid_df) < 1:
        return []

    # ── Source reliability: platforms with more products listed get a small boost ──
    source_counts = valid_df['Source'].value_counts()
    max_source_count = source_counts.max() if not source_counts.empty else 1
    valid_df = valid_df.copy()
    valid_df['SourceReliability'] = valid_df['Source'].map(
        lambda s: source_counts.get(s, 0) / max_source_count
    )

    # ── Price competitiveness: normalize price to 0-1 (lower is better) ──
    min_price = valid_df['Price'].min()
    max_price = valid_df['Price'].max()
    price_range = max_price - min_price if max_price > min_price else 1
    valid_df['PriceScore'] = 1 - ((valid_df['Price'] - min_price) / price_range)

    # ── Rating quality: normalize to 0-1 ──
    valid_df['RatingScore'] = valid_df['NumericRating'] / 5.0

    # ── Value efficiency: rating per ₹1000 spent ──
    valid_df['ValueEfficiency'] = np.where(
        valid_df['Price'] > 0,
        (valid_df['NumericRating'] / (valid_df['Price'] / 1000)),
        0
    )
    max_ve = valid_df['ValueEfficiency'].max()
    valid_df['ValueEfficiencyNorm'] = valid_df['ValueEfficiency'] / max_ve if max_ve > 0 else 0

    # ── Composite score (weighted sum) ──
    valid_df['RecommendationScore'] = (
        0.30 * valid_df['PriceScore'] +
        0.30 * valid_df['RatingScore'] +
        0.25 * valid_df['ValueEfficiencyNorm'] +
        0.15 * valid_df['SourceReliability']
    )

    top_picks = valid_df.sort_values(by='RecommendationScore', ascending=False).head(3)

    recs = []
    for _, pick in top_picks.iterrows():
        rec = pick.to_dict()
        # Clean up helper columns
        for col in ['SourceReliability', 'PriceScore', 'RatingScore',
                     'ValueEfficiency', 'ValueEfficiencyNorm', 'RecommendationScore', 'NumericRating']:
            rec.pop(col, None)
        recs.append(rec)
        
    return recs

def add_similar_products(df):
    """
    Adds a 'SimilarProducts' column to the DataFrame that contains
    up to 3 similar products based on KNN, utilizing get_similar_products_knn.
    """
    if df is None or df.empty:
        return df
        
    df = df.copy()
    similar_list = []
    
    # Needs valid records for KNN
    valid_df = df.dropna(subset=['Price'])
    if len(valid_df) < 2:
        df['SimilarProducts'] = [[] for _ in range(len(df))]
        return df
        
    for _, row in df.iterrows():
        try:
            # We pass the full clean valid_df to give enough neighbors
            similar = get_similar_products_knn(valid_df, row, n_neighbors=3)
            similar_list.append(similar)
        except Exception:
            similar_list.append([])
            
    df['SimilarProducts'] = similar_list
    return df


# import pandas as pd
# import numpy as np

# def get_similar_products_knn(df, target_row, n_neighbors=3):
#     """Find similar products using price and rating"""
#     try:
#         # Ensure numeric values
#         df_valid = df.copy()
#         df_valid['Price'] = pd.to_numeric(df_valid['Price'], errors='coerce')
#         df_valid['Rating'] = pd.to_numeric(df_valid['Rating'], errors='coerce').fillna(0)
        
#         # Remove rows with NaN prices
#         df_valid = df_valid.dropna(subset=['Price'])
        
#         if len(df_valid) < 2:
#             return []
        
#         # Calculate price similarity
#         target_price = target_row['Price']
#         target_rating = target_row.get('Rating', 0)
#         if pd.isna(target_rating):
#             target_rating = 0
        
#         # Find similar products by price range (±30%)
#         price_range = target_price * 0.3
#         similar_mask = (df_valid['Price'] >= target_price - price_range) & \
#                        (df_valid['Price'] <= target_price + price_range) & \
#                        (df_valid['Title'] != target_row['Title'])
        
#         similar_products = df_valid[similar_mask].head(n_neighbors)
        
#         results = []
#         for _, row in similar_products.iterrows():
#             results.append(row.to_dict())
        
#         return results
#     except Exception as e:
#         print(f"KNN Error: {e}")
#         return []

# def add_better_alternatives(df):
#     """Find better alternatives (cheaper with similar rating)"""
#     if df is None or df.empty:
#         return df
    
#     df = df.copy()
#     df['Price'] = pd.to_numeric(df['Price'], errors='coerce')
#     df['Rating'] = pd.to_numeric(df['Rating'], errors='coerce').fillna(0)
#     df = df.dropna(subset=['Price'])
    
#     alternatives = []
    
#     for _, row in df.iterrows():
#         target_price = row['Price']
#         target_rating = row['Rating']
        
#         # Find cheaper products with similar or better rating
#         better_mask = (df['Price'] < target_price) & \
#                      (df['Rating'] >= target_rating - 0.5) & \
#                      (df['Title'] != row['Title'])
        
#         better_options = df[better_mask]
        
#         if not better_options.empty:
#             best = better_options.nsmallest(1, 'Price').iloc[0]
#             savings = target_price - best['Price']
            
#             alternatives.append({
#                 "title": best['Title'],
#                 "price": best['Price'],
#                 "rating": best['Rating'],
#                 "source": best['Source'],
#                 "link": best['Link'],
#                 "savings": int(savings)
#             })
#         else:
#             alternatives.append(None)
    
#     df['BetterAlternative'] = alternatives
#     return df

# def get_top_recommendations(df):
#     """Get top 3 recommendations"""
#     if df is None or df.empty:
#         return []
    
#     df = df.copy()
#     df['Price'] = pd.to_numeric(df['Price'], errors='coerce')
#     df['Rating'] = pd.to_numeric(df['Rating'], errors='coerce').fillna(0)
#     df = df.dropna(subset=['Price'])
    
#     # Calculate value score (higher rating / lower price)
#     df['ValueScore'] = (df['Rating'] / (df['Price'] / 1000)) * 10
    
#     # Sort by value score and get top 3
#     top_picks = df.nlargest(3, 'ValueScore')
    
#     return top_picks.to_dict(orient='records')

# def add_similar_products(df):
#     """Add similar products column"""
#     if df is None or df.empty:
#         return df
    
#     df = df.copy()
#     similar_list = []
    
#     for _, row in df.iterrows():
#         similar = get_similar_products_knn(df, row, n_neighbors=3)
#         similar_list.append(similar)
    
#     df['SimilarProducts'] = similar_list
#     return df

# components/recommendation_engine.py
# import pandas as pd
# import numpy as np

# def get_similar_products_knn(df, target_row, n_neighbors=3):
#     """Find similar products using price and rating"""
#     try:
#         df_valid = df.copy()
#         df_valid['Price'] = pd.to_numeric(df_valid['Price'], errors='coerce')
#         df_valid['Rating'] = pd.to_numeric(df_valid['Rating'], errors='coerce').fillna(0)
#         df_valid = df_valid.dropna(subset=['Price'])
        
#         if len(df_valid) < 2:
#             return []
        
#         target_price = target_row['Price']
#         target_rating = target_row.get('Rating', 0)
#         if pd.isna(target_rating):
#             target_rating = 0
        
#         price_range = target_price * 0.3
#         similar_mask = (df_valid['Price'] >= target_price - price_range) & \
#                        (df_valid['Price'] <= target_price + price_range) & \
#                        (df_valid['Title'] != target_row['Title'])
        
#         similar_products = df_valid[similar_mask].head(n_neighbors)
        
#         results = []
#         for _, row in similar_products.iterrows():
#             results.append(row.to_dict())
        
#         return results
#     except Exception as e:
#         print(f"KNN Error: {e}")
#         return []

# def add_better_alternatives(df):
#     """Find better alternatives (cheaper with similar rating)"""
#     if df is None or df.empty:
#         return df
    
#     df = df.copy()
#     df['Price'] = pd.to_numeric(df['Price'], errors='coerce')
#     df['Rating'] = pd.to_numeric(df['Rating'], errors='coerce').fillna(0)
#     df = df.dropna(subset=['Price'])
    
#     alternatives = []
    
#     for _, row in df.iterrows():
#         target_price = row['Price']
#         target_rating = row['Rating']
        
#         better_mask = (df['Price'] < target_price) & \
#                      (df['Rating'] >= target_rating - 0.5) & \
#                      (df['Title'] != row['Title'])
        
#         better_options = df[better_mask]
        
#         if not better_options.empty:
#             best = better_options.nsmallest(1, 'Price').iloc[0]
#             savings = target_price - best['Price']
            
#             alternatives.append({
#                 "title": best['Title'],
#                 "price": best['Price'],
#                 "rating": best['Rating'],
#                 "source": best['Source'],
#                 "link": best['Link'],
#                 "savings": int(savings)
#             })
#         else:
#             alternatives.append(None)
    
#     df['BetterAlternative'] = alternatives
#     return df

# def get_top_recommendations(df):
#     """Get top 3 recommendations"""
#     if df is None or df.empty:
#         return []
    
#     df = df.copy()
#     df['Price'] = pd.to_numeric(df['Price'], errors='coerce')
#     df['Rating'] = pd.to_numeric(df['Rating'], errors='coerce').fillna(0)
#     df = df.dropna(subset=['Price'])
    
#     # Calculate value score
#     df['ValueScore'] = (df['Rating'] / (df['Price'] / 1000)) * 10
#     df['ValueScore'] = df['ValueScore'].fillna(0)
    
#     top_picks = df.nlargest(3, 'ValueScore')
    
#     return top_picks.to_dict(orient='records')

# def add_similar_products(df):
#     """Add similar products column"""
#     if df is None or df.empty:
#         return df
    
#     df = df.copy()
#     similar_list = []
    
#     for _, row in df.iterrows():
#         similar = get_similar_products_knn(df, row, n_neighbors=3)
#         similar_list.append(similar)
    
#     df['SimilarProducts'] = similar_list
#     return df