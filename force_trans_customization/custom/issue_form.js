// Custom Issue Form Script - Hide Left Sidebar
// Uses immediate CSS injection + standard ERPNext classes to prevent sidebar flash

// Immediate CSS injection to prevent sidebar flash
(function() {
	// Add CSS styles immediately when script loads
	const style = document.createElement('style');
	style.textContent = `
		/* Hide form sidebar immediately for Issue forms */
		body[data-route^="Form/Issue"] .form-sidebar,
		body[data-route^="Form/Issue"] .layout-side-section {
			display: none !important;
		}
		
		/* Ensure main section takes full width */
		body[data-route^="Form/Issue"] .layout-main-section {
			width: 100% !important;
			margin-right: 0 !important;
		}
	`;
	document.head.appendChild(style);
})();

frappe.ui.form.on("Issue", {
	onload: function(frm) {
		// Hide immediately on load to prevent sidebar flash
		$(document.body).addClass("hide-form-sidebar");
		
		// Additional immediate hiding
		if (frm.page && frm.page.sidebar) {
			frm.page.sidebar.hide();
			frm.page.sidebar.addClass("hide-sidebar");
		}
		
		// Hide sidebar element directly
		$('.form-sidebar').hide();
		$('.layout-side-section').hide();

		
		initialize_roleprofile_based_features(frm);
	},
	
	refresh: function(frm) {
		// Add CSS class to hide form sidebar (standard ERPNext approach)
		$(document.body).addClass("hide-form-sidebar");
		
		// Ensure sidebar wrapper is hidden
		if (frm.page && frm.page.sidebar) {
			frm.page.sidebar.addClass("hide-sidebar");
			frm.page.sidebar.hide();
		}
		
		// Hide specific sidebar sections to ensure they stay hidden
		if (frm.sidebar && frm.sidebar.sidebar) {
			frm.sidebar.sidebar.hide();
		}

		// Add "Assign to Me" button
		add_assign_to_me_button(frm);
	}
}); 

// Function to initialize roleprofile-based features
function initialize_roleprofile_based_features(frm) {
	// Get current user's role profile information
	frappe.call({
		method: "force_trans_customization.api.user_utils.get_current_user_role_profile",
		callback: function(r) {
			if (r.message) {
				frm._user_profile_info = r.message;
				setup_roleprofile_based_ui(frm);
			}
		}
	});
}

// Function to setup role-based UI elements
function setup_roleprofile_based_ui(frm) {
	if (!frm._user_profile_info) return;

	const readonly_roles = [
		"Accounting Team",
		"Safety Team",
		"CSM Team",
		"Tracking Team"
	];

	const user_role_profile = frm._user_profile_info.role_profile_name;

	const is_readonly_profile = readonly_roles.includes(user_role_profile);

	if (is_readonly_profile) {
		// Make fields read-only for specific role profiles
		frm.set_df_property('custom_users_assigned', 'read_only', 1);
		frm.set_df_property('custom_assigned_csm_team', 'read_only', 1);

		// Add helper descriptions
		if (frm.fields_dict.custom_users_assigned) {
			frm.set_df_property('custom_users_assigned', 'description',
				`This field is read-only for ${user_role_profile}.`);
		}

		if (frm.fields_dict.custom_assigned_csm_team) {
			frm.set_df_property('custom_assigned_csm_team', 'description',
				`User Group editing is restricted for ${user_role_profile}.`);
		}
	} else {
		// Allow editing for other roles
		frm.set_df_property('custom_users_assigned', 'read_only', 0);
		frm.set_df_property('custom_users_assigned', 'description', '');
		frm.set_df_property('custom_assigned_csm_team', 'read_only', 0);
		frm.set_df_property('custom_assigned_csm_team', 'description', '');
	}
}

// Function to add "Assign to Me" or "Unassign from Me" button
function add_assign_to_me_button(frm) {
	const current_user = frappe.session.user;
	
	// Remove existing buttons if they exist
	frm.remove_custom_button('Assign to Me');
	frm.remove_custom_button('Unassign from Me');
	
	// Check if current user is already assigned
	const existing_assignment = frm.doc.custom_users_assigned?.find(
		row => row.user_assigned === current_user
	);
	
	if (existing_assignment) {
		// Show "Unassign from Me" button
		frm.add_custom_button('Unassign from Me', function() {
			unassign_current_user_from_issue(frm);
		}).addClass('btn-danger');
	} else {
		// Show "Assign to Me" button
		frm.add_custom_button('Assign to Me', function() {
			assign_current_user_to_issue(frm);
		}).addClass('btn-primary');
	}
}

