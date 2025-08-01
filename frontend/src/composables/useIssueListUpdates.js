import { onMounted, onUnmounted, ref } from 'vue'
import { useSocket } from '../socket'
import { reloadIssues, getIssuesCount, issuesResource, fetchSingleIssue, singleIssueResource } from '../data/issues'

/**
 * Composable that implements Frappe's list view realtime update pattern
 * Similar to setup_realtime_updates() in frappe/public/js/frappe/list/list_view.js
 */
export function useIssueListUpdates(getCurrentParams, customRefreshFunction) {
  const socket = useSocket()
  const pendingDocumentRefreshes = ref([])
  const realtimeEventsSetup = ref(false)
  const isLargeTable = ref(false) // Could be made configurable
  
  // Debounced refresh similar to Frappe's approach
  let debounceTimer = null
  const debounceDelay = isLargeTable.value ? 15000 : 2000 // 15s for large tables, 2s for normal
  
  const debouncedRefresh = () => {
    if (debounceTimer) {
      clearTimeout(debounceTimer)
    }
    debounceTimer = setTimeout(() => {
      processDocumentRefreshes()
    }, debounceDelay)
  }

  const setupRealtimeUpdates = () => {
    if (!socket || realtimeEventsSetup.value) {
      console.log('⚠️ Skipping realtime setup - socket:', !!socket, 'already setup:', realtimeEventsSetup.value)
      return
    }
    
    console.log('🚀 Setting up realtime updates for Issue doctype')
    
    // Subscribe to Issue doctype updates (Frappe's standard way)
    console.log('📡 Emitting doctype_subscribe for Issue')
    socket.emit('doctype_subscribe', 'Issue')
    
    // Try alternative subscription methods for different Frappe versions/configurations
    socket.emit('subscribe', 'Issue')
    socket.emit('join_room', 'Issue')
    socket.emit('join', 'doctype:Issue')
    
    // Also try subscribing to specific document events
    socket.emit('subscribe_to_doctype', 'Issue')
    
    // Remove any existing listeners to avoid duplicates
    socket.off('list_update')
    
    // Listen for Frappe's standard list_update event
    socket.on('list_update', (data) => {
      console.log('📨 Received list_update event:', data)
      
      if (data?.doctype !== 'Issue') {
        console.log('⏭️ Ignoring list_update - not for Issue doctype:', data?.doctype)
        return
      }

      console.log('✅ Processing Issue list_update:', data)

      // Skip updates if we're in a state where updates should be avoided
      if (avoidRealtimeUpdate()) {
        console.log('⏸️ Skipping realtime update due to avoidRealtimeUpdate()')
        return
      }

      // Add to pending refreshes
      pendingDocumentRefreshes.value.push(data)
      console.log('📝 Added to pending refreshes. Total pending:', pendingDocumentRefreshes.value.length)
      debouncedRefresh()
    })

    // Also listen for individual document events that should trigger list updates
    const documentEvents = ['doctype_update', 'Issue_update', 'Issue_create', 'Issue_delete']
    
    console.log('👂 Setting up listeners for document events:', documentEvents)
    
    documentEvents.forEach(eventName => {
      socket.on(eventName, (data) => {
        console.log(`📨 Received ${eventName} event:`, data)
        
        if (data?.doctype !== 'Issue') {
          console.log(`⏭️ Ignoring ${eventName} - not for Issue doctype:`, data?.doctype)
          return
        }

        console.log(`✅ Processing Issue ${eventName}:`, data)

        if (avoidRealtimeUpdate()) {
          console.log('⏸️ Skipping realtime update due to avoidRealtimeUpdate()')
          return
        }

        // Convert to list_update format
        const listUpdateData = {
          doctype: 'Issue',
          name: data.name,
          action: eventName.includes('create') ? 'insert' : 
                  eventName.includes('delete') ? 'delete' : 'update',
          modified_by: data.modified_by || data.owner,
          timestamp: new Date().toISOString()
        }

        console.log('📝 Converted to list_update format:', listUpdateData)
        pendingDocumentRefreshes.value.push(listUpdateData)
        console.log('📝 Added to pending refreshes. Total pending:', pendingDocumentRefreshes.value.length)
        debouncedRefresh()
      })
    })

    // Add comprehensive event listeners for different Frappe versions/configurations
    const allPossibleEvents = [
      'list_update',
      'doctype_update', 
      'Issue_update',
      'Issue_create', 
      'Issue_delete',
      'doc_update',
      'doc_create',
      'doc_delete',
      'document_update',
      'document_create',
      'document_delete',
      'eval_js', // Sometimes Frappe sends updates via eval_js
      'msgprint',
      'refresh'
    ]
    
    // Set up listeners for all possible event names
    allPossibleEvents.forEach(eventName => {
      socket.on(eventName, (data) => {
        console.log(`🔍 Received ${eventName} event:`, data)
        
        // Check if this event is related to Issues
        const isIssueRelated = (
          data?.doctype === 'Issue' ||
          data?.doc_type === 'Issue' ||
          data?.name?.startsWith('ISS-') ||
          (typeof data === 'string' && data.includes('Issue')) ||
          eventName.includes('Issue')
        )
        
        if (isIssueRelated) {
          console.log(`✅ Processing Issue-related ${eventName}:`, data)
          
          if (avoidRealtimeUpdate()) {
            console.log('⏸️ Skipping realtime update due to avoidRealtimeUpdate()')
            return
          }
          
          // Normalize the data format
          let normalizedData = data
          if (typeof data === 'string') {
            try {
              normalizedData = JSON.parse(data)
            } catch (e) {
              normalizedData = { name: data, doctype: 'Issue' }
            }
          }
          
          const listUpdateData = {
            doctype: 'Issue',
            name: normalizedData.name || normalizedData.doc_name || 'Unknown',
            action: eventName.includes('create') ? 'insert' : 
                    eventName.includes('delete') ? 'delete' : 'update',
            modified_by: normalizedData.modified_by || normalizedData.owner || 'System',
            timestamp: new Date().toISOString()
          }
          
          console.log('📝 Normalized to list_update format:', listUpdateData)
          pendingDocumentRefreshes.value.push(listUpdateData)
          console.log('📝 Added to pending refreshes. Total pending:', pendingDocumentRefreshes.value.length)
          debouncedRefresh()
        }
      })
    })
    
    // Add a catch-all listener to see ALL events (for debugging)
    socket.onAny((eventName, ...args) => {
      // Only log events that might be relevant to avoid spam
      if (eventName.includes('Issue') || 
          eventName.includes('list') || 
          eventName.includes('update') ||
          eventName.includes('create') ||
          eventName.includes('delete') ||
          eventName.includes('doc') ||
          (args[0] && typeof args[0] === 'object' && args[0].doctype === 'Issue')) {
        console.log('🔍 Catch-all - Received relevant event:', eventName, args)
      }
    })

    realtimeEventsSetup.value = true
    console.log('✅ Realtime updates setup complete')
  }

  const disableRealtimeUpdates = () => {
    if (!socket || !realtimeEventsSetup.value) {
      return
    }
    
    // Unsubscribe from doctype updates
    socket.emit('doctype_unsubscribe', 'Issue')
    
    // Remove all event listeners
    socket.off('list_update')
    const documentEvents = ['doctype_update', 'Issue_update', 'Issue_create', 'Issue_delete']
    documentEvents.forEach(eventName => {
      socket.off(eventName)
    })
    
    realtimeEventsSetup.value = false
  }

  const processDocumentRefreshes = async () => {
    if (!pendingDocumentRefreshes.value.length) {
      return
    }

    // Check if we're still on the correct route/page
    const currentRoute = window.location.hash || window.location.pathname
    if (!currentRoute.includes('issue-tracker') && !currentRoute.includes('issues')) {
      // Clear pending refreshes if user navigated away
      pendingDocumentRefreshes.value = []
      disableRealtimeUpdates()
      return
    }

    // Get unique document names from pending refreshes
    const uniqueDocuments = [...new Set(pendingDocumentRefreshes.value.map(d => d.name))]
    const refreshCount = uniqueDocuments.length

    // Clear pending refreshes
    pendingDocumentRefreshes.value = []

    try {
      // Update with current view parameters to maintain user's context
      await updateIndividualRows(uniqueDocuments)
      
      // Emit a custom event that the parent component can listen to for notifications
      if (window && typeof window.dispatchEvent === 'function') {
        window.dispatchEvent(new CustomEvent('issueListUpdated', {
          detail: { count: refreshCount, documents: uniqueDocuments }
        }))
      }
    } catch (error) {
      console.error('Error updating individual rows, falling back to full refresh:', error)
      // Fallback to full refresh if individual update fails
      try {
        await reloadIssues()
        await getIssuesCount()
      } catch (fallbackError) {
        console.error('Error in fallback refresh:', fallbackError)
      }
    }
  }

  const updateIndividualRows = async (documentNames) => {
    try {
      // If a custom refresh function is provided, use it instead of the default logic
      if (customRefreshFunction && typeof customRefreshFunction === 'function') {
        await customRefreshFunction()
        return
      }
      
      // Fallback to default logic if no custom refresh function
      // Check if we have current data
      if (!issuesResource.data || !Array.isArray(issuesResource.data)) {
        throw new Error('No issues data available')
      }
      
      // Get the current pagination and filter parameters from the component
      let currentParams = {
        limit_page_length: 10,
        limit_start: 0,
        filters: {},
        order_by: "creation desc"
      }
      
      // If getCurrentParams function is provided, use it to get actual current parameters
      if (getCurrentParams && typeof getCurrentParams === 'function') {
        try {
          const params = getCurrentParams()
          if (params) {
            currentParams = { ...currentParams, ...params }
          }
        } catch (paramError) {
          console.warn('Error getting current parameters, using defaults:', paramError)
        }
      }
      
      // Reload the issues resource with current parameters
      // This maintains the user's current view (filters, sort, pagination)
      await issuesResource.reload(currentParams)
      
    } catch (error) {
      console.error('Error during targeted refresh:', error)
      throw error
    }
  }

  const shouldIncludeInCurrentView = (issue) => {
    // This is a simplified check - you might want to implement more sophisticated
    // filtering logic based on current filters, search terms, etc.
    // For now, we'll include all new issues
    return true
  }

  const avoidRealtimeUpdate = () => {
    // Similar to Frappe's avoid_realtime_update() logic
    
    // Check if any bulk operations are in progress
    // (you could check for selected items, bulk actions, etc.)
    
    // Check if filters are being edited
    // (you could check if filter modals/inputs are active)
    
    // Check if the page is hidden/not focused
    if (document.hidden) {
      return true
    }

    // Add any other conditions where updates should be avoided
    return false
  }

  // Manual refresh method (useful for pull-to-refresh or manual refresh buttons)
  const manualRefresh = () => {
    pendingDocumentRefreshes.value = [] // Clear any pending
    try {
      // Use custom refresh function if provided, otherwise use default
      if (customRefreshFunction && typeof customRefreshFunction === 'function') {
        customRefreshFunction()
      } else {
        reloadIssues()
        getIssuesCount()
      }
    } catch (error) {
      console.error('Error during manual refresh:', error)
    }
  }

  // Socket connection handlers
  const handleConnect = () => {
    setupRealtimeUpdates()
  }

  const handleDisconnect = () => {
    realtimeEventsSetup.value = false
  }

  const handleConnectError = (error) => {
    console.error('Socket connection error:', error)
    realtimeEventsSetup.value = false
  }

  // Lifecycle management
  onMounted(() => {
    if (!socket) {
      return
    }

    // Set up socket connection handlers
    socket.on('connect', handleConnect)
    socket.on('disconnect', handleDisconnect)
    socket.on('connect_error', handleConnectError)

    // If already connected, set up immediately
    if (socket.connected) {
      setupRealtimeUpdates()
    }
  })

  onUnmounted(() => {
    if (socket) {
      socket.off('connect', handleConnect)
      socket.off('disconnect', handleDisconnect)
      socket.off('connect_error', handleConnectError)
    }
    
    disableRealtimeUpdates()
    
    // Clear any pending debounce timer
    if (debounceTimer) {
      clearTimeout(debounceTimer)
    }
  })

  return {
    // State (return the refs, not their values)
    pendingDocumentRefreshes,
    realtimeEventsSetup,
    
    // Methods
    setupRealtimeUpdates,
    disableRealtimeUpdates,
    manualRefresh,
    processDocumentRefreshes
  }
}