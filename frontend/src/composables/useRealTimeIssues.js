import { onMounted, onUnmounted, ref } from 'vue'
import { useSocket } from '../socket'
import { usePollingUpdates } from './usePollingUpdates'
import { reloadIssues, getIssuesCount } from '../data/issues'

export function useRealTimeIssues() {
  const socket = useSocket()
  const isConnected = ref(false)
  const lastUpdate = ref(null)
  const conflictingUpdates = ref([])
  const notifications = ref([])
  
  // Fallback polling system
  const { isPolling, startPolling, stopPolling } = usePollingUpdates()

  // Event handlers
  const handleConnect = () => {
    isConnected.value = true
    console.log('Socket connected for real-time issue updates')
    
    // Subscribe to Issue doctype updates
    socket.emit('doctype_subscribe', 'Issue')
    console.log('Subscribed to Issue doctype updates')
    
    // Stop polling since socket is working
    stopPolling()
  }

  const handleDisconnect = () => {
    isConnected.value = false
    console.log('Socket disconnected - starting polling fallback')
    
    // Start polling as fallback
    startPolling()
  }

  // Handle Frappe's built-in list_update event
  const handleListUpdate = (data) => {
    // Check if this is an Issue update
    if (data?.doctype === 'Issue') {
      console.log('Issue list_update via Frappe socket:', data)
      
      lastUpdate.value = {
        type: 'updated',
        doctype: data.doctype,
        name: data.name,
        user: data.modified_by || 'Unknown User',
        timestamp: new Date()
      }

      addNotification({
        type: 'info',
        title: 'Ticket Updated',
        message: `Ticket "${data.name}" was updated`,
        timestamp: new Date()
      })

      // Refresh the issue list to show changes
      refreshIssues()
    }
  }

  // Note: User management and conflict detection would need additional
  // Frappe events or custom implementation if needed in the future

  // Helper functions
  const refreshIssues = () => {
    // Get current filters and pagination from wherever they're stored
    // For now, we'll reload with default parameters
    reloadIssues()
    getIssuesCount()
  }

  const addNotification = (notification) => {
    const id = Date.now() + Math.random()
    notifications.value.push({
      id,
      ...notification
    })

    // Auto-remove non-persistent notifications after 5 seconds
    if (!notification.persistent) {
      setTimeout(() => {
        removeNotification(id)
      }, 5000)
    }
  }

  const removeNotification = (id) => {
    notifications.value = notifications.value.filter(n => n.id !== id)
  }

  const resolveConflict = (conflictId, resolution) => {
    conflictingUpdates.value = conflictingUpdates.value.filter(
      conflict => conflict.id !== conflictId
    )
    
    // Apply the resolution
    if (resolution === 'accept_remote') {
      refreshIssues()
    }
    // If 'keep_local', we don't need to do anything as local changes are preserved
  }

  // Room management functions can be added here if needed for future features

  // Lifecycle management
  const setupSocketListeners = () => {
    if (!socket) {
      console.warn('Socket not available, real-time updates disabled')
      return
    }

    socket.on('connect', handleConnect)
    socket.on('disconnect', handleDisconnect)
    
    // Add error handling
    socket.on('connect_error', (error) => {
      console.error('Socket connection failed:', error)
      isConnected.value = false
      
      // Start polling as fallback
      console.log('Starting polling due to socket connection failure')
      startPolling()
    })
    
    // Listen for Frappe's built-in list_update event
    socket.on('list_update', handleListUpdate)

    // Subscribe to Issue doctype updates (like Frappe's ListView does)
    if (socket.connected) {
      socket.emit('doctype_subscribe', 'Issue')
    }

    // Initial connection status
    isConnected.value = socket.connected
    
    console.log('Socket listeners setup for Frappe list_update event')
    console.log('Socket connected:', socket.connected)
  }

  const removeSocketListeners = () => {
    if (!socket) return

    socket.off('connect', handleConnect)
    socket.off('disconnect', handleDisconnect)
    socket.off('list_update', handleListUpdate)
    
    // Unsubscribe from Issue doctype
    socket.emit('doctype_unsubscribe', 'Issue')
  }

  // Setup and cleanup
  onMounted(() => {
    setupSocketListeners()
    
    // Check initial connection state and only start polling if needed
    setTimeout(() => {
      if (!socket || !socket.connected) {
        console.log('Socket not connected after initial check, starting polling fallback')
        startPolling()
      } else {
        console.log('Socket connected successfully, polling not needed')
      }
    }, 2000) // Reduced to 2 seconds for faster feedback
  })

  onUnmounted(() => {
    removeSocketListeners()
  })

  return {
    // State
    isConnected,
    lastUpdate,
    conflictingUpdates,
    notifications,
    isPolling,

    // Methods
    addNotification,
    removeNotification,
    resolveConflict,
    refreshIssues
  }
}