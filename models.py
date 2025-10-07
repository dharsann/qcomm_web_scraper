# backend/models.py
from dataclasses import dataclass
from typing import List, Optional
import pandas as pd
from fuzzywuzzy import fuzz
import re

@dataclass
class Product:
    """Product data model"""
    name: str
    brand: str
    weight: str
    weight_clean: str
    price: str
    price_numeric: float
    image: str
    platform: str
    
    def to_dict(self):
        return {
            'name': self.name,
            'brand': self.brand,
            'weight': self.weight,
            'weight_clean': self.weight_clean,
            'price': self.price,
            'price_numeric': self.price_numeric,
            'image': self.image,
            'platform': self.platform
        }


@dataclass
class ProductMatch:
    """Matched product across platforms"""
    product_name: str
    brand: str
    weight: str
    platform1: str
    price1: float
    platform2: str
    price2: float
    price_diff: float
    price_diff_pct: float
    similarity: float
    cheaper_platform: str
    savings: float = 0.0
    
    def to_dict(self):
        return {
            'product_name': self.product_name,
            'brand': self.brand,
            'weight': self.weight,
            'platform1': self.platform1,
            'price1': self.price1,
            'platform2': self.platform2,
            'price2': self.price2,
            'price_diff': self.price_diff,
            'price_diff_pct': self.price_diff_pct,
            'similarity': self.similarity,
            'cheaper_platform': self.cheaper_platform,
            'savings': self.savings
        }


class ProductMatcher:
    """Match identical products across platforms"""
    
    @staticmethod
    def normalize_name(name: str) -> str:
        """Normalize product name for matching"""
        name = name.lower()
        name = re.sub(r'[^\w\s]', '', name)
        name = re.sub(r'\s+', ' ', name)
        return name.strip()
    
    @staticmethod
    def calculate_similarity(name1: str, name2: str, weight1: str, weight2: str) -> float:
        """Calculate similarity score between two products"""
        # Name similarity
        name_sim = fuzz.token_sort_ratio(
            ProductMatcher.normalize_name(name1),
            ProductMatcher.normalize_name(name2)
        )
        
        # Weight similarity bonus
        weight_bonus = 20 if weight1 and weight2 and weight1 == weight2 else 0
        
        return min(100, name_sim + weight_bonus)
    
    @staticmethod
    def match_products(df: pd.DataFrame, threshold: float = 75) -> List[ProductMatch]:
        """Find matching products across platforms"""
        matches = []
        platforms = df['platform'].unique()
        
        if len(platforms) < 2:
            return matches
        
        for platform1 in platforms:
            df1 = df[df['platform'] == platform1]
            
            for platform2 in platforms:
                if platform1 >= platform2:
                    continue
                    
                df2 = df[df['platform'] == platform2]
                
                for idx1, row1 in df1.iterrows():
                    for idx2, row2 in df2.iterrows():
                        similarity = ProductMatcher.calculate_similarity(
                            row1['name'], row2['name'],
                            row1['weight_clean'], row2['weight_clean']
                        )
                        
                        if similarity >= threshold:
                            price_diff = abs(row1['price_numeric'] - row2['price_numeric'])
                            max_price = max(row1['price_numeric'], row2['price_numeric'])
                            price_diff_pct = (price_diff / max_price * 100) if max_price > 0 else 0
                            
                            cheaper = platform1 if row1['price_numeric'] < row2['price_numeric'] else platform2
                            savings = price_diff
                            
                            match = ProductMatch(
                                product_name=row1['name'],
                                brand=row1['brand'],
                                weight=row1['weight_clean'],
                                platform1=platform1,
                                price1=row1['price_numeric'],
                                platform2=platform2,
                                price2=row2['price_numeric'],
                                price_diff=price_diff,
                                price_diff_pct=price_diff_pct,
                                similarity=similarity,
                                cheaper_platform=cheaper,
                                savings=savings
                            )
                            matches.append(match)
        
        return matches
    
    @staticmethod
    def get_best_deals(matches: List[ProductMatch], top_n: int = 10) -> List[ProductMatch]:
        """Get top deals by savings amount"""
        sorted_matches = sorted(matches, key=lambda x: x.savings, reverse=True)
        return sorted_matches[:top_n]
    
    @staticmethod
    def get_platform_stats(df: pd.DataFrame) -> dict:
        """Calculate platform-wise statistics"""
        stats = {}
        
        for platform in df['platform'].unique():
            platform_df = df[df['platform'] == platform]
            stats[platform] = {
                'total_products': len(platform_df),
                'avg_price': platform_df['price_numeric'].mean(),
                'min_price': platform_df['price_numeric'].min(),
                'max_price': platform_df['price_numeric'].max(),
                'median_price': platform_df['price_numeric'].median()
            }
        
        return stats
    
    @staticmethod
    def get_brand_analysis(df: pd.DataFrame) -> pd.DataFrame:
        """Analyze pricing by brand"""
        brand_stats = df.groupby(['brand', 'platform']).agg({
            'price_numeric': ['mean', 'count', 'min', 'max']
        }).round(2)
        
        return brand_stats