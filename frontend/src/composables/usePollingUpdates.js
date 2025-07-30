import { ref, onUnmounted } from 'vue'
import { reloadIssues, getIssuesCount } from '../data/issues'

export function usePollingUpdates() {
  const isPolling = ref(false)
  const lastPolled = ref(new Date())
  const pollingInterval = ref(null)
  
  // Poll every 30 seconds as fallback when socket is not available
  const POLL_INTERVAL = 30000 // 30 seconds
  
  const startPolling = () => {
    if (pollingInterval.value) return // Already polling
    
    console.log('Starting polling for issue updates (socket fallback)')
    isPolling.value = true
    
    pollingInterval.value = setInterval(() => {
      console.log('Polling for issue updates...')
      lastPolled.value = new Date()
      
      // Refresh issues data
      reloadIssues()
      getIssuesCount()
    }, POLL_INTERVAL)
  }
  
  const stopPolling = () => {
    if (pollingInterval.value) {
      clearInterval(pollingInterval.value)
      pollingInterval.value = null
      isPolling.value = false
      console.log('Stopped polling for issue updates')
    }
  }
  
  // Note: Polling is now controlled by the real-time composable
  // No auto-start here to avoid conflicts
  
  onUnmounted(() => {
    stopPolling()
  })
  
  return {
    isPolling,
    lastPolled,
    startPolling,
    stopPolling
  }
}