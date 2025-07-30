<template>
  <div v-if="conflicts.length > 0" class="fixed inset-0 z-50 overflow-y-auto">
    <div class="flex items-center justify-center min-h-screen p-4">
      <div class="fixed inset-0 bg-black bg-opacity-50 transition-opacity"></div>
      
      <div class="relative bg-white rounded-lg max-w-4xl w-full max-h-screen overflow-y-auto">
        <div class="sticky top-0 bg-white border-b px-6 py-4">
          <div class="flex items-center justify-between">
            <h2 class="text-lg font-semibold text-gray-900">
              Resolve Conflicts ({{ conflicts.length }})
            </h2>
            <button
              @click="$emit('close')"
              class="text-gray-400 hover:text-gray-600 focus:outline-none"
            >
              <FeatherIcon name="x" class="h-6 w-6" />
            </button>
          </div>
        </div>

        <div class="p-6 space-y-6">
          <div
            v-for="conflict in conflicts"
            :key="conflict.id"
            class="border rounded-lg p-4 bg-gray-50"
          >
            <div class="flex items-start justify-between mb-4">
              <div>
                <h3 class="font-medium text-gray-900">
                  {{ conflict.issue.subject }}
                </h3>
                <p class="text-sm text-gray-600 mt-1">
                  Modified by {{ conflict.user }} {{ formatTime(conflict.timestamp) }}
                </p>
              </div>
              <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                Conflict
              </span>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
              <!-- Local Changes -->
              <div class="bg-white rounded border p-3">
                <h4 class="font-medium text-sm text-gray-900 mb-2 flex items-center">
                  <FeatherIcon name="user" class="h-4 w-4 mr-1 text-blue-500" />
                  Your Changes
                </h4>
                <div class="space-y-2">
                  <div
                    v-for="(change, field) in conflict.localChanges"
                    :key="field"
                    class="text-sm"
                  >
                    <span class="font-medium text-gray-700">{{ formatFieldName(field) }}:</span>
                    <div class="mt-1 p-2 bg-blue-50 rounded text-blue-800">
                      {{ change }}
                    </div>
                  </div>
                </div>
              </div>

              <!-- Remote Changes -->
              <div class="bg-white rounded border p-3">
                <h4 class="font-medium text-sm text-gray-900 mb-2 flex items-center">
                  <FeatherIcon name="users" class="h-4 w-4 mr-1 text-green-500" />
                  {{ conflict.user }}'s Changes
                </h4>
                <div class="space-y-2">
                  <div
                    v-for="(change, field) in conflict.remoteChanges"
                    :key="field"
                    class="text-sm"
                  >
                    <span class="font-medium text-gray-700">{{ formatFieldName(field) }}:</span>
                    <div class="mt-1 p-2 bg-green-50 rounded text-green-800">
                      {{ change }}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div class="flex justify-end space-x-3">
              <Button
                theme="gray"
                variant="outline"
                size="sm"
                @click="resolveConflict(conflict.id, 'keep_local')"
              >
                <template #prefix>
                  <FeatherIcon name="user" class="h-4 w-4" />
                </template>
                Keep My Changes
              </Button>
              
              <Button
                theme="green"
                size="sm"
                @click="resolveConflict(conflict.id, 'accept_remote')"
              >
                <template #prefix>
                  <FeatherIcon name="download" class="h-4 w-4" />
                </template>
                Accept Their Changes
              </Button>
            </div>
          </div>
        </div>

        <div class="sticky bottom-0 bg-gray-50 border-t px-6 py-4">
          <div class="flex justify-between items-center">
            <p class="text-sm text-gray-600">
              {{ conflicts.length }} conflict(s) remaining
            </p>
            <div class="space-x-3">
              <Button
                theme="gray"
                variant="outline"
                @click="resolveAllConflicts('keep_local')"
              >
                Keep All My Changes
              </Button>
              <Button
                theme="green"
                @click="resolveAllConflicts('accept_remote')"
              >
                Accept All Their Changes
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { Button, FeatherIcon } from 'frappe-ui'

defineProps({
  conflicts: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['resolve', 'close'])

const resolveConflict = (conflictId, resolution) => {
  emit('resolve', { conflictId, resolution })
}

const resolveAllConflicts = (resolution) => {
  props.conflicts.forEach(conflict => {
    emit('resolve', { conflictId: conflict.id, resolution })
  })
}

const formatFieldName = (field) => {
  return field
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

const formatTime = (timestamp) => {
  const now = new Date()
  const diff = now - timestamp
  const minutes = Math.floor(diff / 60000)
  
  if (minutes < 1) return 'just now'
  if (minutes < 60) return `${minutes} minutes ago`
  
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours} hours ago`
  
  return timestamp.toLocaleDateString()
}
</script>