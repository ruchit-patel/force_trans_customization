import { userResource } from "@/data/user"
import { createRouter, createWebHistory } from "vue-router"
import { session } from "./data/session"

const routes = [
	{
		path: "/",
		name: "IssueTracker",
		component: () => import("@/pages/IssueTracker.vue"),
	},
	{
		path: "/sent-emails",
		name: "SentEmails",
		component: () => import("@/pages/SentEmails.vue"),
	},
]

const router = createRouter({
	history: createWebHistory("/frontend"),
	routes,
})

router.beforeEach(async (to, from, next) => {
	let isLoggedIn = session.isLoggedIn
	try {
		await userResource.promise
	} catch (error) {
		isLoggedIn = false
	}

	if (!isLoggedIn) {
		// Redirect to Frappe's login page
		window.location.href = "/login?redirect-to=" + encodeURIComponent(window.location.pathname)
	} else {
		next()
	}
})

export default router
