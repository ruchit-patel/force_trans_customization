import router from "@/router"
import { createResource } from "frappe-ui"
import { computed, reactive } from "vue"

import { userResource } from "./user"

export function sessionUser() {
	const cookies = new URLSearchParams(document.cookie.split("; ").join("&"))
	let _sessionUser = cookies.get("user_id")
	if (_sessionUser === "Guest") {
		_sessionUser = null
	}
	return _sessionUser
}

export const session = reactive({
	logout: createResource({
		url: "logout",
		onSuccess() {
			userResource.reset()
			session.user = sessionUser()
			// Redirect to Frappe's login page
			window.location.href = "/login?redirect-to=" + encodeURIComponent(window.location.pathname)
		},
	}),
	user: sessionUser(),
	isLoggedIn: computed(() => !!session.user),
})
