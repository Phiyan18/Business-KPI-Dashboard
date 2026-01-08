"""
Database connection and operations handler
"""
import pandas as pd
import yaml
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import logging
from datetime import datetime

class DatabaseManager:
    def __init__(self, config_path='config/config.yaml'):
        """Initialize database connection"""
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        self.db_config = config['database']
        self.engine = self._create_engine()
        self.Session = sessionmaker(bind=self.engine)
        
        logging.info("Database connection established")
    
    def _create_engine(self):
        """Create SQLAlchemy engine based on database type"""
        db_type = self.db_config['type']
        host = self.db_config['host']
        port = self.db_config['port']
        database = self.db_config['database']
        username = self.db_config['username']
        password = self.db_config['password']
        
        if db_type == 'postgresql':
            conn_string = f"postgresql://{username}:{password}@{host}:{port}/{database}"
        elif db_type == 'mssql':
            conn_string = f"mssql+pyodbc://{username}:{password}@{host}:{port}/{database}?driver=ODBC+Driver+17+for+SQL+Server"
        else:
            raise ValueError(f"Unsupported database type: {db_type}")
        
        return create_engine(conn_string)
    
    def execute_sql_file(self, filepath):
        """Execute SQL file (e.g., schema creation)"""
        with open(filepath, 'r') as f:
            sql = f.read()
        
        with self.engine.connect() as conn:
            # Split and execute each statement
            statements = sql.split(';')
            for statement in statements:
                if statement.strip():
                    conn.execute(text(statement))
                    conn.commit()
        
        logging.info(f"Executed SQL file: {filepath}")
    
    def load_to_table(self, df, table_name, if_exists='append'):
        """Load DataFrame to database table"""
        try:
            df.to_sql(table_name, self.engine, if_exists=if_exists, index=False)
            logging.info(f"Loaded {len(df)} records to {table_name}")
            return True
        except Exception as e:
            logging.error(f"Error loading to {table_name}: {str(e)}")
            return False
    
    def query_to_dataframe(self, query):
        """Execute query and return as DataFrame"""
        try:
            df = pd.read_sql(query, self.engine)
            return df
        except Exception as e:
            logging.error(f"Error executing query: {str(e)}")
            return None
    
    def get_date_key(self, date):
        """Convert date to date key (YYYYMMDD format)"""
        if isinstance(date, str):
            date = pd.to_datetime(date)
        return int(date.strftime('%Y%m%d'))
    
    def populate_date_dimension(self, start_date='2020-01-01', end_date='2026-12-31'):
        """Populate date dimension table"""
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        
        date_data = []
        for date in dates:
            date_data.append({
                'date_key': int(date.strftime('%Y%m%d')),
                'full_date': date.date(),
                'year': date.year,
                'quarter': date.quarter,
                'month': date.month,
                'month_name': date.strftime('%B'),
                'week': date.isocalendar()[1],
                'day_of_week': date.dayofweek,
                'day_name': date.strftime('%A'),
                'is_weekend': date.dayofweek >= 5,
                'fiscal_year': date.year if date.month >= 4 else date.year - 1,
                'fiscal_quarter': ((date.month - 4) % 12) // 3 + 1
            })
        
        df_dates = pd.DataFrame(date_data)
        
        # Check if date dimension already has data
        existing = self.query_to_dataframe("SELECT COUNT(*) as cnt FROM dim_date")
        if existing['cnt'].iloc[0] == 0:
            self.load_to_table(df_dates, 'dim_date', if_exists='append')
            logging.info(f"Populated date dimension with {len(df_dates)} records")
        else:
            logging.info("Date dimension already populated")
    
    def upsert_dimension(self, df, table_name, id_column, key_column):
        """Insert or update dimension table"""
        session = self.Session()
        
        try:
            for _, row in df.iterrows():
                # Check if record exists
                query = f"SELECT {key_column} FROM {table_name} WHERE {id_column} = :id"
                result = session.execute(text(query), {'id': row[id_column]}).fetchone()
                
                if result:
                    # Update existing record
                    update_cols = ', '.join([f"{col} = :{col}" for col in df.columns if col != key_column])
                    update_query = f"UPDATE {table_name} SET {update_cols}, updated_at = CURRENT_TIMESTAMP WHERE {id_column} = :{id_column}"
                    session.execute(text(update_query), row.to_dict())
                else:
                    # Insert new record
                    cols = ', '.join(df.columns)
                    vals = ', '.join([f":{col}" for col in df.columns])
                    insert_query = f"INSERT INTO {table_name} ({cols}) VALUES ({vals})"
                    session.execute(text(insert_query), row.to_dict())
            
            session.commit()
            logging.info(f"Upserted {len(df)} records to {table_name}")
            return True
            
        except Exception as e:
            session.rollback()
            logging.error(f"Error upserting to {table_name}: {str(e)}")
            return False
        finally:
            session.close()
    
    def log_error(self, table_name, column_name, error_type, description, record_id, severity='Medium'):
        """Log data quality error"""
        error_data = {
            'table_name': table_name,
            'column_name': column_name,
            'error_type': error_type,
            'error_description': description,
            'record_id': str(record_id),
            'severity': severity
        }
        
        df_error = pd.DataFrame([error_data])
        self.load_to_table(df_error, 'log_data_errors')
    
    def close(self):
        """Close database connection"""
        self.engine.dispose()
        logging.info("Database connection closed")