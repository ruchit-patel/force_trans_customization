import frappe
from frappe.test_runner import make_test_records
from force_trans_customization.api.email_draft import save_draft, get_drafts, send_draft, delete_draft

def test_email_draft_functionality():
    """
    Test the email draft functionality
    """
    # Create a test issue
    issue = frappe.get_doc({
        "doctype": "Issue",
        "subject": "Test Issue for Email Drafts",
        "description": "Testing the email draft functionality",
        "raised_by": "test@example.com",
        "status": "Open"
    })
    issue.insert()
    
    # Test saving a draft
    draft_data = {
        "doctype": "Issue",
        "docname": issue.name,
        "subject": "Test Draft Email",
        "content": "This is a test draft email content",
        "recipients": "customer@example.com",
        "cc": "manager@example.com",
        "bcc": "",
        "sender": "support@company.com",
        "email_template": ""
    }
    
    # Save draft
    result = save_draft(**draft_data)
    assert result["success"] == True, f"Expected success=True, got {result}"
    draft_name = result["draft_name"]
    
    # Get drafts
    drafts = get_drafts("Issue", issue.name)
    assert len(drafts) == 1, f"Expected 1 draft, got {len(drafts)}"
    assert drafts[0]["subject"] == "Test Draft Email", f"Expected subject 'Test Draft Email', got {drafts[0]['subject']}"
    
    # Test continue editing draft
    from force_trans_customization.api.email_draft import continue_editing_draft
    edit_result = continue_editing_draft(draft_name)
    assert edit_result["success"] == True, f"Expected success=True, got {edit_result}"
    assert edit_result["draft"]["subject"] == "Test Draft Email", f"Expected subject 'Test Draft Email', got {edit_result['draft']['subject']}"
    
    # Test deleting draft
    delete_result = delete_draft(draft_name)
    assert delete_result["success"] == True, f"Expected success=True, got {delete_result}"
    
    # Verify draft is deleted
    drafts_after_delete = get_drafts("Issue", issue.name)
    assert len(drafts_after_delete) == 0, f"Expected 0 drafts after delete, got {len(drafts_after_delete)}"
    
    # Clean up
    issue.delete()
    
    print("✅ Email draft functionality test passed!")

if __name__ == "__main__":
    test_email_draft_functionality() 