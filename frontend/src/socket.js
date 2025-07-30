import { io } from "socket.io-client"
import { socketio_port } from "../../../../sites/common_site_config.json"

let socket = null
export function initSocket() {
	try {
		const host = window.location.hostname
		const siteName = window.site_name || 'force.site'
		
		// Use Frappe's standard socketio URL pattern
		const socketUrl = `http://${host}:${socketio_port}/${siteName}`

		socket = io(socketUrl, {
			withCredentials: true,
			transports: ['websocket', 'polling'],
			reconnectionAttempts: 5,
			reconnectionDelay: 1000,
			timeout: 20000
		})
		
		// Add connection event handlers
		socket.on('connect', () => {
			// Subscribe to doctype updates immediately after connection
			socket.emit('doctype_subscribe', 'Issue')
		})
		
		socket.on('connect_error', (error) => {
			console.error('Socket connection error:', error.message)
		})
		
		socket.on('error', (error) => {
			console.error('Socket error:', error)
		})

		return socket
		
	} catch (error) {
		console.error('Failed to initialize socket:', error)
		return null
	}
}

export function useSocket() {
	return socket
}
