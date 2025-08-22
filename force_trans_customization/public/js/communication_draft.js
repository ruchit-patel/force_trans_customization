// Enhanced CommunicationComposer with draft functionality
frappe.provide('force_trans_customization.communication_draft');

force_trans_customization.communication_draft = {
    init() {
        this.setup_draft_functionality();
    },

    setup_draft_functionality() {
        // Remove auto-save from content field
        const original_get_fields = frappe.views.CommunicationComposer.prototype.get_fields;
        frappe.views.CommunicationComposer.prototype.get_fields = function () {
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
        frappe.views.CommunicationComposer.prototype.make = function () {
            original_make.call(this);
            // Add Save As Draft button to dialog footer
            const me = this;
            const $footer = $(this.dialog.$wrapper).find('.modal-footer');
            if ($footer.find('.save-as-draft-btn').length === 0) {
                const $btn = $('<button class="btn btn-default save-as-draft-btn" style="margin-right: 8px;">' + __("Save As Draft") + '</button>');
                $btn.insertBefore($footer.find('.btn-primary, .btn-secondary').first());
                $btn.on('click', function () {
                    me.save_as_draft();
                });
            }
        };

        const original_save_as_draft = frappe.views.CommunicationComposer.prototype.save_as_draft;
        frappe.views.CommunicationComposer.prototype.save_as_draft = function () {
            if (this.dialog && this.frm) {
                let form_values = this.dialog.get_values();
                // Use draft_name if present (editing existing draft)
                let draft_name = this.draft_name || (form_values && form_values.draft_name);

                console.log("Saving draft with draft_name:", draft_name);

                // Check if this is a reply and get the parent communication ID
                let in_reply_to = null;
                if (this.is_a_reply && this.last_email && this.last_email.name) {
                    in_reply_to = this.last_email.name;
                    console.log("Setting in_reply_to for draft:", in_reply_to);
                }

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
                        draft_name: draft_name,
                        in_reply_to: in_reply_to
                    },
                    callback: function (r) {
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
                            // Close the email composer dialog
                            if (this.dialog) {
                                this.dialog.hide();
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

        // Override send_action to handle draft emails and add 30-second delay
        const original_send_action = frappe.views.CommunicationComposer.prototype.send_action;
        frappe.views.CommunicationComposer.prototype.send_action = async function () {
            // Add 30-second delay to send_after if not specified (for both draft and non-draft)
            let form_values = this.dialog.get_values();
            console.log("=== DEBUG: Communication Draft Send Action ===");
            console.log("Form values:", form_values);

            // Check if send_after is already set by user
            const currentSendAfter = form_values ? form_values.send_after : null;
            console.log("Current send_after value:", currentSendAfter);
            console.log("send_after field exists:", 'send_after' in (form_values || {}));

            let isDelayedSending = false;
            let communicationName = null;

            if (!currentSendAfter) {
                console.log("send_after is empty, applying 30-second delay");
                // Calculate 30 seconds from now in Frappe's configured timezone
                const now = new Date();
                const sendAfter = new Date(now.getTime() + 30 * 1000);

                // Convert to Frappe's timezone and format properly
                const sendAfterInTimezone = frappe.datetime.convert_to_user_tz(sendAfter);
                const formattedDateTime = frappe.datetime.get_datetime_as_string(sendAfterInTimezone);

                console.log("Setting send_after to:", formattedDateTime);

                // Set the send_after value in the dialog
                await this.dialog.set_value('send_after', formattedDateTime);

                // Debug: Check if the value was set
                const afterSetValue = this.dialog.get_value('send_after');
                console.log("After setting send_after, get_value returns:", afterSetValue);

                isDelayedSending = true;
            } else {
                console.log("send_after is already set, not applying delay");
            }

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
                    callback: function (r) {
                        if (r.message && r.message.success) {
                            communicationName = r.message.communication_name;


                            if (isDelayedSending) {
                                // Show toast with undo button for delayed sending
                                this.show_undo_toast(communicationName);
                            } else {
                                frappe.show_alert(__("Draft sent successfully"), 3);
                            }

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
                    }.bind(this)
                });
            } else {
                // This is a new email - check if it's a reply and handle accordingly
                if (this.is_a_reply && this.last_email && this.last_email.name) {
                    // This is a reply, use our custom send method to handle in_reply_to
                    let form_values = this.dialog.get_values();
                    
                    const selected_attachments = $.map(
                        $(this.dialog.wrapper).find("[data-file-name]:checked"),
                        function (element) {
                            return $(element).attr("data-file-name");
                        }
                    );

                    frappe.call({
                        method: "force_trans_customization.api.communication_threading.create_reply_communication",
                        args: {
                            reference_doctype: this.frm.doctype,
                            reference_name: this.frm.docname,
                            recipients: form_values.recipients,
                            sender: form_values.sender,
                            subject: form_values.subject,
                            content: form_values.content,
                            cc: form_values.cc,
                            bcc: form_values.bcc,
                            reply_to_communication: this.last_email.name,
                            send_email: true,
                            email_template: form_values.email_template,
                            attachments: selected_attachments,
                            send_after: form_values.send_after
                        },
                        callback: function (r) {
                            if (r.message && r.message.success) {
                                if (isDelayedSending) {
                                    this.show_undo_toast(r.message.name);
                                } else {
                                    frappe.show_alert(__("Email sent successfully"), 3);
                                }
                                
                                this.dialog.hide();
                                // Refresh timeline
                                if (this.frm && this.frm.timeline) {
                                    this.frm.timeline.refresh();
                                }
                            } else {
                                frappe.msgprint({
                                    title: __("Error"),
                                    message: r.message ? r.message.message : __("Error sending email"),
                                    indicator: "red"
                                });
                            }
                        }.bind(this)
                    });
                } else {
                    // This is not a reply, use the original send action
                    original_send_action.call(this);

                    // If delayed sending is enabled, we need to find the communication that was just created
                    if (isDelayedSending) {
                        // Wait a bit for the communication to be created, then find it
                        setTimeout(function () {
                            this.find_recent_communication_and_show_undo();
                        }.bind(this), 1000);
                    }
                }
            }
        };

        // Override the get_earlier_reply function to format quoted content properly
        const original_get_earlier_reply = frappe.views.CommunicationComposer.prototype.get_earlier_reply;
        frappe.views.CommunicationComposer.prototype.get_earlier_reply = function () {
            // First, get the result from the original Frappe function
            const originalResult = original_get_earlier_reply.call(this);
            
            if (!originalResult) return "";

            // Debug logging to understand the structure
            console.log("Original result:", originalResult);
            
            // Since the problematic blockquotes are created later, let's clean the content differently
            // We'll focus on cleaning excessive br tags and whitespace from the original result
            const cleanedResult = this.clean_excessive_breaks(originalResult);
            
            console.log("Cleaned result:", cleanedResult);
            
            return cleanedResult;
        };

        // New function to clean excessive breaks and whitespace
        frappe.views.CommunicationComposer.prototype.clean_excessive_breaks = function (html) {
            if (!html) return "";

            let cleaned = html;
            
            // Remove excessive consecutive <br> tags (more than 2 becomes 2)
            cleaned = cleaned.replace(/(<br\s*\/?>[\s\r\n]*){3,}/gi, '<br><br>');
            
            // Clean up excessive whitespace between elements
            cleaned = cleaned.replace(/>\s{2,}</g, '><');
            
            // Remove empty blockquotes that might contain only breaks
            cleaned = cleaned.replace(/<blockquote[^>]*>[\s\r\n]*(<br\s*\/?>[\s\r\n]*)*[\s\r\n]*<\/blockquote>/gi, '');
            
            // Clean up any remaining excessive line breaks within blockquotes
            cleaned = cleaned.replace(/<blockquote([^>]*)>([\s\S]*?)<\/blockquote>/gi, function(match, attrs, content) {
                // Clean content inside blockquote
                let cleanContent = content.replace(/(<br\s*\/?>[\s\r\n]*){3,}/gi, '<br><br>');
                // Remove leading/trailing breaks in blockquote
                cleanContent = cleanContent.replace(/^[\s\r\n]*(<br\s*\/?>[\s\r\n]*)+/gi, '');
                cleanContent = cleanContent.replace(/(<br\s*\/?>[\s\r\n]*)+[\s\r\n]*$/gi, '');
                
                return `<blockquote${attrs}>${cleanContent}</blockquote>`;
            });
            
            return cleaned.trim();
        };

        // Clean problematic blockquotes from editor content
        frappe.views.CommunicationComposer.prototype.clean_editor_blockquotes = function (html) {
            if (!html) return "";

            // Create a temporary div to parse HTML
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = html;

            // Find blockquotes with problematic content
            const blockquotes = tempDiv.querySelectorAll('blockquote');
            
            blockquotes.forEach((blockquote) => {
                const innerHTML = blockquote.innerHTML;
                
                // Check if blockquote contains only problematic elements
                const hasOnlyProblematicContent = /^[\s\r\n]*(<br\s*\/?>|<span[^>]*>[\s\u00A0\uFEFF]*<\/span>|&#xFEFF;|\s)*[\s\r\n]*$/i.test(innerHTML);
                
                if (hasOnlyProblematicContent) {
                    // Check if this is one of many consecutive empty blockquotes
                    let consecutiveEmpty = 1;
                    let next = blockquote.nextElementSibling;
                    
                    while (next && next.tagName === 'BLOCKQUOTE') {
                        const nextInner = next.innerHTML;
                        if (/^[\s\r\n]*(<br\s*\/?>|<span[^>]*>[\s\u00A0\uFEFF]*<\/span>|&#xFEFF;|\s)*[\s\r\n]*$/i.test(nextInner)) {
                            consecutiveEmpty++;
                            next = next.nextElementSibling;
                        } else {
                            break;
                        }
                    }
                    
                    // If more than 2 consecutive empty blockquotes, remove the excess
                    if (consecutiveEmpty > 2) {
                        blockquote.remove();
                    }
                }
            });

            return tempDiv.innerHTML;
        };

        // Add method to show undo toast
        frappe.views.CommunicationComposer.prototype.show_undo_toast = function (communicationName) {
            if (!communicationName) return;

            const toast = frappe.show_alert({
                message: __("Email will be sent in 30 seconds. ") +
                    ` <a class="text-small text-muted undo-email-btn" href="#" data-communication="${communicationName}" style="font-weight: bold; text-decoration: underline;">${__("Undo")}</a>`,
                indicator: "yellow"
            }, 30);

            // Add click handler for undo button
            toast.find('.undo-email-btn').on('click', function () {
                const commName = this.draft_name || communicationName;
                frappe.call({
                    method: "force_trans_customization.api.email_draft.undo_scheduled_email",
                    args: {
                        communication_name: commName
                    },
                    callback: function (r) {
                        if (r.message && r.message.success) {
                            frappe.show_alert(__("Email sending cancelled"), 3);
                            // Refresh timeline
                            if (this.frm && this.frm.timeline) {
                                this.frm.timeline.refresh();
                            }
                        } else {
                            frappe.msgprint({
                                title: __("Error"),
                                message: r.message ? r.message.message : __("Error cancelling email"),
                                indicator: "red"
                            });
                        }
                    }.bind(this)
                });

                // Remove the toast
                toast.remove();
            }.bind(this));
        };

        // Add method to find recent communication and show undo
        frappe.views.CommunicationComposer.prototype.find_recent_communication_and_show_undo = function () {
            // Use our custom server-side method to get the most recent communication
            frappe.call({
                method: "force_trans_customization.api.email_draft.get_recent_communication",
                args: {
                    doctype: this.frm.doctype,
                    docname: this.frm.docname,
                    minutes: 1
                },
                callback: function (r) {
                    console.log("Recent communication result:", r.message);
                    if (r.message && r.message.name) {
                        console.log("Using communication:", r.message.name, "created at:", r.message.creation);
                        this.show_undo_toast(r.message.name);
                    } else {
                        console.log("No recent communications found for undo");
                    }
                }.bind(this)
            });
        };


    },

    delete_draft(draft_name) {
        frappe.confirm(
            __("Are you sure you want to delete this draft?"),
            function () {
                frappe.call({
                    method: "force_trans_customization.api.email_draft.delete_draft",
                    args: {
                        draft_name: draft_name
                    },
                    callback: function (r) {
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

force_trans_customization.communication_draft.open_composer_with_draft = function (draft_doc) {
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
$(function () {
    force_trans_customization.communication_draft.init();
}); 