<template>
  <div class="fixed top-4 right-4 z-50 space-y-2 max-w-sm">
    <transition-group name="notification" tag="div">
      <div
        v-for="notification in notifications"
        :key="notification.id"
        :class="notificationClasses(notification.type)"
        class="p-4 rounded-lg shadow-lg border backdrop-blur-sm"
      >
        <div class="flex items-start justify-between">
          <div class="flex items-start space-x-3">
            <div class="flex-shrink-0">
              <FeatherIcon 
                :name="getNotificationIcon(notification.type)" 
                :class="getIconColor(notification.type)"
                class="h-5 w-5"
              />
            </div>
            <div class="flex-1 min-w-0">
              <p class="text-sm font-medium text-gray-900">
                {{ notification.title }}
              </p>
              <p class="text-sm text-gray-600 mt-1">
                {{ notification.message }}
              </p>
              <p class="text-xs text-gray-500 mt-1">
                {{ formatTime(notification.timestamp) }}
              </p>
            </div>
          </div>
          <button
            @click="$emit('remove', notification.id)"
            class="flex-shrink-0 ml-3 text-gray-400 hover:text-gray-600 focus:outline-none"
          >
            <FeatherIcon name="x" class="h-4 w-4" />
          </button>
        </div>
      </div>
    </transition-group>
  </div>
</template>

<script setup>
import { FeatherIcon } from 'frappe-ui'

defineProps({
  notifications: {
    type: Array,
    default: () => []
  }
})

defineEmits(['remove'])

const notificationClasses = (type) => {
  const baseClasses = 'bg-white/95 border-l-4'
  const typeClasses = {
    success: 'border-green-500',
    info: 'border-blue-500', 
    warning: 'border-yellow-500',
    error: 'border-red-500'
  }
  return `${baseClasses} ${typeClasses[type] || typeClasses.info}`
}

const getNotificationIcon = (type) => {
  const icons = {
    success: 'check-circle',
    info: 'info',
    warning: 'alert-triangle',
    error: 'alert-circle'
  }
  return icons[type] || icons.info
}

const getIconColor = (type) => {
  const colors = {
    success: 'text-green-500',
    info: 'text-blue-500',
    warning: 'text-yellow-500', 
    error: 'text-red-500'
  }
  return colors[type] || colors.info
}

const formatTime = (timestamp) => {
  const now = new Date()
  const diff = now - timestamp
  const minutes = Math.floor(diff / 60000)
  
  if (minutes < 1) return 'Just now'
  if (minutes < 60) return `${minutes}m ago`
  
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  
  return timestamp.toLocaleDateString()
}
</script>

<style scoped>
.notification-enter-active,
.notification-leave-active {
  transition: all 0.3s ease;
}

.notification-enter-from {
  opacity: 0;
  transform: translateX(100%);
}

.notification-leave-to {
  opacity: 0;
  transform: translateX(100%);
}

.notification-move {
  transition: transform 0.3s ease;
}
</style>