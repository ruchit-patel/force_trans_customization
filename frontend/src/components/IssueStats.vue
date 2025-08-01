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
    >
      <div class="text-3xl font-bold text-orange-600">{{ actionableTickets }}</div>
      <div class="text-sm text-gray-600 mt-1">Actionable</div>
    </div>
    <div 
      @click="handleStatClick('response_tickets')"
      :class="[
        'bg-white p-6 rounded-lg shadow-sm border cursor-pointer transition-all duration-200 hover:shadow-md',
        activeFilter === 'response_tickets' ? 'ring-2 ring-purple-500 bg-purple-50' : 'hover:bg-purple-50'
      ]"
    >
      <div class="text-3xl font-bold text-purple-600">{{ responseTickets }}</div>
      <div class="text-sm text-gray-600 mt-1">Response</div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from "vue"
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

// Global statistics (independent of current page)
const stats = ref({
  team_tickets: 0,
  open_tickets: 0,
  assigned_to_me: 0,
  actionable_tickets: 0,
  response_tickets: 0
})

// Reactive getters for template
const teamTickets = computed(() => stats.value.team_tickets)
const openTickets = computed(() => stats.value.open_tickets)
const assignedToMe = computed(() => stats.value.assigned_to_me)
const actionableTickets = computed(() => stats.value.actionable_tickets)
const responseTickets = computed(() => stats.value.response_tickets)

// Function to fetch global stats
const fetchStats = async () => {
  try {
    const result = await call("force_trans_customization.api.issues.get_issue_stats")
    stats.value = result
  } catch (error) {
    console.error("Error fetching issue stats:", error)
    // Keep existing values on error
  }
}

// Fetch stats on component mount
onMounted(() => {
  fetchStats()
})

// Watch for changes in issues prop to refresh stats
// This ensures stats are updated when issues are modified/added/deleted
watch(() => props.issues, () => {
  fetchStats()
}, { deep: true })

// Handle stat tile clicks
const handleStatClick = (filterType) => {
  emit('filter-changed', filterType)
}

// Expose fetchStats method for parent components to trigger refresh
defineExpose({
  refreshStats: fetchStats
})
</script>