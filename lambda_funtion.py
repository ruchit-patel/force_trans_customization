import json
import boto3
import urllib3
import logging
import email
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import base64
from datetime import datetime

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize clients
s3_client = boto3.client('s3')
http = urllib3.PoolManager()

# Configuration - Update these values
# FRAPPE_BASE_URL = "https://bda3974fbea5.ngrok-free.app"  # Update with your Frappe URL
# FRAPPE_WEBHOOK_ENDPOINT = "/api/method/force_trans_customization.api.email_webhook.test"  # Update endpoint
# FRAPPE_API_KEY = "2ae35805831d36f"  # Optional: for authentication
# FRAPPE_API_SECRET = "87eb7ee488899a1"  # Optional: for authentication

FRAPPE_BASE_URL = "https://force-trans.v.frappe.cloud"  # Update with your Frappe URL
FRAPPE_WEBHOOK_ENDPOINT = "/api/method/force_trans_customization.api.email_webhook.test"  # Update endpoint
FRAPPE_API_KEY = "7cbc2d5765876b8"  # Optional: for authentication
FRAPPE_API_SECRET = "8e1e71bcd05a251"  # Optional: for authentication

def lambda_handler(event, context):
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        # Process each SES record
        for record in event['Records']:
            if 'ses' in record:
                process_ses_email(record['ses'])
            else:
                logger.warning(f"Non-SES record received: {record}")
        
        return {
            'statusCode': 200,
            'body': json.dumps('Email processed successfully')
        }
        
    except Exception as e:
        logger.error(f"Error processing email: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error: {str(e)}')
        }

def process_ses_email(ses_data):
    """Process SES email data and send webhook to Frappe"""
    
    mail_data = ses_data['mail']
    receipt_data = ses_data['receipt']
    
    # Extract basic email information
    message_id = mail_data['messageId']
    timestamp = mail_data['timestamp']
    source = mail_data['source']
    destination = mail_data['destination']
    
    logger.info(f"Processing email - ID: {message_id}, From: {source}, To: {destination}")
    
    # Get S3 object key (email location) - STATIC BUCKET APPROACH
    s3_bucket = "mysesemailbucket"  # Static bucket name
    
    logger.info(f"Searching for email with message ID: {message_id} in bucket: {s3_bucket}")
    
    # Try different possible file naming patterns for SES
    possible_keys = [
        f"{message_id}",
        f"emails/{message_id}",
        f"{message_id}.txt",
        f"emails/{message_id}.txt",
        f"incoming/{message_id}",
        f"incoming/{message_id}.txt",
        f"raw/{message_id}",
        f"raw/{message_id}.txt"
    ]
    
    # Try to find the actual file in S3
    s3_key = find_email_in_s3(s3_bucket, possible_keys, message_id)
    
    if not s3_key:
        logger.error(f"Could not find email file in S3 bucket '{s3_bucket}' with message ID '{message_id}'")
        return
    
    logger.info(f"Found email at S3 location - Bucket: {s3_bucket}, Key: {s3_key}")
    
    # Read email from S3
    email_content = read_email_from_s3(s3_bucket, s3_key)
    if not email_content:
        logger.error("Could not read email from S3")
        return
    
    # Parse email
    parsed_email = parse_email(email_content)
    
    # Prepare webhook payload
    webhook_payload = {
        'message_id': message_id,
        'timestamp': timestamp,
        'from_email': source,
        'to_emails': destination,
        'subject': parsed_email.get('subject', ''),
        'body_text': parsed_email.get('body_text', ''),
        'body_html': parsed_email.get('body_html', ''),
        'attachments': parsed_email.get('attachments', []),
        's3_bucket': s3_bucket,
        's3_key': s3_key,
        'headers': parsed_email.get('headers', {}),
        'spam_verdict': receipt_data.get('spamVerdict', {}).get('status'),
        'virus_verdict': receipt_data.get('virusVerdict', {}).get('status'),
        'dkim_verdict': receipt_data.get('dkimVerdict', {}).get('status'),
        'spf_verdict': receipt_data.get('spfVerdict', {}).get('status')
    }
    
    # Send webhook to Frappe
    send_webhook_to_frappe(webhook_payload)

