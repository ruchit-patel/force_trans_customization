// Custom Issue Form Script - Hide Left Sidebar
// Uses immediate CSS injection + standard ERPNext classes to prevent sidebar flash

// Immediate CSS injection to prevent sidebar flash


frappe.ui.form.on("Issue", {
	onload: function(frm) {
		inject_issue_labels_in_email_dialog(frm);
		initialize_roleprofile_based_features(frm);
	},
	
	refresh: function(frm) {
		const collection = document.getElementsByClassName('form-assignments');
		collection[0].hidden=true;

		const collection3 = document.getElementsByClassName('form-shared');
		collection3[0].hidden=true;
		// Add "Assign to Me" button
		add_assign_to_me_button(frm);
	},

	    // Remove add_edit_draft_buttons logic
    // Instead, use timeline_refresh event
    timeline_refresh: function(frm) {
        // Add edit buttons for draft communications
        if (!frm.timeline.wrapper.data("edit-draft-event-attached")) {
            // Attach event handler for edit draft buttons
            frm.timeline.wrapper.on("click", ".btn-edit-draft", (e) => {
                e.preventDefault();
                e.stopPropagation();
                let comm_name = e.currentTarget.closest(".timeline-item").getAttribute("data-name");
                if (comm_name) {
                    frappe.call({
                        method: "frappe.client.get",
                        args: {
                            doctype: "Communication",
                            name: comm_name
                        },
                        callback: function(r) {
                            if (r.message) {
                                force_trans_customization.communication_draft.open_composer_with_draft(r.message);
                            } else {
                                frappe.msgprint({
                                    title: __("Error"),
                                    message: __("Could not load draft communication"),
                                    indicator: "red"
                                });
                            }
                        }
                    });
                }
            });

			frm.timeline.wrapper.on("click", ".btn-delete-draft", (e) => {
                e.preventDefault();
                e.stopPropagation();
                let comm_name = e.currentTarget.closest(".timeline-item").getAttribute("data-name");
                if (comm_name) {
                    // Call the delete draft function from communication_draft.js
                    force_trans_customization.communication_draft.delete_draft(comm_name);
                }
            });

            frm.timeline.wrapper.data("edit-draft-event-attached", true);
        }

        // Add edit buttons to draft communications
        add_edit_delete_buttons_to_drafts(frm);

		patchTimelineInstance(frm);
    }
}); 


// --- Timeline patch logic (Show Only Emails switch) ---
function patchTimelineInstance(frm) {
	if (frm.timeline && !frm.timeline.__force_trans_email_switch_patched) {
		frm.timeline.__force_trans_email_switch_patched = true;
		
		// Save originals
		const origSetup = frm.timeline.setup_activity_toggle.bind(frm.timeline);
		const origPrepare = frm.timeline.prepare_timeline_contents.bind(frm.timeline);
		
		// Patch setup_activity_toggle to add our switch
		frm.timeline.setup_activity_toggle = function() {
			//origSetup();
			const me = this;
			
			// Only add switch if not already present
			if (this.timeline_wrapper.find('.show-emails-only-switch').length > 0) {
				return;
			}
			
			// Call original setup to ensure all elements are created
			//origSetup();
			
			const $activityTitle = this.timeline_wrapper.find(".timeline-item.activity-title").first();
			if ($activityTitle.length === 0) return;
			
			// Create "Show Only Emails" switch
			const $switchWrapper = $(`
				<div class="d-flex align-items-center show-emails-only-switch">
					<span style="color: var(--text-light); margin:0px 6px;">Show Only Emails</span>
					<label class="switch">
						<input type="checkbox" ${me.only_emails_switch ? "checked" : ""}>
						<span class="slider round"></span>
					</label>
				</div>
			`);
			
			$switchWrapper.find("input[type=checkbox]").on("change", function() {
				me.only_emails_switch = this.checked;
				me.render_timeline_items();
			});
			
			// Insert before the "Show all activity" switch if it exists
			const $showAllActivity = $activityTitle.find('.show-all-activity');
			if ($showAllActivity.length > 0) {
				$showAllActivity.before($switchWrapper);
			} else {
				// Fallback: append to activity title	
				$activityTitle.append($switchWrapper);
			}
		};
		
		// Patch prepare_timeline_contents to filter for emails only
		frm.timeline.prepare_timeline_contents = function() {
			if (this.only_emails_switch) {
				this.timeline_items = [];
				this.timeline_items.push(...this.get_email_communication_timeline_contents());
				return;
			}
			origPrepare();
		};
		
		// Re-render timeline only if setup function exists and hasn't been called yet
		setTimeout(() => {
			if (frm.timeline && frm.timeline.timeline_wrapper.find('.show-emails-only-switch').length === 0) {
				frm.timeline.setup_activity_toggle();
			}
		}, 500);
	} else if (!frm.timeline) {
		setTimeout(patchTimelineInstance, 200);
	}
}


