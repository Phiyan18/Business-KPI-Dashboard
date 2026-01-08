"""
REST API Module (Optional)
Provides HTTP endpoints to access KPIs and data quality metrics
Uses Flask for simplicity
"""
from flask import Flask, jsonify, request
from flask_cors import CORS
import logging
from datetime import datetime, timedelta
from database import DatabaseManager

app = Flask(__name__)
CORS(app)  # Enable CORS for Power BI or web dashboards

# Initialize database connection
db_manager = DatabaseManager()

@app.route('/')
def home():
    """API home endpoint"""
    return jsonify({
        'message': 'Business KPI Dashboard API',
        'version': '1.0',
        'endpoints': {
            '/health': 'Health check',
            '/kpis': 'Get all KPIs',
            '/kpis/<name>': 'Get specific KPI',
            '/quality': 'Get data quality metrics',
            '/sales/summary': 'Get sales summary',
            '/errors': 'Get error log'
        }
    })

@app.route('/health')
def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        result = db_manager.query_to_dataframe("SELECT 1")
        db_status = 'connected' if result is not None else 'disconnected'
    except:
        db_status = 'error'
    
    return jsonify({
        'status': 'healthy' if db_status == 'connected' else 'unhealthy',
        'timestamp': datetime.now().isoformat(),
        'database': db_status
    })

