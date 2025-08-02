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
      return
    }
    
    // Subscribe to Issue doctype updates (Frappe's standard way)
    socket.emit('doctype_subscribe', 'Issue')
    
    // Remove any existing listeners to avoid duplicates
    socket.off('list_update')
    
    // Listen for Frappe's standard list_update event
    socket.on('list_update', (data) => {
      if (data?.doctype !== 'Issue') {
        return
      }

      // Skip updates if we're in a state where updates should be avoided
      if (avoidRealtimeUpdate()) {
        return
      }

      // Add to pending refreshes
      pendingDocumentRefreshes.value.push(data)
      debouncedRefresh()
    })

    // Also listen for individual document events that should trigger list updates
    const documentEvents = ['doctype_update', 'Issue_update', 'Issue_create', 'Issue_delete']
    
    documentEvents.forEach(eventName => {
      socket.on(eventName, (data) => {
        if (data?.doctype !== 'Issue') {
          return
        }

        if (avoidRealtimeUpdate()) {
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

        pendingDocumentRefreshes.value.push(listUpdateData)
        debouncedRefresh()
      })
    })

    realtimeEventsSetup.value = true
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

  // Track page visibility state for focus-based refresh
  const wasPageHidden = ref(false)
  
  const handleVisibilityChange = () => {
    if (document.hidden) {
      // Page became hidden - remember this state
      wasPageHidden.value = true
    } else if (wasPageHidden.value) {
      // Page became visible again after being hidden - refresh the table
      wasPageHidden.value = false
      console.log('🔄 Page came back into focus - refreshing Issue table')
      
      // Process any pending updates that were skipped while page was hidden
      if (pendingDocumentRefreshes.value.length > 0) {
        console.log(`📋 Processing ${pendingDocumentRefreshes.value.length} pending updates`)
        processDocumentRefreshes()
      } else {
        // No pending updates, but still do a manual refresh to ensure data is current
        manualRefresh()
      }
    }
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

    // Set up page visibility change listener for focus-based refresh
    document.addEventListener('visibilitychange', handleVisibilityChange)

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
    
    // Remove page visibility change listener
    document.removeEventListener('visibilitychange', handleVisibilityChange)
    
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