# backend/utils.py
import json
import pandas as pd
from datetime import datetime
from typing import List, Dict
import gspread
from oauth2client.service_account import ServiceAccountCredentials

class DataExporter:
    """Export data to various formats"""
    
    @staticmethod
    def save_to_json(data: dict, filename: str = None):
        """Save data to JSON file"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'bread_data_{timestamp}.json'
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f'💾 Data saved to {filename}')
        return filename
    
    @staticmethod
    def save_to_csv(df: pd.DataFrame, filename: str = None):
        """Save DataFrame to CSV"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'bread_data_{timestamp}.csv'
        
        df.to_csv(filename, index=False, encoding='utf-8')
        print(f'💾 Data saved to {filename}')
        return filename
    
    @staticmethod
    def save_to_excel(data_dict: Dict[str, pd.DataFrame], filename: str = None):
        """Save multiple DataFrames to Excel with different sheets"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'bread_analysis_{timestamp}.xlsx'
        
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            for sheet_name, df in data_dict.items():
                df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        print(f'💾 Excel saved to {filename}')
        return filename
    
    @staticmethod
    def export_to_google_sheets(data_dict: Dict[str, pd.DataFrame], 
                                sheet_name: str = 'Bread Price Comparison',
                                credentials_file: str = 'backend/credentials.json'):
        """
        Export data to Google Sheets
        
        Prerequisites:
        1. Create a Google Cloud Project
        2. Enable Google Sheets API
        3. Create Service Account and download credentials.json
        4. Share your Google Sheet with the service account email
        """
        try:
            scope = ['https://www.googleapis.com/auth/spreadsheets']
            
            creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_file, scope)
            client = gspread.authorize(creds)
            
            # Create or open spreadsheet
            try:
                spreadsheet = client.open(sheet_name)
            except:
                spreadsheet = client.create(sheet_name)
                print(f"📊 Created new Google Sheet: {sheet_name}")
            
            # Clear existing data and add new sheets
            for sheet_title, df in data_dict.items():
                try:
                    worksheet = spreadsheet.worksheet(sheet_title)
                    worksheet.clear()
                except:
                    worksheet = spreadsheet.add_worksheet(title=sheet_title, rows=1000, cols=20)
                
                # Convert DataFrame to list of lists
                data = [df.columns.tolist()] + df.values.tolist()
                worksheet.update('A1', data)
                
                print(f"  ✅ Updated sheet: {sheet_title}")
            
            print(f"\n🔗 Google Sheet URL: {spreadsheet.url}")
            return spreadsheet.url
            
        except Exception as e:
            print(f"❌ Error exporting to Google Sheets: {str(e)}")
            print("Make sure you have:")
            print("1. Created credentials.json from Google Cloud Console")
            print("2. Shared the sheet with your service account email")
            return None


class PriceAnalyzer:
    """Analyze pricing patterns"""
    
    @staticmethod
    def calculate_statistics(df: pd.DataFrame) -> dict:
        """Calculate overall statistics"""
        return {
            'total_products': len(df),
            'total_platforms': df['platform'].nunique(),
            'total_brands': df['brand'].nunique(),
            'avg_price': df['price_numeric'].mean(),
            'median_price': df['price_numeric'].median(),
            'min_price': df['price_numeric'].min(),
            'max_price': df['price_numeric'].max(),
            'price_std': df['price_numeric'].std()
        }
    
    @staticmethod
    def get_price_distribution(df: pd.DataFrame) -> pd.DataFrame:
        """Get price distribution across platforms"""
        return df.groupby('platform')['price_numeric'].describe().round(2)
    
    @staticmethod
    def get_brand_comparison(df: pd.DataFrame) -> pd.DataFrame:
        """Compare brands across platforms"""
        pivot = df.pivot_table(
            values='price_numeric',
            index='brand',
            columns='platform',
            aggfunc='mean'
        ).round(2)
        
        return pivot
    
    @staticmethod
    def find_cheapest_platform(df: pd.DataFrame) -> dict:
        """Find which platform is cheapest overall"""
        platform_avg = df.groupby('platform')['price_numeric'].mean().sort_values()
        
        return {
            'cheapest': platform_avg.index[0],
            'avg_price': platform_avg.values[0],
            'all_platforms': platform_avg.to_dict()
        }
    
    @staticmethod
    def get_savings_potential(matches: List) -> dict:
        """Calculate total savings potential"""
        if not matches:
            return {'total_savings': 0, 'avg_savings': 0, 'num_matches': 0}
        
        total_savings = sum(m['price_diff'] for m in matches)
        avg_savings = total_savings / len(matches)
        
        return {
            'total_savings': round(total_savings, 2),
            'avg_savings': round(avg_savings, 2),
            'num_matches': len(matches),
            'max_saving': max(m['price_diff'] for m in matches)
        }