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

		if (host.includes('.force-trans.com') || host.includes('frappe.cloud')) {
			// Frappe Cloud configuration
			socketUrl = `${protocol}://${host}`
			socketOptions = {
				...socketOptions,
				path: '/socket.io/',
				timeout: 30000, // Increase timeout for cloud
				transports: ['websocket', 'polling'], // Try websocket first for cloud
				forceNew: true, // Force new connection for cloud
				upgrade: true, // Allow transport upgrades
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
			console.log('🔌 Socket ID:', socket.id)
			
			// Subscribe to doctype updates immediately after connection
			console.log('📡 Subscribing to Issue doctype updates...')
			socket.emit('doctype_subscribe', 'Issue')
			
			// Also try alternative subscription methods for production
			socket.emit('subscribe', 'Issue')
			socket.emit('join', 'Issue')
			
			// Test if the server acknowledges our subscription
			socket.emit('doctype_subscribe', 'Issue', (ack) => {
				if (ack) {
					console.log('✅ Doctype subscription acknowledged:', ack)
				} else {
					console.warn('⚠️ No acknowledgment for doctype subscription')
				}
			})
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

// Debug function to test socket connection and events
export function debugSocket() {
	if (!socket) {
		console.error('❌ Socket not initialized')
		return
	}
	
	console.log('🔍 Socket Debug Info:')
	console.log('- Connected:', socket.connected)
	console.log('- Socket ID:', socket.id)
	console.log('- Transport:', socket.io.engine.transport.name)
	console.log('- URL:', socket.io.uri)
	
	// Test subscription
	console.log('📡 Testing doctype subscription...')
	socket.emit('doctype_subscribe', 'Issue', (ack) => {
		console.log('✅ Subscription acknowledgment:', ack)
	})
	
	// Test if we can emit a custom event
	socket.emit('test_event', { message: 'Hello from frontend' }, (response) => {
		console.log('📨 Test event response:', response)
	})
	
	return {
		socket,
		connected: socket.connected,
		id: socket.id,
		transport: socket.io.engine.transport.name,
		url: socket.io.uri
	}
}

// Make debug function available globally for console testing
if (typeof window !== 'undefined') {
	window.debugSocket = debugSocket
}
