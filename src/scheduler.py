"""
Automated Scheduler for Pipeline Execution
Runs the pipeline on a schedule (daily/hourly/weekly)
"""
import schedule
import time
import yaml
import logging
from datetime import datetime
from main import DataPipeline

def run_scheduled_pipeline():
    """Execute the pipeline on schedule"""
    logging.info(f"Scheduled pipeline execution started at {datetime.now()}")
    
    try:
        pipeline = DataPipeline()
        success = pipeline.run_pipeline(initialize_db=False)
        
        if success:
            logging.info("✅ Scheduled pipeline completed successfully")
        else:
            logging.error("❌ Scheduled pipeline failed")
            
    except Exception as e:
        logging.error(f"❌ Scheduled pipeline error: {str(e)}", exc_info=True)

def setup_scheduler():
    """Setup the scheduler based on config"""
    with open('config/config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    schedule_config = config.get('schedule', {})
    
    if not schedule_config.get('enabled', False):
        print("⚠️  Scheduler is disabled in config.yaml")
        return False
    
    frequency = schedule_config.get('frequency', 'daily')
    time_str = schedule_config.get('time', '06:00')
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('data/logs/scheduler.log'),
            logging.StreamHandler()
        ]
    )
    
    # Setup schedule
    if frequency == 'daily':
        schedule.every().day.at(time_str).do(run_scheduled_pipeline)
        print(f"📅 Scheduler configured: Daily at {time_str}")
        
    elif frequency == 'hourly':
        schedule.every().hour.do(run_scheduled_pipeline)
        print(f"📅 Scheduler configured: Every hour")
        
    elif frequency == 'weekly':
        schedule.every().monday.at(time_str).do(run_scheduled_pipeline)
        print(f"📅 Scheduler configured: Weekly on Monday at {time_str}")
    
    else:
        print(f"❌ Unknown frequency: {frequency}")
        return False
    
    return True

def main():
    """Main scheduler loop"""
    print("="*60)
    print("BUSINESS KPI DASHBOARD - AUTOMATED SCHEDULER")
    print("="*60)
    
    if not setup_scheduler():
        return
    
    print("\n🚀 Scheduler is running...")
    print("Press Ctrl+C to stop\n")
    
    # Run once immediately (optional)
    # run_scheduled_pipeline()
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Scheduler stopped by user")
        logging.info("Scheduler stopped")

if __name__ == "__main__":
    main()