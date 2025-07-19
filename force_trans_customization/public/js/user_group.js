// Custom User Group Form Handler
// Handles email validation and processing for custom_associated_email field

frappe.ui.form.on('User Group', {
    refresh: function(frm) {
        // Add validation to the custom_associated_email field on blur (tab out)
        if (frm.fields_dict.custom_associated_email) {
            frm.fields_dict.custom_associated_email.$input.on('blur', function() {
                validateAndFormatEmails(frm);
            });
        }
    },
    
    before_save: function(frm) {
        // Validate emails before saving
        return validateAndFormatEmails(frm);
    }
});

function validateAndFormatEmails(frm) {
    const emailField = frm.fields_dict.custom_associated_email;
    if (!emailField) return true;
    
    let emailValue = emailField.get_value() || '';
    if (!emailValue.trim()) return true;
    
    // Split by comma and clean up
    let emails = emailValue.split(',').map(email => email.trim()).filter(email => email);
    
    let validEmails = [];
    let invalidEmails = [];
    
    // Validate each email
    emails.forEach(email => {
        if (isValidEmail(email)) {
            validEmails.push(email);
        } else {
            invalidEmails.push(email);
        }
    });
    
    // Show error for invalid emails
    if (invalidEmails.length > 0) {
        frappe.msgprint({
            title: __('Invalid Email Addresses'),
            message: __('The following email addresses are invalid:') + '<br><br>' + 
                     invalidEmails.map(email => `<code>${frappe.utils.escape_html(email)}</code>`).join('<br>'),
            indicator: 'red'
        });
        
        // Highlight the field to show there's an error
        emailField.$wrapper.addClass('has-error');
        return false;
    }
    
    // Remove error styling if all emails are valid
    emailField.$wrapper.removeClass('has-error');
    
    // Update the field with properly formatted emails (remove duplicates, sort)
    const formattedEmails = [...new Set(validEmails)].sort().join(', ');
    if (formattedEmails !== emailValue) {
        emailField.set_value(formattedEmails);
    }
    
    return true;
}

function isValidEmail(email) {
    // Basic email validation regex
    const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
    return emailRegex.test(email);
}

// Add helper function to get valid emails
function getValidEmails(emailString) {
    if (!emailString) return [];
    
    return emailString.split(',')
        .map(email => email.trim())
        .filter(email => email && isValidEmail(email));
}


// Export for use in other parts of the app if needed
window.forceTransCustomization = window.forceTransCustomization || {};
window.forceTransCustomization.getValidEmails = getValidEmails;
window.forceTransCustomization.isValidEmail = isValidEmail; 