@app.route('/kpis', methods=['GET'])
def get_kpis():
    """Get all KPIs, optionally filtered by date range"""
    try:
        # Get query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        query = "SELECT * FROM vw_kpi_dashboard"
        
        if start_date and end_date:
            query += f" WHERE full_date BETWEEN '{start_date}' AND '{end_date}'"
        
        query += " ORDER BY full_date DESC LIMIT 100"
        
        df = db_manager.query_to_dataframe(query)
        
        if df is None or df.empty:
            return jsonify({'kpis': [], 'count': 0})
        
        return jsonify({
            'kpis': df.to_dict('records'),
            'count': len(df),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logging.error(f"Error fetching KPIs: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/kpis/<kpi_name>', methods=['GET'])
def get_kpi_by_name(kpi_name):
    """Get specific KPI with historical data"""
    try:
        days = request.args.get('days', 30, type=int)
        
        query = f"""
        SELECT 
            full_date,
            kpi_value,
            target_value,
            variance,
            variance_pct,
            status
        FROM vw_kpi_dashboard
        WHERE kpi_name = '{kpi_name}'
        AND full_date >= CURRENT_DATE - INTERVAL '{days} days'
        ORDER BY full_date DESC
        """
        
        df = db_manager.query_to_dataframe(query)
        
        if df is None or df.empty:
            return jsonify({'error': f'KPI {kpi_name} not found'}), 404
        
        # Calculate statistics
        stats = {
            'current_value': float(df.iloc[0]['kpi_value']),
            'target_value': float(df.iloc[0]['target_value']) if df.iloc[0]['target_value'] else None,
            'current_status': df.iloc[0]['status'],
            'average': float(df['kpi_value'].mean()),
            'min': float(df['kpi_value'].min()),
            'max': float(df['kpi_value'].max()),
            'trend': 'up' if df.iloc[0]['kpi_value'] > df.iloc[-1]['kpi_value'] else 'down'
        }
        
        return jsonify({
            'kpi_name': kpi_name,
            'statistics': stats,
            'history': df.to_dict('records'),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logging.error(f"Error fetching KPI {kpi_name}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/quality', methods=['GET'])
def get_data_quality():
    """Get data quality metrics"""
    try:
        query = """
        SELECT 
            table_name,
            quality_score,
            completeness_pct,
            duplicate_pct,
            error_count,
            status,
            full_date
        FROM vw_data_quality_dashboard
        ORDER BY full_date DESC
        LIMIT 100
        """
        
        df = db_manager.query_to_dataframe(query)
        
        if df is None or df.empty:
            return jsonify({'quality_metrics': [], 'count': 0})
        
        # Group by table to get latest scores
        latest_scores = df.groupby('table_name').first().reset_index()
        
        return jsonify({
            'overall_health': 'healthy' if all(latest_scores['quality_score'] >= 90) else 'issues_detected',
            'tables': latest_scores.to_dict('records'),
            'history': df.to_dict('records'),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logging.error(f"Error fetching quality metrics: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/sales/summary', methods=['GET'])
def get_sales_summary():
    """Get sales summary statistics"""
    try:
        period = request.args.get('period', 'day')  # day, week, month
        
        if period == 'day':
            date_filter = "CURRENT_DATE"
        elif period == 'week':
            date_filter = "CURRENT_DATE - INTERVAL '7 days'"
        else:  # month
            date_filter = "CURRENT_DATE - INTERVAL '30 days'"
        
        query = f"""
        SELECT 
            COUNT(DISTINCT transaction_id) as total_transactions,
            COUNT(DISTINCT customer_name) as unique_customers,
            SUM(revenue) as total_revenue,
            AVG(revenue) as avg_order_value,
            SUM(profit) as total_profit,
            (SUM(profit) / SUM(revenue) * 100) as profit_margin
        FROM vw_sales_summary
        WHERE full_date >= {date_filter}
        """
        
        df = db_manager.query_to_dataframe(query)
        
        if df is None or df.empty:
            return jsonify({'error': 'No sales data found'}), 404
        
        summary = df.iloc[0].to_dict()
        
        # Convert Decimal to float for JSON serialization
        for key, value in summary.items():
            if hasattr(value, 'item'):
                summary[key] = float(value)
        
        return jsonify({
            'period': period,
            'summary': summary,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logging.error(f"Error fetching sales summary: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/errors', methods=['GET'])
def get_errors():
    """Get recent error log"""
    try:
        limit = request.args.get('limit', 50, type=int)
        severity = request.args.get('severity')
        
        query = "SELECT * FROM vw_error_log"
        
        if severity:
            query += f" WHERE severity = '{severity}'"
        
        query += f" ORDER BY error_timestamp DESC LIMIT {limit}"
        
        df = db_manager.query_to_dataframe(query)
        
        if df is None or df.empty:
            return jsonify({'errors': [], 'count': 0})
        
        return jsonify({
            'errors': df.to_dict('records'),
            'count': len(df),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logging.error(f"Error fetching error log: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/dashboard/summary', methods=['GET'])
def get_dashboard_summary():
    """Get complete dashboard summary for homepage"""
    try:
        # Get latest KPIs
        kpi_query = """
        SELECT kpi_name, kpi_value, target_value, status
        FROM fact_kpis
        WHERE date_key = (SELECT MAX(date_key) FROM fact_kpis)
        """
        
        df_kpis = db_manager.query_to_dataframe(kpi_query)
        
        # Get quality scores
        quality_query = """
        SELECT table_name, quality_score, status
        FROM fact_data_quality
        WHERE date_key = (SELECT MAX(date_key) FROM fact_data_quality)
        """
        
        df_quality = db_manager.query_to_dataframe(quality_query)
        
        # Get today's sales
        sales_query = """
        SELECT 
            COUNT(*) as transactions,
            SUM(revenue) as revenue,
            SUM(profit) as profit
        FROM fact_sales
        WHERE date_key = (SELECT MAX(date_key) FROM fact_sales)
        """
        
        df_sales = db_manager.query_to_dataframe(sales_query)
        
        return jsonify({
            'kpis': df_kpis.to_dict('records') if df_kpis is not None else [],
            'quality': df_quality.to_dict('records') if df_quality is not None else [],
            'sales': df_sales.iloc[0].to_dict() if df_sales is not None else {},
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logging.error(f"Error fetching dashboard summary: {str(e)}")
        return jsonify({'error': str(e)}), 500

def run_api(host='0.0.0.0', port=5000, debug=False):
    """Run the Flask API"""
    app.run(host=host, port=port, debug=debug)

if __name__ == '__main__':
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    print("\n" + "="*60)
    print("Business KPI Dashboard API")
    print("="*60)
    print("\nAPI Endpoints:")
    print("  • http://localhost:5000/")
    print("  • http://localhost:5000/health")
    print("  • http://localhost:5000/kpis")
    print("  • http://localhost:5000/quality")
    print("  • http://localhost:5000/sales/summary")
    print("\n" + "="*60 + "\n")
    
    run_api(debug=True)