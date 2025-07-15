# In your_app/tasks.py
import frappe
import time

def process_email_queue_frequent():
    print('----------------------------------------------- test for email -----------------------------------')
    print(f'process_email_queue_frequent called at {frappe.utils.now()}')
    
    for i in range(6):  # Run 6 times in 60 seconds
        # Your email processing logic here
        try:
            from frappe.email.queue import flush
            flush()
            print(f'Email queue flushed - iteration {i+1}')
        except Exception as e:
            print(f'Error flushing email queue: {str(e)}')
        
        if i < 5:  # Don't sleep on the last iteration
            time.sleep(10)