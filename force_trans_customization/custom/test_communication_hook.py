import frappe
from frappe.test_runner import make_test_records
from force_trans_customization.custom.communication import on_communication_after_insert, is_customer_email

def test_communication_hook():
	"""
	Test the communication hook functionality
	"""
	# Create a test issue
	issue = frappe.get_doc({
		"doctype": "Issue",
		"subject": "Test Issue for Communication Hook",
		"description": "Testing the communication hook",
		"raised_by": "customer@example.com",
		"status": "Open"
	})
	issue.insert()
	
	# Create a test communication (outgoing email to customer)
	communication = frappe.get_doc({
		"doctype": "Communication",
		"communication_type": "Communication",
		"communication_medium": "Email",
		"sent_or_received": "Sent",
		"subject": "Re: Test Issue",
		"content": "This is a test reply to the customer",
		"recipients": "customer@example.com",
		"sender": "support@company.com",
		"reference_doctype": "Issue",
		"reference_name": issue.name
	})
	
	# Test the hook function directly
	on_communication_after_insert(communication, "after_insert")
	
	# Reload the issue to check if status was updated
	issue.reload()
	
	# Verify the status was updated
	assert issue.status == "Waiting on Customer", f"Expected status 'Waiting on Customer', got '{issue.status}'"
	
	# Clean up
	issue.delete()
	communication.delete()
	
	print("✅ Communication hook test passed!")

def test_is_customer_email():
	"""
	Test the is_customer_email function
	"""
	# Create a test issue
	issue = frappe.get_doc({
		"doctype": "Issue",
		"subject": "Test Issue for Email Detection",
		"description": "Testing email detection",
		"raised_by": "customer@example.com",
		"status": "Open"
	})
	issue.insert()
	
	# Test communication to customer email
	communication_to_customer = frappe.get_doc({
		"doctype": "Communication",
		"communication_type": "Communication",
		"communication_medium": "Email",
		"sent_or_received": "Sent",
		"subject": "Test",
		"recipients": "customer@example.com",
		"reference_doctype": "Issue",
		"reference_name": issue.name
	})
	
	# Test communication to internal email
	communication_to_internal = frappe.get_doc({
		"doctype": "Communication",
		"communication_type": "Communication",
		"communication_medium": "Email",
		"sent_or_received": "Sent",
		"subject": "Test",
		"recipients": "internal@company.com",
		"reference_doctype": "Issue",
		"reference_name": issue.name
	})
	
	# Test the function
	assert is_customer_email(communication_to_customer) == True, "Should detect customer email"
	assert is_customer_email(communication_to_internal) == False, "Should not detect internal email"
	
	# Clean up
	issue.delete()
	
	print("✅ Email detection test passed!")

if __name__ == "__main__":
	test_is_customer_email()
	test_communication_hook() 