function  add_edit_delete_buttons_to_drafts(frm) {
	if (!frm.timeline || !frm.timeline.doc_info || !frm.timeline.doc_info.communications) {
		return;
	}

	// Find draft communications from doc_info
	const draft_communications = frm.timeline.doc_info.communications.filter(comm => 
		comm._doc_status === "Draft" || comm.delivery_status === "Draft"
	);

	draft_communications.forEach(comm => {
		// Find the timeline item for this communication
		const timeline_item = frm.timeline.wrapper.find(`.timeline-item[data-name="${comm.name}"]`);
		
		if (timeline_item.length > 0 && timeline_item.find('.btn-edit-draft').length === 0) {
				let edit_draft_btn = $(`
					<a class="action-btn btn-edit-draft" title="${__("Edit Draft")}">
						${frappe.utils.icon("edit", "sm")}
					</a>
				`);

			let delete_draft_btn = $(`
				<a class="action-btn btn-delete-draft" title="${__("Delete Draft")}">
					${frappe.utils.icon("delete", "sm")}
				</a>
			`);

			// Try to find the actions area
			let $actions = timeline_item.find(".actions");
			if ($actions.length === 0) {
				$actions = timeline_item.find(".timeline-actions");
			}
			if ($actions.length === 0) {
				$actions = timeline_item.find(".timeline-message-box .actions");
			}
			
			if ($actions.length > 0) {
				$actions.prepend(edit_draft_btn);
				$actions.prepend(delete_draft_btn);
			} else {
				// Fallback: add to the timeline item itself
				timeline_item.prepend(edit_draft_btn);
				timeline_item.prepend(delete_draft_btn);
			}
		}
	});
}

