import { io } from "socket.io-client"
import { socketio_port } from "../../../../sites/common_site_config.json"

let socket = null
export function initSocket() {
	try {
		const host = window.location.hostname
		const siteName = window.site_name || 'force.site'
		
		// Use Frappe's standard socketio URL pattern
		const socketUrl = `http://${host}:${socketio_port}/${siteName}`
		
		console.log('Attempting socket connection to:', socketUrl)
		console.log('Site name:', siteName)

		socket = io(socketUrl, {
			withCredentials: true,
			transports: ['websocket', 'polling'],
			reconnectionAttempts: 5,
			reconnectionDelay: 1000,
			timeout: 20000
		})
		
		// Add connection event handlers for debugging
		socket.on('connect', () => {
			console.log('Socket connected successfully:', socket.id)
			
			// Subscribe to doctype updates immediately after connection
			socket.emit('doctype_subscribe', 'Issue')
			console.log('Subscribed to Issue doctype updates')
			
			// Listen for all events for debugging
			socket.onAny((eventName, ...args) => {
				if (eventName.includes('list_update') || eventName.includes('Issue') || eventName.includes('doc_')) {
					console.log('🔥 Socket received event:', eventName, args)
				}
			})
		})
		
		socket.on('connect_error', (error) => {
			console.error('Socket connection error:', error.message)
			console.log('Trying fallback connection methods...')
		})
		
		socket.on('disconnect', (reason) => {
			console.log('Socket disconnected:', reason)
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
