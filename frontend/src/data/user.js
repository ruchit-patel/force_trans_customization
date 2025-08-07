import router from "@/router"
import { createResource } from "frappe-ui"

export const userResource = createResource({
	url: "frappe.auth.get_logged_user",
	cache: "User",
	onError(error) {
		if (error && error.exc_type === "AuthenticationError") {
			// Redirect to Frappe's login page
			window.location.href = "/login?redirect-to=" + encodeURIComponent(window.location.pathname)
		}
	},
})
