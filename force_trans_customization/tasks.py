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

def pull_email_accounts():
    """Pull emails from all configured email accounts every minute"""
    try:
        print(f'pull_email_accounts called at {frappe.utils.now()}')
        from frappe.email.doctype.email_account.email_account import pull
        pull()
        print('Email accounts pulled successfully')
    except Exception as e:
        frappe.log_error(f'Error pulling email accounts: {str(e)}', 'Email Account Pull Error')
        print(f'Error pulling email accounts: {str(e)}')