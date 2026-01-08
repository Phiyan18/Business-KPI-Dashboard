"""
Data Quality Module
Performs comprehensive data quality checks and validation
"""
import pandas as pd
import numpy as np
import yaml
import logging
from datetime import datetime

class DataQualityChecker:
    def __init__(self, config_path='config/config.yaml', db_manager=None):
        """Initialize data quality checker"""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.thresholds = self.config['quality_thresholds']
        self.db_manager = db_manager
        self.quality_report = {}
        
        logging.info("Data Quality Checker initialized")
    
    def check_completeness(self, df, table_name):
        """Check for missing values"""
        total_cells = df.shape[0] * df.shape[1]
        missing_cells = df.isnull().sum().sum()
        completeness = (total_cells - missing_cells) / total_cells
        
        issues = []
        for col in df.columns:
            missing_count = df[col].isnull().sum()
            if missing_count > 0:
                missing_pct = (missing_count / len(df)) * 100
                severity = 'High' if missing_pct > 10 else 'Medium' if missing_pct > 5 else 'Low'
                
                issues.append({
                    'column': col,
                    'missing_count': missing_count,
                    'missing_pct': missing_pct,
                    'severity': severity
                })
                
                # Log to database
                if self.db_manager:
                    self.db_manager.log_error(
                        table_name=table_name,
                        column_name=col,
                        error_type='Missing',
                        description=f'{missing_count} missing values ({missing_pct:.2f}%)',
                        record_id='N/A',
                        severity=severity
                    )
        
        return {
            'completeness': completeness,
            'status': 'Pass' if completeness >= self.thresholds['completeness_min'] else 'Fail',
            'issues': issues
        }
    
    def check_duplicates(self, df, table_name, key_columns=None):
        """Check for duplicate records"""
        if key_columns is None:
            # Check all columns
            duplicates = df.duplicated()
        else:
            # Check specific key columns
            duplicates = df.duplicated(subset=key_columns)
        
        duplicate_count = duplicates.sum()
        duplicate_pct = duplicate_count / len(df)
        
        issues = []
        if duplicate_count > 0:
            severity = 'High' if duplicate_pct > 0.05 else 'Medium' if duplicate_pct > 0.01 else 'Low'
            
            issues.append({
                'duplicate_count': duplicate_count,
                'duplicate_pct': duplicate_pct * 100,
                'severity': severity
            })
            
            # Log to database
            if self.db_manager:
                self.db_manager.log_error(
                    table_name=table_name,
                    column_name=str(key_columns) if key_columns else 'All',
                    error_type='Duplicate',
                    description=f'{duplicate_count} duplicate records ({duplicate_pct*100:.2f}%)',
                    record_id='N/A',
                    severity=severity
                )
        
        return {
            'duplicate_count': duplicate_count,
            'duplicate_pct': duplicate_pct,
            'status': 'Pass' if duplicate_pct <= self.thresholds['duplicate_max'] else 'Fail',
            'issues': issues
        }
    
    def check_outliers(self, df, table_name, numeric_columns=None):
        """Detect outliers using Z-score method"""
        if numeric_columns is None:
            numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()
        
        outliers = {}
        issues = []
        
        for col in numeric_columns:
            if df[col].notna().sum() > 0:
                z_scores = np.abs((df[col] - df[col].mean()) / df[col].std())
                outlier_mask = z_scores > self.thresholds['outlier_zscore']
                outlier_count = outlier_mask.sum()
                
                if outlier_count > 0:
                    outlier_pct = (outlier_count / len(df)) * 100
                    severity = 'Medium' if outlier_pct > 5 else 'Low'
                    
                    outliers[col] = {
                        'count': outlier_count,
                        'pct': outlier_pct,
                        'values': df[outlier_mask][col].tolist()[:10]  # First 10 outliers
                    }
                    
                    issues.append({
                        'column': col,
                        'outlier_count': outlier_count,
                        'outlier_pct': outlier_pct,
                        'severity': severity
                    })
                    
                    # Log to database
                    if self.db_manager:
                        self.db_manager.log_error(
                            table_name=table_name,
                            column_name=col,
                            error_type='Outlier',
                            description=f'{outlier_count} outliers detected ({outlier_pct:.2f}%)',
                            record_id='N/A',
                            severity=severity
                        )
        
        return {
            'outliers': outliers,
            'issues': issues,
            'status': 'Pass' if len(outliers) == 0 else 'Warning'
        }
    
    def check_business_rules(self, df, table_name):
        """Validate business rules"""
        issues = []
        
        # Rule 1: Prices should be positive
        if 'unit_price' in df.columns:
            invalid_price = df['unit_price'] <= 0
            if invalid_price.any():
                count = invalid_price.sum()
                issues.append({
                    'rule': 'Positive Price',
                    'column': 'unit_price',
                    'invalid_count': count,
                    'severity': 'High'
                })
                
                if self.db_manager:
                    self.db_manager.log_error(
                        table_name=table_name,
                        column_name='unit_price',
                        error_type='Invalid',
                        description=f'{count} records with non-positive prices',
                        record_id='N/A',
                        severity='High'
                    )
        
        # Rule 2: Quantity should be positive
        if 'quantity' in df.columns:
            invalid_qty = df['quantity'] <= 0
            if invalid_qty.any():
                count = invalid_qty.sum()
                issues.append({
                    'rule': 'Positive Quantity',
                    'column': 'quantity',
                    'invalid_count': count,
                    'severity': 'High'
                })
                
                if self.db_manager:
                    self.db_manager.log_error(
                        table_name=table_name,
                        column_name='quantity',
                        error_type='Invalid',
                        description=f'{count} records with non-positive quantity',
                        record_id='N/A',
                        severity='High'
                    )
        
        # Rule 3: Discount should be between 0 and 1
        if 'discount' in df.columns:
            invalid_discount = (df['discount'] < 0) | (df['discount'] > 1)
            if invalid_discount.any():
                count = invalid_discount.sum()
                issues.append({
                    'rule': 'Valid Discount Range',
                    'column': 'discount',
                    'invalid_count': count,
                    'severity': 'Medium'
                })
                
                if self.db_manager:
                    self.db_manager.log_error(
                        table_name=table_name,
                        column_name='discount',
                        error_type='Invalid',
                        description=f'{count} records with invalid discount values',
                        record_id='N/A',
                        severity='Medium'
                    )
        
        # Rule 4: Email format validation
        if 'email' in df.columns:
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            invalid_email = ~df['email'].astype(str).str.match(email_pattern, na=False)
            if invalid_email.any():
                count = invalid_email.sum()
                issues.append({
                    'rule': 'Valid Email Format',
                    'column': 'email',
                    'invalid_count': count,
                    'severity': 'Low'
                })
        
        return {
            'issues': issues,
            'status': 'Pass' if len(issues) == 0 else 'Warning'
        }
    
    def calculate_quality_score(self, checks):
        """Calculate overall data quality score (0-100)"""
        weights = {
            'completeness': 0.3,
            'duplicates': 0.2,
            'outliers': 0.2,
            'business_rules': 0.3
        }
        
        score = 0
        
        # Completeness score
        if 'completeness' in checks:
            score += checks['completeness']['completeness'] * 100 * weights['completeness']
        
        # Duplicates score
        if 'duplicates' in checks:
            dup_pct = checks['duplicates']['duplicate_pct']
            dup_score = max(0, 1 - dup_pct / 0.1) * 100  # Penalize heavily after 10%
            score += dup_score * weights['duplicates']
        
        # Outliers score (minor penalty)
        if 'outliers' in checks:
            outlier_count = len(checks['outliers']['outliers'])
            outlier_score = max(0, 100 - outlier_count * 5)
            score += outlier_score * weights['outliers']
        
        # Business rules score
        if 'business_rules' in checks:
            br_issues = len(checks['business_rules']['issues'])
            br_score = max(0, 100 - br_issues * 10)
            score += br_score * weights['business_rules']
        
        return round(score, 2)
    
    def run_quality_checks(self, df, table_name, key_columns=None):
        """Run all quality checks on a dataframe"""
        logging.info(f"Running quality checks on {table_name}...")
        
        checks = {}
        
        # Check completeness
        checks['completeness'] = self.check_completeness(df, table_name)
        
        # Check duplicates
        checks['duplicates'] = self.check_duplicates(df, table_name, key_columns)
        
        # Check outliers
        checks['outliers'] = self.check_outliers(df, table_name)
        
        # Check business rules
        checks['business_rules'] = self.check_business_rules(df, table_name)
        
        # Calculate overall quality score
        quality_score = self.calculate_quality_score(checks)
        
        # Determine overall status
        if quality_score >= 90:
            overall_status = 'Pass'
        elif quality_score >= 70:
            overall_status = 'Warning'
        else:
            overall_status = 'Fail'
        
        self.quality_report[table_name] = {
            'checks': checks,
            'quality_score': quality_score,
            'status': overall_status,
            'timestamp': datetime.now()
        }
        
        logging.info(f"Quality check completed for {table_name}: Score={quality_score}, Status={overall_status}")
        
        return checks, quality_score, overall_status
    
    def save_quality_metrics_to_db(self, table_name, date_key):
        """Save quality metrics to database"""
        if table_name not in self.quality_report or not self.db_manager:
            return
        
        report = self.quality_report[table_name]
        checks = report['checks']
        
        # Prepare data quality fact record
        dq_data = {
            'date_key': date_key,
            'table_name': table_name,
            'total_records': 0,
            'complete_records': 0,
            'completeness_pct': checks['completeness']['completeness'] * 100,
            'duplicate_records': checks['duplicates']['duplicate_count'],
            'duplicate_pct': checks['duplicates']['duplicate_pct'] * 100,
            'null_count': 0,
            'outlier_count': sum([v['count'] for v in checks['outliers']['outliers'].values()]),
            'error_count': len(checks['business_rules']['issues']),
            'quality_score': report['quality_score'],
            'status': report['status']
        }
        
        df_dq = pd.DataFrame([dq_data])
        self.db_manager.load_to_table(df_dq, 'fact_data_quality')
        
        logging.info(f"Quality metrics saved to database for {table_name}")