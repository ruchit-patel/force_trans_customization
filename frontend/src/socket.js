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

		if (host.includes('.force-trans.com')) {
			// Frappe Cloud configuration - socket.io is proxied through main domain
			socketUrl = `${protocol}://${host}/force-trans.v.frappe.cloud`
			socketOptions = {
				...socketOptions,
				path: '/socket.io/',
				timeout: 30000,
				transports: ['polling', 'websocket'], // Frappe Cloud may prefer polling first
			}
			
			console.log(`Frappe Cloud mode: connecting to main domain with site path`)
		} else {
			// Standard Frappe installation with custom socketio port
			socketUrl = `${protocol}://${host}:${socketio_port}/${siteName}`
		}

		console.log('Attempting to connect to:', socketUrl, 'with options:', socketOptions)
		socket = io(socketUrl, socketOptions)
		
		// Add connection event handlers
		socket.on('connect', () => {
			console.log('✅ Socket connected successfully')
			console.log('🔗 Socket ID:', socket.id)
		})
		
		socket.on('connect_error', (error) => {
			console.error('❌ Socket connection error:', error.message)
			console.error('🔍 Error details:', error)
			if (host.includes('.force-trans.com')) {
				console.warn('⚠️  Frappe Cloud socket.io connection failed')
				console.warn('💡 This could mean:')
				console.warn('   1. Socket.io is not enabled on this Frappe Cloud plan')
				console.warn('   2. Site name or path configuration is incorrect')
				console.warn('   3. Real-time features require a higher tier plan')
				console.warn(`   4. Attempted URL: ${socketUrl}`)
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