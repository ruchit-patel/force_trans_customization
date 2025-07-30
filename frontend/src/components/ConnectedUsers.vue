<template>
  <div class="bg-white rounded-lg shadow-sm border p-4">
    <div class="flex items-center justify-between mb-3">
      <h3 class="text-sm font-medium text-gray-900 flex items-center">
        <div 
          :class="connectionStatusClass"
          class="w-2 h-2 rounded-full mr-2"
        ></div>
        Connected Users
      </h3>
      <span class="text-xs text-gray-500">
        {{ connectedUsers.length }} online
      </span>
    </div>

    <div v-if="connectedUsers.length === 0" class="text-sm text-gray-500 text-center py-2">
      No other users currently online
    </div>

    <div v-else class="space-y-2">
      <div
        v-for="user in connectedUsers"
        :key="user.id"
        class="flex items-center justify-between py-2 px-3 bg-gray-50 rounded-lg"
      >
        <div class="flex items-center space-x-2">
          <div class="w-6 h-6 rounded-full bg-blue-500 flex items-center justify-center text-white text-xs font-medium">
            {{ getUserInitials(user.name) }}
          </div>
          <span class="text-sm font-medium text-gray-900">{{ user.name }}</span>
        </div>
        <div class="flex items-center space-x-2">
          <div class="w-2 h-2 bg-green-500 rounded-full"></div>
          <span class="text-xs text-gray-500">
            {{ formatJoinTime(user.joinedAt) }}
          </span>
        </div>
      </div>
    </div>

    <div v-if="!isConnected" class="mt-3 p-2 bg-yellow-50 border border-yellow-200 rounded text-sm text-yellow-800">
      <div class="flex items-center">
        <FeatherIcon name="wifi-off" class="h-4 w-4 mr-2" />
        Connection lost. Attempting to reconnect...
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { FeatherIcon } from 'frappe-ui'

const props = defineProps({
  connectedUsers: {
    type: Array,
    default: () => []
  },
  isConnected: {
    type: Boolean,
    default: false
  }
})

const connectionStatusClass = computed(() => {
  return props.isConnected 
    ? 'bg-green-500 animate-pulse' 
    : 'bg-red-500'
})

const getUserInitials = (name) => {
  return name
    .split(' ')
    .map(word => word.charAt(0))
    .join('')
    .toUpperCase()
    .slice(0, 2)
}

const formatJoinTime = (timestamp) => {
  const now = new Date()
  const diff = now - timestamp
  const minutes = Math.floor(diff / 60000)
  
  if (minutes < 1) return 'just joined'
  if (minutes < 60) return `${minutes}m ago`
  
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  
  return 'earlier today'
}
</script>