// Function to initialize roleprofile-based features
function initialize_roleprofile_based_features(frm) {
	// Get current user's role profile information
	frappe.call({
		method: "force_trans_customization.utils.user_utils.get_current_user_role_profile",
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
	
	// Check if current user is already assigned using ERPNext's assignment system
	check_user_assignment(frm, current_user).then((is_assigned) => {
		if (is_assigned) {
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
	});
}

// Function to assign current user to the issue using BOTH custom field AND ERPNext's native assignment
function assign_current_user_to_issue(frm) {
	const current_user = frappe.session.user;
	
	// First, get user's team information for custom field
	frappe.call({
		method: "force_trans_customization.utils.user_utils.get_current_user_role_profile",
		callback: function(r) {
			let team_name = 'General';
			
			if (r.message) {
				const role_profile = r.message.role_profile_name;
				
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
			}
			
			// Check if someone from the same team is already assigned
			const existing_team_assignment = frm.doc.custom_users_assigned?.find(
				row => row.team === team_name && row.user_assigned !== current_user
			);
			
			if (existing_team_assignment) {
				// Show takeover confirmation dialog
				// frappe.confirm(
				// 	__(`A team member from ${team_name} team is already working on this issue: <strong>${existing_team_assignment.user_assigned}</strong><br><br>Do you want to take over this assignment?`),
				// 	function() {
				// 		// User confirmed takeover - remove existing team member and assign to current user
				// 		perform_team_takeover(frm, current_user, team_name, existing_team_assignment.user_assigned);
				// 	},
				// 	function() {
				// 		// User cancelled - do nothing
						
				// 	}
				//);
				frappe.msgprint({
							title: __('Team Member Already Assigned'),
							message: __('This issue is already being handled by a member of your team and cannot be reassigned to you. Please contact the Administrator if you wish to take over this issue.'),
							indicator: 'red'
						});
			} else {
				// No team conflict - proceed with normal assignment
				perform_normal_assignment(frm, current_user, team_name);
			}
		}
	});
}

// Function to perform normal assignment (no team conflict)
function perform_normal_assignment(frm, current_user, team_name) {
	// Step 1: Add to custom multi-select field
	const new_row = frm.add_child('custom_users_assigned');
	new_row.user_assigned = current_user;
	new_row.team = team_name;
	new_row.assigned_date = frappe.datetime.now_datetime();
	
	// Check if this is the first assignment and update status if needed
	const total_assignments = frm.doc.custom_users_assigned.length;
	if (total_assignments === 1 && frm.doc.status === 'New') {
		frm.set_value('status', 'In Review');
	}
	
	// Refresh the custom field
	frm.refresh_field('custom_users_assigned');
	
	// Step 2: Add to ERPNext's native assignment system
	frappe.call({
		method: "frappe.desk.form.assign_to.add",
		args: {
			doctype: frm.doc.doctype,
			name: frm.doc.name,
			assign_to: [current_user],
			description: `Self-assigned to ${frm.doc.subject || frm.doc.name} (Team: ${team_name})`
		},
		callback: function(assign_r) {
			if (!assign_r.exc) {
				// Step 3: Save the form to persist custom field changes
				frm.save().then(() => {
					// Update button to show "Unassign from Me"
					add_assign_to_me_button(frm);
					
					// Show success message
					let message = `You have been successfully assigned to this issue.<br>Team: ${team_name}`;
					if (total_assignments === 1) {
						message += '<br><br>Issue status has been updated to "In Review".';
					}
					
					frappe.msgprint({
						title: __('Success'),
						message: __(message),
						indicator: 'green'
					});
					
					// Refresh the assignment area in sidebar
					if (frm.assign_to && frm.assign_to.refresh) {
						frm.assign_to.refresh();
					}
				}).catch((save_error) => {
					// If form save fails, show error but assignment still worked
					frappe.msgprint({
						title: __('Partial Success'),
						message: __('ERPNext assignment succeeded, but failed to save custom field. Please save manually.'),
						indicator: 'orange'
					});
					console.error('Form save error:', save_error);
				});
			} else {
				// ERPNext assignment failed, remove the custom field entry
				const index = frm.doc.custom_users_assigned.findIndex(row => row.user_assigned === current_user);
				if (index > -1) {
					frm.doc.custom_users_assigned.splice(index, 1);
					frm.refresh_field('custom_users_assigned');
				}
				
				// Revert status change if assignment failed
				if (total_assignments === 1) {
					frm.set_value('status', 'New');
				}
				
				frappe.msgprint({
					title: __('Error'),
					message: __('Failed to assign. Please try again.'),
					indicator: 'red'
				});
				console.error('Assignment error:', assign_r.exc);
			}
		}
	});
}

// Function to perform team takeover (remove previous team member and assign new user)
function perform_team_takeover(frm, new_user, team_name, previous_user) {
	// Step 1: Remove previous team member from custom field
	const remaining_rows = frm.doc.custom_users_assigned.filter(row => 
		!(row.team === team_name && row.user_assigned === previous_user)
	);
	
	// Clear and rebuild the custom field table
	frappe.model.clear_table(frm.doc, 'custom_users_assigned');
	
	remaining_rows.forEach((row) => {
		const new_row = frm.add_child('custom_users_assigned');
		new_row.user_assigned = row.user_assigned;
		new_row.team = row.team;
		new_row.assigned_date = row.assigned_date;
	});
	
	// Step 2: Add new user to custom field
	const new_row = frm.add_child('custom_users_assigned');
	new_row.user_assigned = new_user;
	new_row.team = team_name;
	new_row.assigned_date = frappe.datetime.now_datetime();
	
	// Check if this is the first assignment and update status if needed
	const total_assignments = frm.doc.custom_users_assigned.length;
	if (total_assignments === 1 && frm.doc.status === 'New') {
		frm.set_value('status', 'In Review');
	}
	
	// Force the document to be marked as dirty/changed
	frm.dirty();
	
	// Refresh the custom field
	frm.refresh_field('custom_users_assigned');
	
	// Step 3: Remove previous user from ERPNext assignment
	frappe.call({
		method: "frappe.desk.form.assign_to.remove",
		args: {
			doctype: frm.doc.doctype,
			name: frm.doc.name,
			assign_to: previous_user
		},
		callback: function(remove_r) {
			// Step 4: Add new user to ERPNext assignment (regardless of removal success)
			frappe.call({
				method: "frappe.desk.form.assign_to.add",
				args: {
					doctype: frm.doc.doctype,
					name: frm.doc.name,
					assign_to: [new_user],
					description: `Takeover assignment from ${previous_user} (Team: ${team_name})`
				},
				callback: function(assign_r) {
					// Step 5: Save the form
					frm.save().then(() => {
						// Update button to show "Unassign from Me"
						add_assign_to_me_button(frm);
						
						// Show takeover success message
						let message = `Assignment takeover completed!<br>`;
						message += `<strong>Previous:</strong> ${previous_user}<br>`;
						message += `<strong>New:</strong> ${new_user}<br>`;
						message += `<strong>Team:</strong> ${team_name}`;
						
						// Add status change notification if this was the first assignment
						if (total_assignments === 1) {
							message += `<br><br>Issue status has been updated to "In Review".`;
						}
						
						if (!remove_r.exc && !assign_r.exc) {
							message += `<br>`;
							frappe.msgprint({
								title: __('Takeover Successful'),
								message: __(message),
								indicator: 'green'
							});
						} else if (!assign_r.exc) {
							message += `<br><br>New assignment successful. Previous ERPNext assignment removal may have failed.`;
							frappe.msgprint({
								title: __('Partial Takeover'),
								message: __(message),
								indicator: 'orange'
							});
						} else {
							message += `<br><br>Custom field updated, but ERPNext assignment failed.`;
							frappe.msgprint({
								title: __('Partial Takeover'),
								message: __(message),
								indicator: 'orange'
							});
						}
						
						// Refresh the assignment area in sidebar
						if (frm.assign_to && frm.assign_to.refresh) {
							frm.assign_to.refresh();
						}
					}).catch((save_error) => {
						frappe.msgprint({
							title: __('Error'),
							message: __('Takeover completed but failed to save form. Please save manually.'),
							indicator: 'red'
						});
						console.error('Takeover save error:', save_error);
					});
				}
			});
		}
	});
}

// Function to unassign current user from the issue using BOTH custom field AND ERPNext's native assignment
function unassign_current_user_from_issue(frm) {
    const current_user = frappe.session.user;
    
    // Check if user is assigned in custom field
    const existing_assignments = frm.doc.custom_users_assigned?.filter(
        row => row.user_assigned === current_user
    );
    
    if (!existing_assignments || existing_assignments.length === 0) {
        frappe.msgprint({
            title: __('Not Assigned'),
            message: __('You are not currently assigned to this issue in the custom tracking.'),
            indicator: 'orange'
        });
        return;
    }
    
    // Step 1: Remove from custom multi-select field
    const remaining_rows = frm.doc.custom_users_assigned.filter(row => 
        row.user_assigned !== current_user
    );
    
    // Clear and rebuild the custom field table
    frappe.model.clear_table(frm.doc, 'custom_users_assigned');
    
    remaining_rows.forEach((row) => {
        const new_row = frm.add_child('custom_users_assigned');
        new_row.user_assigned = row.user_assigned;
        new_row.team = row.team;
        new_row.assigned_date = row.assigned_date;
    });
    
    // Check if no assignments remain and revert status to "New" if needed
    const remaining_assignments = frm.doc.custom_users_assigned.length;
    if (remaining_assignments === 0 && frm.doc.status === 'In Review') {
        frm.set_value('status', 'New');
    }
    
    // Force the document to be marked as dirty/changed
    frm.dirty();

    // Refresh the custom field
    frm.refresh_field('custom_users_assigned');
    
    // Step 2: Remove from ERPNext's native assignment system
    frappe.call({
        method: "frappe.desk.form.assign_to.remove",
        args: {
            doctype: frm.doc.doctype,
            name: frm.doc.name,
            assign_to: current_user
        },
        callback: function(assign_r) {
            // Step 3: Save the form to persist custom field changes
            frm.save().then(() => {
                // Update button to show "Assign to Me"
                add_assign_to_me_button(frm);
                
                // Show success message based on assignment removal result
                if (!assign_r.exc) {
                    let message = __('You have been successfully unassigned from this issue.');
                    
                    // Add status change notification if no assignments remain
                    if (remaining_assignments === 0) {
                        message += '<br><br>Issue status has been reverted to "New" as no assignments remain.';
                    }
                    
                    frappe.msgprint({
                        title: __('Success'),
                        message: message,
                        indicator: 'green'
                    });
                    
                    // Refresh the assignment area in sidebar
                    if (frm.assign_to && frm.assign_to.refresh) {
                        frm.assign_to.refresh();
                    }
                } else {
                    // ERPNext unassignment failed but custom field was updated
                    let message = __('Custom field updated, but ERPNext assignment removal failed. You may still appear in the assignment panel.');
                    
                    // Add status change notification if no assignments remain
                    if (remaining_assignments === 0) {
                        message += '<br><br>Issue status has been reverted to "New" as no assignments remain.';
                    }
                    
                    frappe.msgprint({
                        title: __('Partial Success'),
                        message: message,
                        indicator: 'orange'
                    });
                    console.error('ERPNext unassignment error:', assign_r.exc);
                }
            }).catch((save_error) => {
                // Form save failed, show error
                frappe.msgprint({
                    title: __('Error'),
                    message: __('Failed to save unassignment. Please save manually.'),
                    indicator: 'red'
                });
                console.error('Form save error:', save_error);
            });
        }
    });
}

// Helper function to check if current user is assigned using BOTH custom field AND ERPNext's assignment system
function check_user_assignment(frm, user) {
	return new Promise((resolve) => {
		// First check custom field (primary source of truth)
		const custom_assignment = frm.doc.custom_users_assigned?.find(
			row => row.user_assigned === user
		);
		
		if (custom_assignment) {
			resolve(true); // User is assigned in custom field
			return;
		}
		
		// If not in custom field, check ERPNext's assignment system as fallback
		frappe.call({
			method: "frappe.client.get_list",
			args: {
				doctype: "ToDo",
				filters: {
					reference_type: frm.doc.doctype,
					reference_name: frm.doc.name,
					allocated_to: user,
					status: ["!=", "Cancelled"]
				},
				fields: ["name"]
			},
			callback: function(r) {
				if (r.message && r.message.length > 0) {
					resolve(true); // User is assigned in ERPNext system
				} else {
					resolve(false); // User is not assigned in either system
				}
			}
		});
	});
}

// --- PATCH: Inject Issue Labels as read-only tags in Email Composer dialog ---
function inject_issue_labels_in_email_dialog(frm) {
    // Patch only once
    if (window.__issue_email_tag_patch_applied) return;
    window.__issue_email_tag_patch_applied = true;

    // Save original CommunicationComposer
    const OriginalComposer = frappe.views.CommunicationComposer;

    frappe.views.CommunicationComposer = class extends OriginalComposer {
        make() {
            super.make();
            // Only for Issue doctype
            if (this.frm && this.frm.doctype === "Issue") {
                // Wait for dialog to be fully rendered
                setTimeout(() => {
                    try {
                        const subjectField = this.dialog.fields_dict.subject;
                        if (!subjectField) return;
                        // Find the subject field wrapper
                        const $subjectWrapper = $(subjectField.wrapper);
                        // Remove any previous tags
                        $subjectWrapper.siblings('.issue-label-tags').remove();
                        // Get tags from _user_tags (default Frappe tags)
                        const tagString = this.frm.doc._user_tags || '';
                        const tags = tagString.split(',').map(t => t.trim()).filter(Boolean);
                        if (!tags.length) return;
                        const tagsHtml = `<div class="issue-label-tags" style="margin: 8px 0 0 0; display: flex; flex-wrap: wrap; gap: 6px;">
                            ${tags.map(tag => {
                                const palette = frappe.get_palette ? frappe.get_palette(tag) : ["#888", "#fff"];
                                const bg = Array.isArray(palette) ? palette[0] : palette;
                                const color = Array.isArray(palette) ? palette[1] : "#fff";
                                const bgStyle = (typeof bg === 'string' && bg.startsWith('--')) ? `var(${bg})` : bg;
                                const colorStyle = (typeof color === 'string' && color.startsWith('--')) ? `var(${color})` : color;
                                return `<span style="background: ${bgStyle}; color: ${colorStyle}; border-radius: 12px; padding: 2px 10px; font-size: 12px; font-weight: 500; display: inline-block;">${frappe.utils.escape_html(tag)}</span>`;
                            }).join('')}
                        </div>`;
                        $subjectWrapper.after(tagsHtml);
                    } catch (e) { console.warn('Issue label tag inject error', e); }
                }, 0);
            }
        }
    };
}