// Function to assign current user to the issue
function assign_current_user_to_issue(frm) {
	const current_user = frappe.session.user;
	
	// Get user's team information
	frappe.call({
		method: "force_trans_customization.api.user_utils.get_current_user_role_profile",
		callback: function(r) {
			if (r.message) {
				const role_profile = r.message.role_profile_name;
				let team_name = '';
				
				// Map role profile to team name
				switch(role_profile) {
					case 'Accounting Team':
						team_name = 'Accounting';
						break;
					case 'Safety Team':
						team_name = 'Safety';
						break;
					case 'CSM Team':
						team_name = 'CSM';
						break;
					case 'Tracking Team':
						team_name = 'Tracking';
						break;
					default:
						team_name = role_profile || 'General';
				}
				
				// Add new row to the custom_users_assigned table
				const new_row = frm.add_child('custom_users_assigned');
				new_row.user_assigned = current_user;
				new_row.team = team_name;
				new_row.assigned_date = frappe.datetime.now_datetime();
				
				// Refresh the field to show the new row
				frm.refresh_field('custom_users_assigned');
				
				// Save the form immediately
				frm.save().then(() => {
					// Update button to show "Unassign from Me" after successful save
					add_assign_to_me_button(frm);
					
					// Show success message
					frappe.msgprint({
						title: __('Success'),
						message: __('You have been successfully assigned to this issue.'),
						indicator: 'green'
					});
				}).catch((error) => {
					// Handle save error
					frappe.msgprint({
						title: __('Error'),
						message: __('Failed to save assignment. Please try again or save manually.'),
						indicator: 'red'
					});
					console.error('Assignment save error:', error);
				});
			} else {
				// Fallback if role profile API fails
				const new_row = frm.add_child('custom_users_assigned');
				new_row.user_assigned = current_user;
				new_row.team = 'General';
				new_row.assigned_date = frappe.datetime.now_datetime();
				
				frm.refresh_field('custom_users_assigned');
				
				// Save the form immediately
				frm.save().then(() => {
					// Update button to show "Unassign from Me" after successful save
					add_assign_to_me_button(frm);
					
					frappe.msgprint({
						title: __('Success'),
						message: __('You have been assigned to this issue with default team.'),
						indicator: 'green'
					});
				}).catch((error) => {
					// Handle save error
					frappe.msgprint({
						title: __('Error'),
						message: __('Failed to save assignment. Please try again or save manually.'),
						indicator: 'red'
					});
					console.error('Assignment save error:', error);
				});
			}
		}
	});
}

function unassign_current_user_from_issue(frm) {
    const current_user = frappe.session.user;
    
    // Find the rows to remove
    const rows_to_remove = [];
    frm.doc.custom_users_assigned?.forEach((row) => {
        if (row.user_assigned === current_user) {
            rows_to_remove.push(row);
        }
    });
    
    if (rows_to_remove.length === 0) {
        frappe.msgprint({
            title: __('Not Assigned'),
            message: __('You are not currently assigned to this issue.'),
            indicator: 'orange'
        });
        return;
    }
    
    // Store all rows except the ones to remove
    const remaining_rows = frm.doc.custom_users_assigned.filter(row => 
        row.user_assigned !== current_user
    );
    
    // Clear the entire child table
    frappe.model.clear_table(frm.doc, 'custom_users_assigned');
    
    // Re-add all remaining rows
    remaining_rows.forEach((row) => {
        const new_row = frm.add_child('custom_users_assigned');
        new_row.user_assigned = row.user_assigned;
        new_row.team = row.team;
        new_row.assigned_date = row.assigned_date;
    });
    
    // Force the document to be marked as dirty/changed
    frm.dirty();
    
    // Refresh the field to show the updated table
    frm.refresh_field('custom_users_assigned');
    
    // Save the form
    frm.save().then(() => {
        add_assign_to_me_button(frm);
        frappe.msgprint({
            title: __('Success'),
            message: __('You have been successfully unassigned from this issue.'),
            indicator: 'green'
        });
    }).catch((error) => {
        frappe.msgprint({
            title: __('Error'),
            message: __('Failed to save unassignment. Please try again or save manually.'),
            indicator: 'red'
        });
        console.error('Unassignment save error:', error);
    });
}