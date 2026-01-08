"""
Data Ingestion Module
Handles loading data from CSV files and APIs
"""
import pandas as pd
import yaml
import logging
import requests
from pathlib import Path

class DataIngestion:
    def __init__(self, config_path='config/config.yaml'):
        """Initialize data ingestion"""
        config_file = Path(config_path)
        with config_file.open("r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)
        
        self.data_sources = self.config['data_sources']
        logging.info("Data Ingestion initialized")
    
    def load_csv(self, filepath):
        """Load data from CSV file"""
        try:
            df = pd.read_csv(filepath)
            logging.info(f"Loaded {len(df)} rows from {filepath}")
            return df
        except FileNotFoundError:
            logging.error(f"File not found: {filepath}")
            return None
        except Exception as e:
            logging.error(f"Error loading CSV {filepath}: {str(e)}")
            return None
    
    def load_from_api(self, url, params=None, headers=None):
        """Load data from API endpoint"""
        try:
            response = requests.get(url, params=params, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            df = pd.DataFrame(data)
            logging.info(f"Loaded {len(df)} rows from API: {url}")
            return df
        except requests.RequestException as e:
            logging.error(f"Error fetching from API {url}: {str(e)}")
            return None
    
    def load_sales_data(self):
        """Load sales transaction data"""
        source = self.data_sources['sales']
        
        if source['url']:
            df = self.load_from_api(source['url'])
        else:
            df = self.load_csv(source['path'])
        
        if df is not None:
            # Standardize column names
            df.columns = df.columns.str.lower().str.replace(' ', '_')
            
            # Parse dates
            if 'order_date' in df.columns:
                df['order_date'] = pd.to_datetime(df['order_date'], errors='coerce')
            
            logging.info(f"Sales data loaded: {df.shape}")
        
        return df
    
    def load_customer_data(self):
        """Load customer data"""
        source = self.data_sources['customers']
        
        if source['url']:
            df = self.load_from_api(source['url'])
        else:
            df = self.load_csv(source['path'])
        
        if df is not None:
            df.columns = df.columns.str.lower().str.replace(' ', '_')
            
            if 'registration_date' in df.columns:
                df['registration_date'] = pd.to_datetime(df['registration_date'], errors='coerce')
            
            logging.info(f"Customer data loaded: {df.shape}")
        
        return df
    
    def load_product_data(self):
        """Load product data"""
        source = self.data_sources['products']
        
        if source['url']:
            df = self.load_from_api(source['url'])
        else:
            df = self.load_csv(source['path'])
        
        if df is not None:
            df.columns = df.columns.str.lower().str.replace(' ', '_')
            logging.info(f"Product data loaded: {df.shape}")
        
        return df
    
    def generate_sample_data(self):
        """Generate sample data for testing (if no data exists)"""
        import numpy as np
        from datetime import datetime, timedelta
        
        # Create data directories
        Path("data/raw").mkdir(parents=True, exist_ok=True)
        
        # Generate sample sales data
        n_sales = 10000
        start_date = datetime(2023, 1, 1)
        
        sales_data = {
            'transaction_id': [f'TXN{str(i).zfill(6)}' for i in range(1, n_sales + 1)],
            'order_date': [start_date + timedelta(days=np.random.randint(0, 730)) for _ in range(n_sales)],
            'customer_id': [f'CUST{str(np.random.randint(1, 1001)).zfill(4)}' for _ in range(n_sales)],
            'product_id': [f'PROD{str(np.random.randint(1, 201)).zfill(3)}' for _ in range(n_sales)],
            'quantity': np.random.randint(1, 10, n_sales),
            'unit_price': np.random.uniform(10, 500, n_sales).round(2),
            'discount': np.random.choice([0, 0.05, 0.10, 0.15, 0.20], n_sales),
            'shipping_cost': np.random.uniform(5, 50, n_sales).round(2)
        }
        
        df_sales = pd.DataFrame(sales_data)
        df_sales.to_csv('data/raw/sales_data.csv', index=False)
        
        # Generate sample customer data
        n_customers = 1000
        
        customer_data = {
            'customer_id': [f'CUST{str(i).zfill(4)}' for i in range(1, n_customers + 1)],
            'customer_name': [f'Customer {i}' for i in range(1, n_customers + 1)],
            'email': [f'customer{i}@example.com' for i in range(1, n_customers + 1)],
            'segment': np.random.choice(['Consumer', 'Corporate', 'Home Office'], n_customers),
            'country': np.random.choice(['USA', 'Canada', 'UK', 'Germany', 'France'], n_customers),
            'state': np.random.choice(['CA', 'NY', 'TX', 'FL', 'IL', 'PA'], n_customers),
            'city': [f'City{i}' for i in range(1, n_customers + 1)],
            'registration_date': [start_date + timedelta(days=np.random.randint(0, 365)) for _ in range(n_customers)]
        }
        
        df_customers = pd.DataFrame(customer_data)
        df_customers.to_csv('data/raw/customer_data.csv', index=False)
        
        # Generate sample product data
        n_products = 200
        
        categories = ['Technology', 'Furniture', 'Office Supplies']
        sub_categories = {
            'Technology': ['Phones', 'Computers', 'Accessories'],
            'Furniture': ['Chairs', 'Tables', 'Bookcases'],
            'Office Supplies': ['Paper', 'Binders', 'Pens']
        }
        
        product_data = {
            'product_id': [f'PROD{str(i).zfill(3)}' for i in range(1, n_products + 1)],
            'product_name': [f'Product {i}' for i in range(1, n_products + 1)],
            'category': [np.random.choice(categories) for _ in range(n_products)],
        }
        
        product_data['sub_category'] = [
            np.random.choice(sub_categories[cat]) for cat in product_data['category']
        ]
        
        product_data['unit_cost'] = np.random.uniform(5, 300, n_products).round(2)
        product_data['unit_price'] = (product_data['unit_cost'] * np.random.uniform(1.2, 2.5, n_products)).round(2)
        
        df_products = pd.DataFrame(product_data)
        df_products.to_csv('data/raw/product_data.csv', index=False)
        
        logging.info("Sample data generated successfully")
        print("✅ Sample data files created in data/raw/")