"""
Main Pipeline Orchestrator
Runs the complete data pipeline: Ingestion -> Quality Checks -> KPI Calculation -> Database Load
"""
import logging
import yaml
from datetime import datetime
from pathlib import Path
import sys

# Import custom modules
from database import DatabaseManager
from ingestion import DataIngestion
from data_quality import DataQualityChecker
from kpi_calculator import KPICalculator

class SafeStreamHandler(logging.StreamHandler):
    """StreamHandler that safely handles encoding errors on Windows"""
    def emit(self, record):
        try:
            msg = self.format(record)
            stream = self.stream
            # Handle encoding errors gracefully
            try:
                stream.write(msg + self.terminator)
            except UnicodeEncodeError:
                # For Windows console, replace problematic Unicode characters
                # Get the stream encoding (usually cp1252 on Windows)
                encoding = getattr(stream, 'encoding', 'utf-8') or 'utf-8'
                # Encode with error replacement, then decode back
                msg_bytes = msg.encode(encoding, errors='replace')
                msg_safe = msg_bytes.decode(encoding, errors='replace')
                stream.write(msg_safe + self.terminator)
            self.flush()
        except Exception:
            self.handleError(record)

class DataPipeline:
    def __init__(self, config_path='config/config.yaml'):
        """Initialize the data pipeline"""
        # Setup logging
        self._setup_logging()
        
        logging.info("="*60)
        logging.info("BUSINESS KPI DASHBOARD PIPELINE - STARTED")
        logging.info("="*60)
        config_file = Path(config_path)

        # Load configuration
        with open(config_path, 'r', encoding="utf-8") as f:
            self.config = yaml.safe_load(f)
        
        
        # Initialize components
        self.db_manager = DatabaseManager(config_path)
        self.data_ingestion = DataIngestion(config_path)
        self.quality_checker = DataQualityChecker(config_path, self.db_manager)
        self.kpi_calculator = KPICalculator(config_path, self.db_manager)
        
        self.current_date_key = self.db_manager.get_date_key(datetime.now())
    
    def _setup_logging(self):
        """Configure logging"""
        Path("data/logs").mkdir(parents=True, exist_ok=True)
        
        # Create file handler with UTF-8 encoding
        file_handler = logging.FileHandler('data/logs/pipeline.log', encoding='utf-8')
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        
        # Create safe console handler that handles encoding errors
        console_handler = SafeStreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        
        logging.basicConfig(
            level=logging.INFO,
            handlers=[file_handler, console_handler]
        )
    
    def initialize_database(self):
        """Initialize database schema"""
        logging.info("Initializing database schema...")
        
        try:
            # Execute schema SQL
            self.db_manager.execute_sql_file('sql/schema.sql')
            
            # Populate date dimension
            self.db_manager.populate_date_dimension()
            
            logging.info("✅ Database initialized successfully")
            return True
            
        except Exception as e:
            logging.error(f"❌ Database initialization failed: {str(e)}")
            return False
    
    def ingest_data(self):
        """Ingest data from sources"""
        logging.info("Starting data ingestion...")
        
        # Load sales data
        df_sales = self.data_ingestion.load_sales_data()
        if df_sales is None:
            logging.error("❌ Failed to load sales data")
            return None, None, None
        
        # Load customer data
        df_customers = self.data_ingestion.load_customer_data()
        if df_customers is None:
            logging.error("❌ Failed to load customer data")
            return None, None, None
        
        # Load product data
        df_products = self.data_ingestion.load_product_data()
        if df_products is None:
            logging.error("❌ Failed to load product data")
            return None, None, None
        
        logging.info("✅ Data ingestion completed")
        return df_sales, df_customers, df_products
    
    def run_quality_checks(self, df_sales, df_customers, df_products):
        """Run data quality checks"""
        logging.info("Running data quality checks...")
        
        # Check sales data
        checks_sales, score_sales, status_sales = self.quality_checker.run_quality_checks(
            df_sales, 'sales', key_columns=['transaction_id']
        )
        
        # Check customer data
        checks_customers, score_customers, status_customers = self.quality_checker.run_quality_checks(
            df_customers, 'customers', key_columns=['customer_id']
        )
        
        # Check product data
        checks_products, score_products, status_products = self.quality_checker.run_quality_checks(
            df_products, 'products', key_columns=['product_id']
        )
        
        # Save quality metrics to database
        self.quality_checker.save_quality_metrics_to_db('sales', self.current_date_key)
        self.quality_checker.save_quality_metrics_to_db('customers', self.current_date_key)
        self.quality_checker.save_quality_metrics_to_db('products', self.current_date_key)
        
        # Print summary
        print("\n" + "="*60)
        print("DATA QUALITY SUMMARY")
        print("="*60)
        print(f"Sales Data      - Score: {score_sales:.2f} | Status: {status_sales}")
        print(f"Customer Data   - Score: {score_customers:.2f} | Status: {status_customers}")
        print(f"Product Data    - Score: {score_products:.2f} | Status: {status_products}")
        print("="*60)
        
        logging.info("✅ Data quality checks completed")
        
        # Return cleaned data (remove duplicates, handle missing values)
        df_sales_clean = self._clean_data(df_sales, 'transaction_id')
        df_customers_clean = self._clean_data(df_customers, 'customer_id')
        df_products_clean = self._clean_data(df_products, 'product_id')
        
        return df_sales_clean, df_customers_clean, df_products_clean
    
    def _clean_data(self, df, id_column):
        """Basic data cleaning"""
        # Remove duplicates
        df_clean = df.drop_duplicates(subset=[id_column])
        
        # Fill missing numeric values with 0
        numeric_cols = df_clean.select_dtypes(include=['float64', 'int64']).columns
        df_clean[numeric_cols] = df_clean[numeric_cols].fillna(0)
        
        # Fill missing categorical values with 'Unknown'
        categorical_cols = df_clean.select_dtypes(include=['object']).columns
        df_clean[categorical_cols] = df_clean[categorical_cols].fillna('Unknown')
        
        return df_clean
    
    def load_to_warehouse(self, df_sales, df_customers, df_products):
        """Load cleaned data to data warehouse"""
        logging.info("Loading data to warehouse...")
        
        # Load dimension tables
        self._load_customers(df_customers)
        self._load_products(df_products)
        
        # Load fact table
        self._load_sales(df_sales)
        
        logging.info("✅ Data loaded to warehouse")
    
    def _load_customers(self, df):
        """Load customer dimension"""
        df_dim = df[['customer_id', 'customer_name', 'email', 'segment', 
                     'country', 'state', 'city', 'registration_date']].copy()
        df_dim['is_active'] = True
        
        # Upsert to database
        self.db_manager.upsert_dimension(df_dim, 'dim_customers', 'customer_id', 'customer_key')
    
    def _load_products(self, df):
        """Load product dimension"""
        df_dim = df[['product_id', 'product_name', 'category', 'sub_category', 
                     'unit_cost', 'unit_price']].copy()
        df_dim['is_active'] = True
        
        # Upsert to database
        self.db_manager.upsert_dimension(df_dim, 'dim_products', 'product_id', 'product_key')
    
    def _load_sales(self, df):
        """Load sales fact table"""
        # Get customer and product keys
        customers = self.db_manager.query_to_dataframe(
            "SELECT customer_key, customer_id FROM dim_customers"
        )
        products = self.db_manager.query_to_dataframe(
            "SELECT product_key, product_id FROM dim_products"
        )
        
        # Merge keys
        df_fact = df.merge(customers, on='customer_id', how='left')
        df_fact = df_fact.merge(products, on='product_id', how='left')
        
        # Add date key
        df_fact['date_key'] = df_fact['order_date'].apply(
            lambda x: self.db_manager.get_date_key(x)
        )
        
        # Calculate metrics
        df_fact['revenue'] = df_fact['quantity'] * df_fact['unit_price'] * (1 - df_fact['discount'])
        df_fact['cost'] = df_fact['quantity'] * df_fact['unit_price'] * 0.6  # Simplified
        df_fact['profit'] = df_fact['revenue'] - df_fact['cost']
        
        # Select columns for fact table
        df_fact = df_fact[[
            'transaction_id', 'date_key', 'customer_key', 'product_key',
            'quantity', 'unit_price', 'discount', 'shipping_cost',
            'revenue', 'cost', 'profit'
        ]]
        
        # Load to database
        self.db_manager.load_to_table(df_fact, 'fact_sales', if_exists='append')
    
    def calculate_kpis(self, df_sales, df_customers, df_products):
        """Calculate and save KPIs"""
        logging.info("Calculating KPIs...")
        
        # Calculate all KPIs
        kpis = self.kpi_calculator.calculate_all_kpis(df_sales, df_customers, df_products)
        
        # Save to database
        self.kpi_calculator.save_kpis_to_db(self.current_date_key)
        
        # Print summary
        self.kpi_calculator.print_kpi_summary()
        
        logging.info("✅ KPIs calculated and saved")
    
    def run_pipeline(self, initialize_db=False):
        """Run the complete pipeline"""
        try:
            # Initialize database if requested
            if initialize_db:
                if not self.initialize_database():
                    return False
            
            # Step 1: Ingest data
            df_sales, df_customers, df_products = self.ingest_data()
            if df_sales is None:
                return False
            
            # Step 2: Run quality checks
            df_sales_clean, df_customers_clean, df_products_clean = self.run_quality_checks(
                df_sales, df_customers, df_products
            )
            
            # Step 3: Load to warehouse
            self.load_to_warehouse(df_sales_clean, df_customers_clean, df_products_clean)
            
            # Step 4: Calculate KPIs
            self.calculate_kpis(df_sales_clean, df_customers_clean, df_products_clean)
            
            logging.info("="*60)
            logging.info("✅ PIPELINE COMPLETED SUCCESSFULLY")
            logging.info("="*60)
            
            return True
            
        except Exception as e:
            logging.error(f"❌ Pipeline failed: {str(e)}", exc_info=True)
            return False
        
        finally:
            # Close database connection
            self.db_manager.close()

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Business KPI Dashboard Pipeline')
    parser.add_argument('--init-db', action='store_true', help='Initialize database schema')
    parser.add_argument('--generate-data', action='store_true', help='Generate sample data')
    
    args = parser.parse_args()
    
    # Generate sample data if requested
    if args.generate_data:
        ingestion = DataIngestion()
        ingestion.generate_sample_data()
        print("✅ Sample data generated. Now run: python main.py --init-db")
        return
    
    # Run pipeline
    pipeline = DataPipeline()
    success = pipeline.run_pipeline(initialize_db=args.init_db)
    
    if success:
        print("\n🎉 Pipeline completed successfully!")
        print("\nNext steps:")
        print("1. Connect Power BI to your database")
        print("2. Use the views: vw_sales_summary, vw_kpi_dashboard, vw_data_quality_dashboard")
        print("3. Schedule this script to run automatically")
    else:
        print("\n❌ Pipeline failed. Check logs for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()