import { createApp } from "vue"

import App from "./App.vue"
import router from "./router"
import { initSocket } from "./socket"

import {
	Alert,
	Badge,
	Button,
	Dialog,
	ErrorMessage,
	FormControl,
	Input,
	TextInput,
	frappeRequest,
	pageMetaPlugin,
	resourcesPlugin,
	setConfig,
} from "frappe-ui"

import "./index.css"

const globalComponents = {
	Button,
	TextInput,
	Input,
	FormControl,
	ErrorMessage,
	Dialog,
	Alert,
	Badge,
}

const app = createApp(App)

setConfig("resourceFetcher", frappeRequest)

app.use(router)
app.use(resourcesPlugin)
app.use(pageMetaPlugin)

const socket = initSocket()
app.config.globalProperties.$socket = socket

// Make socket available globally for debugging
if (typeof window !== 'undefined') {
	window.socket = socket
	
	// Load test utilities in development
	if (import.meta.env.DEV) {
		import('./utils/realtimeTest.js').then(() => {
			console.log('🧪 Realtime test functions available:');
			console.log('- testRealtimeConnection()');
			console.log('- testBackendEmission()');
			console.log('- createTestIssue()');
			console.log('- updateTestIssue(issueName)');
		})
	}
}

for (const key in globalComponents) {
	app.component(key, globalComponents[key])
}

app.mount("#app")
