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

        const original_save_as_draft = frappe.views.CommunicationComposer.prototype.save_as_draft;
        frappe.views.CommunicationComposer.prototype.save_as_draft = function() {
            if (this.dialog && this.frm) {
                let form_values = this.dialog.get_values();
                // Use draft_name if present (editing existing draft)
                let draft_name = this.draft_name || (form_values && form_values.draft_name);
                
                console.log("Saving draft with draft_name:", draft_name);
                
                // Call our server-side save method
                frappe.call({
                    method: "force_trans_customization.api.email_draft.save_draft",
                    args: {
                        doctype: this.frm.doctype,
                        docname: this.frm.docname,
                        subject: form_values.subject,
                        recipients: form_values.recipients,
                        content: form_values.content,
                        cc: form_values.cc,
                        bcc: form_values.bcc,
                        sender: form_values.sender,
                        email_template: form_values.email_template,
                        draft_name: draft_name
                    },
                    callback: function(r) {
                        if (r.message && r.message.success) {
                            frappe.show_alert(__("Draft saved"), 3);
                            // Update draft_name for future saves
                            if (r.message.draft_name) {
                                this.draft_name = r.message.draft_name;
                                console.log("Updated draft_name to:", this.draft_name);
                            }
                            // Refresh timeline to show updated draft
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
                    }.bind(this)
                });
                
                // Also call the original method for local storage
                original_save_as_draft.call(this);
            }
        };

        // Override send_action to handle draft emails
        const original_send_action = frappe.views.CommunicationComposer.prototype.send_action;
        frappe.views.CommunicationComposer.prototype.send_action = function() {
            // Check if this is editing a draft
            if (this.draft_name) {
                // This is editing a draft, so update the existing draft and send it
                let form_values = this.dialog.get_values();
                if (!form_values) return;

                const selected_attachments = $.map(
                    $(this.dialog.wrapper).find("[data-file-name]:checked"),
                    function (element) {
                        return $(element).attr("data-file-name");
                    }
                );

                // Call our server-side send draft method
                frappe.call({
                    method: "force_trans_customization.api.email_draft.send_draft",
                    args: {
                        draft_name: this.draft_name,
                        form_values: form_values,
                        selected_attachments: selected_attachments
                    },
                    callback: (r) => {
                        if (r.message && r.message.success) {
                            frappe.show_alert(__("Draft sent successfully"), 3);
                            this.dialog.hide();
                            // Refresh timeline
                            if (this.frm && this.frm.timeline) {
                                this.frm.timeline.refresh();
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
            } else {
                // This is a new email, use the original send action
                original_send_action.call(this);
            }
        };

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

force_trans_customization.communication_draft.open_composer_with_draft = function(draft_doc) {
    // Open the CommunicationComposer dialog with draft_doc's data
    const composer = new frappe.views.CommunicationComposer({
        doc: cur_frm.doc,
        frm: cur_frm,
        subject: draft_doc.subject,
        recipients: draft_doc.recipients,
        message: draft_doc.content, // Use 'message' instead of 'content'
        cc: draft_doc.cc,
        bcc: draft_doc.bcc,
        sender: draft_doc.sender,
        email_template: draft_doc.email_template,
        // Track draft_name for updating
        draft_name: draft_doc.name
    });
    // Attach draft_name to the composer instance for later use
    composer.draft_name = draft_doc.name;
};

// Initialize when page loads
$(function() {
    force_trans_customization.communication_draft.init();
}); 