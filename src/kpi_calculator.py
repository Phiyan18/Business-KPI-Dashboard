"""
KPI Calculator Module
Calculates business KPIs and metrics
"""
import pandas as pd
import numpy as np
import yaml
import logging
from datetime import datetime, timedelta

class KPICalculator:
    def __init__(self, config_path='config/config.yaml', db_manager=None):
        """Initialize KPI calculator"""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.kpi_config = self.config['kpi_config']
        self.db_manager = db_manager
        self.kpis = {}
        
        logging.info("KPI Calculator initialized")
    
    def calculate_revenue_metrics(self, df_sales):
        """Calculate revenue-related KPIs"""
        kpis = {}
        
        # Calculate revenue components
        df_sales['revenue'] = df_sales['quantity'] * df_sales['unit_price'] * (1 - df_sales['discount'])
        
        # Total Revenue
        total_revenue = df_sales['revenue'].sum()
        revenue_target = self.kpi_config['revenue_target']
        
        kpis['Total_Revenue'] = {
            'value': total_revenue,
            'target': revenue_target,
            'variance': total_revenue - revenue_target,
            'variance_pct': ((total_revenue - revenue_target) / revenue_target) * 100 if revenue_target > 0 else 0,
            'status': 'Good' if total_revenue >= revenue_target else 'Critical'
        }
        
        # Average Order Value (AOV)
        aov = df_sales['revenue'].mean()
        kpis['Avg_Order_Value'] = {
            'value': aov,
            'target': None,
            'variance': None,
            'variance_pct': None,
            'status': 'Good'
        }
        
        # Revenue Growth (comparing to previous period)
        if 'order_date' in df_sales.columns:
            df_sales['order_date'] = pd.to_datetime(df_sales['order_date'])
            current_month = df_sales['order_date'].max().replace(day=1)
            prev_month = current_month - timedelta(days=1)
            prev_month = prev_month.replace(day=1)
            
            current_revenue = df_sales[df_sales['order_date'] >= current_month]['revenue'].sum()
            previous_revenue = df_sales[
                (df_sales['order_date'] >= prev_month) & 
                (df_sales['order_date'] < current_month)
            ]['revenue'].sum()
            
            if previous_revenue > 0:
                growth_rate = ((current_revenue - previous_revenue) / previous_revenue) * 100
            else:
                growth_rate = 0
            
            kpis['Revenue_Growth_Rate'] = {
                'value': growth_rate,
                'target': 5.0,  # 5% growth target
                'variance': growth_rate - 5.0,
                'variance_pct': None,
                'status': 'Good' if growth_rate >= 5 else 'Warning' if growth_rate >= 0 else 'Critical'
            }
        
        return kpis
    
    def calculate_customer_metrics(self, df_sales, df_customers):
        """Calculate customer-related KPIs"""
        kpis = {}
        
        # Customer Count
        unique_customers = df_sales['customer_id'].nunique()
        kpis['Active_Customers'] = {
            'value': unique_customers,
            'target': None,
            'variance': None,
            'variance_pct': None,
            'status': 'Good'
        }
        
        # Customer Churn Rate (simplified calculation)
        # In real scenario, need historical data
        if 'order_date' in df_sales.columns:
            df_sales['order_date'] = pd.to_datetime(df_sales['order_date'])
            last_30_days = df_sales['order_date'].max() - timedelta(days=30)
            last_60_days = df_sales['order_date'].max() - timedelta(days=60)
            
            customers_60_days = set(df_sales[
                df_sales['order_date'] >= last_60_days
            ]['customer_id'].unique())
            
            customers_30_days = set(df_sales[
                df_sales['order_date'] >= last_30_days
            ]['customer_id'].unique())
            
            churned = len(customers_60_days - customers_30_days)
            churn_rate = (churned / len(customers_60_days)) if len(customers_60_days) > 0 else 0
            
            churn_threshold = self.kpi_config['churn_threshold']
            
            kpis['Customer_Churn_Rate'] = {
                'value': churn_rate * 100,
                'target': churn_threshold * 100,
                'variance': (churn_rate - churn_threshold) * 100,
                'variance_pct': None,
                'status': 'Good' if churn_rate <= churn_threshold else 'Warning' if churn_rate <= churn_threshold * 1.5 else 'Critical'
            }
        
        # Customer Lifetime Value (CLV) - simplified
        revenue_per_customer = df_sales.groupby('customer_id')['revenue'].sum().mean()
        kpis['Customer_Lifetime_Value'] = {
            'value': revenue_per_customer,
            'target': None,
            'variance': None,
            'variance_pct': None,
            'status': 'Good'
        }
        
        # Repeat Purchase Rate
        purchase_counts = df_sales.groupby('customer_id').size()
        repeat_customers = (purchase_counts > 1).sum()
        repeat_rate = repeat_customers / len(purchase_counts) if len(purchase_counts) > 0 else 0
        
        kpis['Repeat_Purchase_Rate'] = {
            'value': repeat_rate * 100,
            'target': None,
            'variance': None,
            'variance_pct': None,
            'status': 'Good'
        }
        
        return kpis
    
    def calculate_product_metrics(self, df_sales, df_products):
        """Calculate product-related KPIs"""
        kpis = {}
        
        # Product mix
        top_products = df_sales.groupby('product_id')['revenue'].sum().nlargest(10)
        
        # Average items per order
        avg_items = df_sales.groupby('transaction_id')['quantity'].sum().mean()
        kpis['Avg_Items_Per_Order'] = {
            'value': avg_items,
            'target': None,
            'variance': None,
            'variance_pct': None,
            'status': 'Good'
        }
        
        return kpis
    
    def calculate_operational_metrics(self, df_sales):
        """Calculate operational KPIs"""
        kpis = {}
        
        # Calculate costs and profit
        if 'unit_price' in df_sales.columns and 'quantity' in df_sales.columns:
            # Assume cost is 60% of price (simplified)
            df_sales['cost'] = df_sales['quantity'] * df_sales['unit_price'] * 0.6
            df_sales['profit'] = df_sales['revenue'] - df_sales['cost']
            
            # Profit Margin
            total_profit = df_sales['profit'].sum()
            total_revenue = df_sales['revenue'].sum()
            profit_margin = (total_profit / total_revenue) * 100 if total_revenue > 0 else 0
            
            kpis['Profit_Margin'] = {
                'value': profit_margin,
                'target': 25.0,  # 25% target margin
                'variance': profit_margin - 25.0,
                'variance_pct': None,
                'status': 'Good' if profit_margin >= 25 else 'Warning' if profit_margin >= 20 else 'Critical'
            }
            
            # Cost to Revenue Ratio
            cost_ratio = (df_sales['cost'].sum() / total_revenue) * 100 if total_revenue > 0 else 0
            kpis['Cost_to_Revenue_Ratio'] = {
                'value': cost_ratio,
                'target': 60.0,
                'variance': 60.0 - cost_ratio,  # Lower is better
                'variance_pct': None,
                'status': 'Good' if cost_ratio <= 60 else 'Warning' if cost_ratio <= 70 else 'Critical'
            }
        
        # Order fulfillment rate (assuming all orders are fulfilled)
        kpis['Order_Fulfillment_Rate'] = {
            'value': 100.0,
            'target': 98.0,
            'variance': 2.0,
            'variance_pct': None,
            'status': 'Good'
        }
        
        return kpis
    
    def calculate_conversion_metrics(self, df_sales, df_customers):
        """Calculate conversion-related KPIs"""
        kpis = {}
        
        # Conversion Rate (customers who made purchase vs total customers)
        purchasing_customers = df_sales['customer_id'].nunique()
        total_customers = len(df_customers)
        
        conversion_rate = (purchasing_customers / total_customers) if total_customers > 0 else 0
        conversion_target = self.kpi_config['conversion_target']
        
        kpis['Conversion_Rate'] = {
            'value': conversion_rate * 100,
            'target': conversion_target * 100,
            'variance': (conversion_rate - conversion_target) * 100,
            'variance_pct': None,
            'status': 'Good' if conversion_rate >= conversion_target else 'Warning'
        }
        
        return kpis
    
    def calculate_all_kpis(self, df_sales, df_customers, df_products):
        """Calculate all KPIs"""
        logging.info("Calculating KPIs...")
        
        # Calculate all KPI categories
        revenue_kpis = self.calculate_revenue_metrics(df_sales)
        customer_kpis = self.calculate_customer_metrics(df_sales, df_customers)
        product_kpis = self.calculate_product_metrics(df_sales, df_products)
        operational_kpis = self.calculate_operational_metrics(df_sales)
        conversion_kpis = self.calculate_conversion_metrics(df_sales, df_customers)
        
        # Merge all KPIs
        self.kpis = {
            **revenue_kpis,
            **customer_kpis,
            **product_kpis,
            **operational_kpis,
            **conversion_kpis
        }
        
        logging.info(f"Calculated {len(self.kpis)} KPIs")
        
        return self.kpis
    
    def save_kpis_to_db(self, date_key):
        """Save KPIs to database"""
        if not self.db_manager or not self.kpis:
            return
        
        kpi_records = []
        
        for kpi_name, kpi_data in self.kpis.items():
            record = {
                'date_key': date_key,
                'kpi_name': kpi_name,
                'kpi_value': kpi_data['value'],
                'target_value': kpi_data['target'],
                'variance': kpi_data['variance'],
                'variance_pct': kpi_data['variance_pct'],
                'status': kpi_data['status']
            }
            kpi_records.append(record)
        
        df_kpis = pd.DataFrame(kpi_records)
        self.db_manager.load_to_table(df_kpis, 'fact_kpis')
        
        logging.info(f"Saved {len(kpi_records)} KPI records to database")
    
    def print_kpi_summary(self):
        """Print KPI summary to console"""
        print("\n" + "="*60)
        print("KPI SUMMARY REPORT")
        print("="*60)
        
        for kpi_name, kpi_data in self.kpis.items():
            status_icon = "✅" if kpi_data['status'] == 'Good' else "⚠️" if kpi_data['status'] == 'Warning' else "❌"
            
            print(f"\n{status_icon} {kpi_name.replace('_', ' ')}")
            print(f"   Value: {kpi_data['value']:.2f}")
            
            if kpi_data['target'] is not None:
                print(f"   Target: {kpi_data['target']:.2f}")
                print(f"   Variance: {kpi_data['variance']:.2f}")
            
            print(f"   Status: {kpi_data['status']}")
        
        print("\n" + "="*60)