<template>
  <div class="grid grid-cols-1 md:grid-cols-5 gap-4 mb-8">
    <div class="bg-white p-6 rounded-lg shadow-sm border">
      <div class="text-3xl font-bold text-gray-900">{{ teamTickets }}</div>
      <div class="text-sm text-gray-600 mt-1">Team Tickets</div>
    </div>
    <div class="bg-white p-6 rounded-lg shadow-sm border">
      <div class="text-3xl font-bold text-blue-600">{{ openTickets }}</div>
      <div class="text-sm text-gray-600 mt-1">Open Tickets</div>
    </div>
    <div class="bg-white p-6 rounded-lg shadow-sm border">
      <div class="text-3xl font-bold text-green-600">{{ assignedToMe }}</div>
      <div class="text-sm text-gray-600 mt-1">Assigned To Me</div>
    </div>
    <div class="bg-white p-6 rounded-lg shadow-sm border">
      <div class="text-3xl font-bold text-orange-600">{{ actionableTickets }}</div>
      <div class="text-sm text-gray-600 mt-1">Actionable</div>
    </div>
    <div class="bg-white p-6 rounded-lg shadow-sm border">
      <div class="text-3xl font-bold text-purple-600">{{ responseTickets }}</div>
      <div class="text-sm text-gray-600 mt-1">Response</div>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue"
import { session } from "../data/session"

const props = defineProps({
	issues: {
		type: Array,
		default: () => [],
	},
})

// Statistics calculations
const teamTickets = computed(() => props.issues.length)
const openTickets = computed(
	() => props.issues.filter((issue) => issue.status === "Open").length,
)
const assignedToMe = computed(
	() => props.issues.filter((issue) => issue.raised_by === session.user).length,
)
const actionableTickets = computed(
	() =>
		props.issues.filter((issue) => ["Open", "Replied"].includes(issue.status))
			.length,
)
const responseTickets = computed(
	() => props.issues.filter((issue) => issue.status === "Replied").length,
)
</script>