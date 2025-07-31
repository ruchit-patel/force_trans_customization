import { io } from "socket.io-client"
import { socketio_port } from "../../../../sites/common_site_config.json"

let socket = null
export function initSocket() {
	try {
		const host = window.location.hostname
		const siteName = window.site_name || 'force.site'
		
		// Use appropriate protocol based on current page protocol
		const protocol = window.location.protocol === 'https:' ? 'https' : 'http'
		
		// Handle Frappe Cloud vs standard Frappe installation
		let socketUrl
		let socketOptions = {
			withCredentials: true,
			transports: ['websocket', 'polling'],
			reconnectionAttempts: 5,
			reconnectionDelay: 1000,
			timeout: 20000
		}

		if (host.includes('.frappe.cloud')) {
			// Frappe Cloud configuration
			socketUrl = `${protocol}://${host}`
			socketOptions = {
				...socketOptions,
				path: '/socket.io/',
				timeout: 30000, // Increase timeout for cloud
				transports: ['polling', 'websocket'], // Try polling first for cloud
			}
		} else {
			// Standard Frappe installation with custom socketio port
			socketUrl = `${protocol}://${host}:${socketio_port}/${siteName}`
		}

		console.log('Attempting to connect to:', socketUrl, 'with options:', socketOptions)
		socket = io(socketUrl, socketOptions)
		
		// Add connection event handlers
		socket.on('connect', () => {
			console.log('✅ Socket connected successfully')
			// Subscribe to doctype updates immediately after connection
			socket.emit('doctype_subscribe', 'Issue')
		})
		
		socket.on('connect_error', (error) => {
			console.error('❌ Socket connection error:', error.message)
			if (host.includes('.frappe.cloud')) {
				console.warn('⚠️  Frappe Cloud may not have Socket.IO enabled or configured differently')
				console.warn('💡 Consider checking if real-time features are available on your Frappe Cloud plan')
			}
		})
		
		socket.on('disconnect', (reason) => {
			console.warn('🔌 Socket disconnected:', reason)
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
