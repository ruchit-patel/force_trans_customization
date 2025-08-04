<template>
  <div class="grid grid-cols-1 md:grid-cols-5 gap-4 mb-8">
    <div 
      @click="handleStatClick('team_tickets')"
      :class="[
        'bg-white p-6 rounded-lg shadow-sm border cursor-pointer transition-all duration-200 hover:shadow-md',
        activeFilter === 'team_tickets' ? 'ring-2 ring-gray-500 bg-gray-50' : 'hover:bg-gray-50'
      ]"
    >
      <div class="text-3xl font-bold text-gray-900">{{ teamTickets }}</div>
      <div class="text-sm text-gray-600 mt-1">Team Tickets</div>
    </div>
    <div 
      @click="handleStatClick('open_tickets')"
      :class="[
        'bg-white p-6 rounded-lg shadow-sm border cursor-pointer transition-all duration-200 hover:shadow-md',
        activeFilter === 'open_tickets' ? 'ring-2 ring-blue-500 bg-blue-50' : 'hover:bg-blue-50'
      ]"
    >
      <div class="text-3xl font-bold text-blue-600">{{ openTickets }}</div>
      <div class="text-sm text-gray-600 mt-1">Open Tickets</div>
    </div>
    <div 
      @click="handleStatClick('assigned_to_me')"
      :class="[
        'bg-white p-6 rounded-lg shadow-sm border cursor-pointer transition-all duration-200 hover:shadow-md',
        activeFilter === 'assigned_to_me' ? 'ring-2 ring-green-500 bg-green-50' : 'hover:bg-green-50'
      ]"
    >
      <div class="text-3xl font-bold text-green-600">{{ assignedToMe }}</div>
      <div class="text-sm text-gray-600 mt-1">Assigned To Me</div>
    </div>
    <div 
      @click="handleStatClick('actionable_tickets')"
      :class="[
        'bg-white p-6 rounded-lg shadow-sm border cursor-pointer transition-all duration-200 hover:shadow-md',
        activeFilter === 'actionable_tickets' ? 'ring-2 ring-orange-500 bg-orange-50' : 'hover:bg-orange-50'
      ]"
      title="Issues where customer awaits our reply"
    >
      <div class="text-3xl font-bold text-orange-600">{{ actionableTickets }}</div>
      <div class="text-sm text-gray-600 mt-1">Customers Awaiting Our Reply</div>
    </div>
    <div 
      @click="handleStatClick('response_tickets')"
      :class="[
        'bg-white p-6 rounded-lg shadow-sm border cursor-pointer transition-all duration-200 hover:shadow-md',
        activeFilter === 'response_tickets' ? 'ring-2 ring-purple-500 bg-purple-50' : 'hover:bg-purple-50'
      ]"
      title="Issues awaiting customer response"
    >
      <div class="text-3xl font-bold text-purple-600">{{ responseTickets }}</div>
      <div class="text-sm text-gray-600 mt-1">Awaiting Response from Customer</div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, shallowRef } from "vue"
import { call } from "frappe-ui"

const props = defineProps({
  issues: {
    type: Array,
    default: () => [],
  },
  activeFilter: {
    type: String,
    default: 'team_tickets'
  }
})

// Define emits
const emit = defineEmits(['filter-changed'])

// Use shallowRef for stats object since we replace the entire object
const stats = shallowRef({
  team_tickets: 0,
  open_tickets: 0,
  assigned_to_me: 0,
  actionable_tickets: 0,
  response_tickets: 0
})

// Memoized reactive getters for template with proper reactivity
const teamTickets = computed(() => stats.value.team_tickets)
const openTickets = computed(() => stats.value.open_tickets)
const assignedToMe = computed(() => stats.value.assigned_to_me)
const actionableTickets = computed(() => stats.value.actionable_tickets)
const responseTickets = computed(() => stats.value.response_tickets)

// Memoized stats fetching with debouncing to prevent excessive API calls
let statsCache = null
let lastFetchTime = 0
const CACHE_DURATION = 30000 // 30 seconds cache

const fetchStats = async () => {
  const now = Date.now()
  
  // Return cached result if still valid
  if (statsCache && (now - lastFetchTime) < CACHE_DURATION) {
    return statsCache
  }
  
  try {
    const result = await call("force_trans_customization.api.issues.get_issue_stats")
    stats.value = result
    statsCache = result
    lastFetchTime = now
    return result
  } catch (error) {
    console.error("Error fetching issue stats:", error)
    // Keep existing values on error
    return stats.value
  }
}

// Debounced stats refresh to prevent excessive API calls
let refreshTimeout = null
const debouncedStatsRefresh = () => {
  if (refreshTimeout) {
    clearTimeout(refreshTimeout)
  }
  refreshTimeout = setTimeout(() => {
    fetchStats()
  }, 500) // 500ms debounce
}

// Fetch stats on component mount
onMounted(() => {
  fetchStats()
})

// Optimized watcher - only watch issues length instead of deep watching entire array
// This prevents unnecessary re-renders when issue content changes but count remains same
watch(() => props.issues.length, () => {
  debouncedStatsRefresh()
})

// Handle stat tile clicks
const handleStatClick = (filterType) => {
  emit('filter-changed', filterType)
}

// Expose fetchStats method for parent components to trigger refresh
defineExpose({
  refreshStats: fetchStats
})
</script>