def find_email_in_s3(bucket, possible_keys, message_id):
    """Try to find the email file in S3 using various possible key patterns"""
    try:
        for key in possible_keys:
            try:
                # Check if object exists
                s3_client.head_object(Bucket=bucket, Key=key)
                logger.info(f"Found email file at: s3://{bucket}/{key}")
                return key
            except s3_client.exceptions.NoSuchKey:
                continue
            except Exception as e:
                logger.warning(f"Error checking key '{key}': {str(e)}")
                continue
        
        # If none of the standard patterns work, try listing objects with message_id prefix
        logger.info(f"Standard patterns failed. Searching bucket for files containing: {message_id}")
        try:
            response = s3_client.list_objects_v2(
                Bucket=bucket,
                MaxKeys=100
            )
            
            if 'Contents' in response:
                for obj in response['Contents']:
                    key = obj['Key']
                    if message_id in key:
                        logger.info(f"Found email file by search: s3://{bucket}/{key}")
                        return key
        except Exception as e:
            logger.error(f"Error listing S3 objects: {str(e)}")
        
        return None
        
    except Exception as e:
        logger.error(f"Error finding email in S3: {str(e)}")
        return None

def read_email_from_s3(bucket, key):
    """Read email content from S3"""
    try:
        logger.info(f"Reading email from S3 - Bucket: {bucket}, Key: {key}")
        response = s3_client.get_object(Bucket=bucket, Key=key)
        email_content = response['Body'].read()
        logger.info(f"Successfully read email content ({len(email_content)} bytes)")
        return email_content
    except Exception as e:
        logger.error(f"Error reading email from S3: {str(e)}")
        return None

def parse_email(email_content):
    """Parse email content and extract components"""
    try:
        # Parse the email
        msg = email.message_from_bytes(email_content)
        
        parsed_data = {
            'subject': msg.get('Subject', ''),
            'from': msg.get('From', ''),
            'to': msg.get('To', ''),
            'date': msg.get('Date', ''),
            'body_text': '',
            'body_html': '',
            'attachments': [],
            'headers': dict(msg.items())
        }
        
        # Extract body and attachments
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))
                
                # Extract body
                if content_type == "text/plain" and "attachment" not in content_disposition:
                    body = part.get_payload(decode=True)
                    if body:
                        parsed_data['body_text'] = body.decode('utf-8', errors='ignore')
                
                elif content_type == "text/html" and "attachment" not in content_disposition:
                    body = part.get_payload(decode=True)
                    if body:
                        parsed_data['body_html'] = body.decode('utf-8', errors='ignore')
                
                # Extract attachments
                elif "attachment" in content_disposition:
                    filename = part.get_filename()
                    if filename:
                        attachment_data = part.get_payload(decode=True)
                        if attachment_data:
                            parsed_data['attachments'].append({
                                'filename': filename,
                                'content_type': content_type,
                                'size': len(attachment_data),
                                'content': base64.b64encode(attachment_data).decode('utf-8')
                            })
        else:
            # Non-multipart message
            body = msg.get_payload(decode=True)
            if body:
                content_type = msg.get_content_type()
                if content_type == "text/html":
                    parsed_data['body_html'] = body.decode('utf-8', errors='ignore')
                else:
                    parsed_data['body_text'] = body.decode('utf-8', errors='ignore')
        
        logger.info(f"Successfully parsed email - Subject: {parsed_data['subject']}")
        return parsed_data
        
    except Exception as e:
        logger.error(f"Error parsing email: {str(e)}")
        return {
            'subject': 'Error parsing email',
            'body_text': 'Could not parse email content',
            'body_html': '',
            'attachments': [],
            'headers': {}
        }

def send_webhook_to_frappe(payload):
    """Send webhook to Frappe application"""
    try:
        webhook_url = f"{FRAPPE_BASE_URL}{FRAPPE_WEBHOOK_ENDPOINT}"
        
        # Prepare headers
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        # Add authentication if configured
        if FRAPPE_API_KEY and FRAPPE_API_SECRET:
            headers['Authorization'] = f'token {FRAPPE_API_KEY}:{FRAPPE_API_SECRET}'
        
        # Send POST request
        logger.info(f"Sending webhook to: {webhook_url}")
        logger.info(f"Payload size: {len(json.dumps(payload))} characters")
        
        response = http.request(
            'POST',
            webhook_url,
            body=json.dumps(payload).encode('utf-8'),
            headers=headers,
            timeout=30.0
        )
        
        logger.info(f"Webhook response - Status: {response.status}, Data: {response.data.decode()}")
        
        if response.status == 200:
            logger.info("Webhook sent successfully")
        else:
            logger.warning(f"Webhook returned non-200 status: {response.status}")
            
    except Exception as e:
        logger.error(f"Error sending webhook to Frappe: {str(e)}")
        # Don't raise exception - we don't want to retry failed webhooks
        # You might want to send to DLQ or another notification system