// Enhanced CommunicationComposer with draft functionality
frappe.provide('force_trans_customization.communication_draft');

force_trans_customization.communication_draft = {
    init() {
        this.setup_draft_functionality();
    },

    setup_draft_functionality() {
        // Remove auto-save from content field
        const original_get_fields = frappe.views.CommunicationComposer.prototype.get_fields;
        frappe.views.CommunicationComposer.prototype.get_fields = function() {
            let fields = original_get_fields.call(this);
            // Remove onchange from content field
            fields = fields.map(field => {
                if (field.fieldname === "content" && field.onchange) {
                    delete field.onchange;
                }
                return field;
            });
            return fields;
        };

        // Add Save As Draft button after dialog is created
        const original_make = frappe.views.CommunicationComposer.prototype.make;
        frappe.views.CommunicationComposer.prototype.make = function() {
            original_make.call(this);
            // Add Save As Draft button to dialog footer
            const me = this;
            const $footer = $(this.dialog.$wrapper).find('.modal-footer');
            if ($footer.find('.save-as-draft-btn').length === 0) {
                const $btn = $('<button class="btn btn-default save-as-draft-btn" style="margin-right: 8px;">' + __("Save As Draft") + '</button>');
                $btn.insertBefore($footer.find('.btn-primary, .btn-secondary').first());
                $btn.on('click', function() {
                    me.save_as_draft();
                });
            }
        };

        // Override the original save_as_draft method to show a message
        frappe.views.CommunicationComposer.prototype.save_as_draft = function() {
            if (this.dialog && this.frm) {
                let form_values = this.dialog.get_values();
                // Save to server-side draft
                frappe.call({
                    method: "force_trans_customization.api.email_draft.save_draft",
                    args: {
                        doctype: this.frm.doctype,
                        docname: this.frm.docname,
                        subject: form_values.subject,
                        content: form_values.content,
                        recipients: form_values.recipients,
                        cc: form_values.cc,
                        bcc: form_values.bcc,
                        sender: form_values.sender,
                        email_template: form_values.email_template
                    },
                    callback: (r) => {
                        if (r.message && r.message.success) {
                            frappe.show_alert(__("Draft saved"), 3);
                            // Refresh timeline to show draft
                            if (this.frm && this.frm.timeline) {
                                this.frm.timeline.refresh();
                            }
                        } else {
                            frappe.msgprint({
                                title: __("Error"),
                                message: r.message ? r.message.message : __("Error saving draft"),
                                indicator: "red"
                            });
                        }
                    }
                });
            }
        };

        // Override the original delete_saved_draft method
        const original_delete_saved_draft = frappe.views.CommunicationComposer.prototype.delete_saved_draft;
        frappe.views.CommunicationComposer.prototype.delete_saved_draft = function() {
            if (this.dialog && this.frm) {
                // Get the current draft
                frappe.call({
                    method: "force_trans_customization.api.email_draft.get_drafts",
                    args: {
                        doctype: this.frm.doctype,
                        docname: this.frm.docname
                    },
                    callback: (r) => {
                        if (r.message && r.message.length > 0) {
                            // Delete the first draft (most recent)
                            const draft_name = r.message[0].name;
                            frappe.call({
                                method: "force_trans_customization.api.email_draft.delete_draft",
                                args: {
                                    draft_name: draft_name
                                },
                                callback: (delete_r) => {
                                    if (delete_r.message && delete_r.message.success) {
                                        frappe.show_alert(__("Draft deleted"), 3);
                                        // Refresh timeline
                                        if (this.frm && this.frm.timeline) {
                                            this.frm.timeline.refresh();
                                        }
                                    }
                                }
                            });
                        }
                    }
                });
            }
        };
    },

    // Add draft functionality to timeline
    add_draft_to_timeline(draft_data) {
        const timeline_item = $(`
            <div class="timeline-item" data-draft-name="${draft_data.name}">
                <div class="timeline-badge">
                    <i class="fa fa-edit text-warning"></i>
                </div>
                <div class="timeline-content">
                    <div class="timeline-heading">
                        <span class="text-muted">${__("Draft")}</span>
                        <span class="pull-right text-muted">
                            ${frappe.datetime.global_date_format(draft_data.modified)}
                        </span>
                    </div>
                    <div class="timeline-body">
                        <div class="draft-subject">
                            <strong>${draft_data.subject || __("No Subject")}</strong>
                        </div>
                        <div class="draft-recipients text-muted">
                            ${__("To")}: ${draft_data.recipients || __("No recipients")}
                        </div>
                        <div class="draft-content">
                            ${draft_data.content ? frappe.utils.strip_html_tags(draft_data.content).substring(0, 100) + "..." : __("No content")}
                        </div>
                        <div class="draft-actions mt-2">
                            <button class="btn btn-xs btn-primary continue-draft" data-draft-name="${draft_data.name}">
                                ${__("Continue Editing")}
                            </button>
                            <button class="btn btn-xs btn-success send-draft" data-draft-name="${draft_data.name}">
                                ${__("Send")}
                            </button>
                            <button class="btn btn-xs btn-danger delete-draft" data-draft-name="${draft_data.name}">
                                ${__("Delete")}
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `);

        // Add event handlers
        timeline_item.find('.continue-draft').on('click', function() {
            const draft_name = $(this).data('draft-name');
            force_trans_customization.communication_draft.continue_editing_draft(draft_name);
        });

        timeline_item.find('.send-draft').on('click', function() {
            const draft_name = $(this).data('draft-name');
            force_trans_customization.communication_draft.send_draft(draft_name);
        });

        timeline_item.find('.delete-draft').on('click', function() {
            const draft_name = $(this).data('draft-name');
            force_trans_customization.communication_draft.delete_draft(draft_name);
        });

        return timeline_item;
    },

    continue_editing_draft(draft_name) {
        frappe.call({
            method: "force_trans_customization.api.email_draft.continue_editing_draft",
            args: {
                draft_name: draft_name
            },
            callback: (r) => {
                if (r.message && r.message.success) {
                    const draft = r.message.draft;
                    
                    // Open communication composer with draft data
                    new frappe.views.CommunicationComposer({
                        doc: {
                            doctype: "Communication",
                            name: draft.name
                        },
                        frm: cur_frm,
                        subject: draft.subject,
                        message: draft.content,
                        recipients: draft.recipients,
                        cc: draft.cc,
                        bcc: draft.bcc,
                        sender: draft.sender,
                        email_template: draft.email_template,
                        is_draft: true
                    });
                } else {
                    frappe.msgprint({
                        title: __("Error"),
                        message: r.message ? r.message.message : __("Error loading draft"),
                        indicator: "red"
                    });
                }
            }
        });
    },

    send_draft(draft_name) {
        frappe.confirm(
            __("Are you sure you want to send this draft?"),
            () => {
                frappe.call({
                    method: "force_trans_customization.api.email_draft.send_draft",
                    args: {
                        draft_name: draft_name
                    },
                    callback: (r) => {
                        if (r.message && r.message.success) {
                            frappe.show_alert(__("Draft sent successfully"), 3);
                            // Refresh timeline
                            if (cur_frm && cur_frm.timeline) {
                                cur_frm.timeline.refresh();
                            }
                        } else {
                            frappe.msgprint({
                                title: __("Error"),
                                message: r.message ? r.message.message : __("Error sending draft"),
                                indicator: "red"
                            });
                        }
                    }
                });
            }
        );
    },

    delete_draft(draft_name) {
        frappe.confirm(
            __("Are you sure you want to delete this draft?"),
            () => {
                frappe.call({
                    method: "force_trans_customization.api.email_draft.delete_draft",
                    args: {
                        draft_name: draft_name
                    },
                    callback: (r) => {
                        if (r.message && r.message.success) {
                            frappe.show_alert(__("Draft deleted"), 3);
                            // Refresh timeline
                            if (cur_frm && cur_frm.timeline) {
                                cur_frm.timeline.refresh();
                            }
                        } else {
                            frappe.msgprint({
                                title: __("Error"),
                                message: r.message ? r.message.message : __("Error deleting draft"),
                                indicator: "red"
                            });
                        }
                    }
                });
            }
        );
    }
};

// Initialize when page loads
$(function() {
    force_trans_customization.communication_draft.init();
}); 