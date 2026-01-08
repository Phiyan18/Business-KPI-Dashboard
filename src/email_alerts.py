"""
Email Alert System
Sends notifications when KPIs breach thresholds or data quality issues occur
"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from pathlib import Path

class EmailAlertSystem:
    def __init__(self, smtp_host, smtp_port, username, password, from_email=None):
        """Initialize email alert system"""
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_email = from_email or username
        
        logging.info("Email Alert System initialized")
    
    def send_email(self, to_email, subject, body, html_body=None, attachments=None):
        """Send an email"""
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.from_email
            msg['To'] = to_email
            msg['Subject'] = subject
            msg['Date'] = datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')
            
            # Add text body
            msg.attach(MIMEText(body, 'plain'))
            
            # Add HTML body if provided
            if html_body:
                msg.attach(MIMEText(html_body, 'html'))
            
            # Add attachments if provided
            if attachments:
                for file_path in attachments:
                    self._add_attachment(msg, file_path)
            
            # Connect and send
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
            
            logging.info(f"Email sent to {to_email}: {subject}")
            return True
            
        except Exception as e:
            logging.error(f"Failed to send email: {str(e)}")
            return False
    
    def _add_attachment(self, msg, file_path):
        """Add file attachment to email"""
        try:
            with open(file_path, 'rb') as f:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename={Path(file_path).name}'
                )
                msg.attach(part)
        except Exception as e:
            logging.error(f"Failed to attach file {file_path}: {str(e)}")
    
    def send_kpi_alert(self, to_email, kpi_name, kpi_value, target_value, status):
        """Send alert when KPI breaches threshold"""
        subject = f"🚨 KPI Alert: {kpi_name} - {status}"
        
        # Determine emoji
        emoji = "✅" if status == "Good" else "⚠️" if status == "Warning" else "❌"
        
        body = f"""
{emoji} KPI ALERT
{'='*50}

KPI: {kpi_name}
Current Value: {kpi_value:.2f}
Target Value: {target_value:.2f}
Status: {status}
Variance: {kpi_value - target_value:.2f}

Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{'='*50}

This is an automated alert from the Business KPI Dashboard.
Please review the dashboard for more details.
"""
        
        html_body = f"""
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; }}
        .alert-box {{ 
            border: 2px solid {'#d32f2f' if status == 'Critical' else '#ff9800' if status == 'Warning' else '#4caf50'};
            padding: 20px;
            border-radius: 5px;
            background-color: #f5f5f5;
        }}
        .kpi-name {{ font-size: 24px; font-weight: bold; margin-bottom: 10px; }}
        .kpi-value {{ font-size: 36px; font-weight: bold; color: {'#d32f2f' if status == 'Critical' else '#ff9800' if status == 'Warning' else '#4caf50'}; }}
        .details {{ margin-top: 20px; }}
        .detail-row {{ margin: 5px 0; }}
    </style>
</head>
<body>
    <div class="alert-box">
        <div class="kpi-name">{emoji} {kpi_name}</div>
        <div class="kpi-value">{kpi_value:.2f}</div>
        <div class="details">
            <div class="detail-row"><strong>Target:</strong> {target_value:.2f}</div>
            <div class="detail-row"><strong>Status:</strong> {status}</div>
            <div class="detail-row"><strong>Variance:</strong> {kpi_value - target_value:.2f}</div>
            <div class="detail-row"><strong>Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
        </div>
    </div>
    <p style="margin-top: 20px; color: #666;">
        This is an automated alert from the Business KPI Dashboard.
    </p>
</body>
</html>
"""
        
        return self.send_email(to_email, subject, body, html_body)
    
    def send_data_quality_alert(self, to_email, table_name, quality_score, issues):
        """Send alert for data quality issues"""
        subject = f"⚠️ Data Quality Alert: {table_name}"
        
        issue_summary = "\n".join([
            f"  • {issue['type']}: {issue['description']}"
            for issue in issues[:5]  # Top 5 issues
        ])
        
        body = f"""
⚠️ DATA QUALITY ALERT
{'='*50}

Table: {table_name}
Quality Score: {quality_score:.2f}/100
Status: {'PASS' if quality_score >= 90 else 'WARNING' if quality_score >= 70 else 'FAIL'}

Top Issues:
{issue_summary}

Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{'='*50}

Please review and address these data quality issues.
"""
        
        return self.send_email(to_email, subject, body)
    
    def send_pipeline_summary(self, to_email, success, kpis_calculated, quality_scores, errors):
        """Send daily pipeline execution summary"""
        subject = f"{'✅' if success else '❌'} Daily Pipeline Report - {datetime.now().strftime('%Y-%m-%d')}"
        
        kpi_summary = "\n".join([
            f"  • {kpi}: {value:.2f}"
            for kpi, value in list(kpis_calculated.items())[:10]
        ])
        
        quality_summary = "\n".join([
            f"  • {table}: {score:.2f}/100"
            for table, score in quality_scores.items()
        ])
        
        error_summary = f"  {len(errors)} errors logged" if errors else "  No errors"
        
        body = f"""
{'✅ PIPELINE COMPLETED SUCCESSFULLY' if success else '❌ PIPELINE FAILED'}
{'='*50}

Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Status: {'Success' if success else 'Failed'}

KPI Summary:
{kpi_summary}

Data Quality Scores:
{quality_summary}

Errors:
{error_summary}

{'='*50}

View the complete dashboard for detailed metrics.
"""
        
        return self.send_email(to_email, subject, body)

# Example usage:
# from email_alerts import EmailAlertSystem
# 
# alert_system = EmailAlertSystem(
#     smtp_host='smtp.gmail.com',
#     smtp_port=587,
#     username='your_email@gmail.com',
#     password='your_app_password'
# )
# 
# # Send KPI alert
# alert_system.send_kpi_alert(
#     to_email='manager@company.com',
#     kpi_name='Customer Churn Rate',
#     kpi_value=18.5,
#     target_value=15.0,
#     status='Warning'
# )