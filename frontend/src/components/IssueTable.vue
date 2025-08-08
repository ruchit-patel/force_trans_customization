<template>
	<div class="bg-white rounded-lg shadow-sm border">
		<div class="px-6 py-4 border-b border-gray-200">
			<h3 class="text-lg font-medium text-gray-900">Issues</h3>
		</div>

		<!-- Loading state -->
		<div v-if="loading" class="px-6 py-12 text-center text-gray-500">
			<div class="flex items-center justify-center">
				<div class="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
				<span class="ml-2">Loading issues...</span>
			</div>
		</div>

		<!-- ListView -->
		<ListView v-else :columns="columns" :rows="transformedIssues" row-key="name" :options="listOptions"
			@update:selections="handleSelections" class="p-4">

			<ListHeader>
				<ListHeaderItem v-for="column in columns" :key="column.key" :item="column">
					<template v-if="column.icon" #prefix="{ item }">
						<FeatherIcon :name="item.icon" class="h-4 w-4" />
					</template>

					<!-- Sort indicator for sortable columns -->
					<template v-if="column.sortable" #suffix>
						<button @click="handleColumnSort(column.key)"
							class="ml-2 p-1 rounded hover:bg-gray-100 transition-colors"
							:class="getSortButtonClass(column.key)">
							<FeatherIcon :name="getSortIcon(column.key)" class="h-3 w-3"
								:class="getSortIconClass(column.key)" />
						</button>
					</template>
				</ListHeaderItem>
			</ListHeader>

			<ListRows>
				<ListRow v-for="issue in transformedIssues" :key="issue.name" :row="issue">
					<template #default="{ column, item }">
						<ListRowItem :item="item" :align="column.align">
							<template #prefix>
								<!-- Avatar for assignee column -->
								<Avatar v-if="column.key === 'raised_by'" :size="'sm'"
									:label="getInitials(issue.raised_by)" class="mr-3" />
							</template>

							<!-- Custom content for specific columns only -->
							<template #default>
								<!-- Issue ID with link -->
								<a v-if="column.key === 'name'" href="#"
									class="text-blue-600 hover:text-blue-800 hover:underline font-medium text-sm"
									@click.prevent="handleIssueClick(issue)">
									{{ formatIssueId(item) }}
								</a>


								<!-- Title with description tooltip and communication click -->
								<div v-else-if="column.key === 'subject'" class="max-w-xs">
									<div class="font-medium truncate cursor-pointer" @click="openCommunicationDialog(issue)">
										{{ issue.subject }}
									</div>
									<Tooltip 
										v-if="issue.description" 
										:text="stripHtml(issue.description)"
										placement="top"
									>
										<div class="text-gray-500 text-sm mt-1 description-text cursor-help">
											{{ stripHtml(issue.description) }}
										</div>
									</Tooltip>
								</div>

								<!-- Assignee email with truncation -->
								<Tooltip 
									v-if="column.key === 'raised_by'" 
									:text="item || '-'"
									placement="top"
								>
									<span class="text-sm font-medium text-gray-900 truncate block cursor-help">
										{{ item || '-' }}
									</span>
								</Tooltip>

								<!-- Assigned Users as pills with hover popup -->
								<div v-else-if="column.key === 'custom_users_assigned'" class="flex flex-wrap gap-1">
									<template
										v-if="issue.custom_users_assigned && issue.custom_users_assigned.length > 0">
										<div v-for="user in issue.custom_users_assigned.filter(u => u.user_assigned)"
											:key="user.name || user" class="relative inline-block">
											<span
												class="inline-flex items-center px-2 py-1 text-xs font-medium rounded-full bg-blue-100 text-blue-800 cursor-pointer hover:bg-blue-200 transition-colors"
												@mouseenter="showUserPopup($event, user)" @mouseleave="hideUserPopup">
												{{ getInitials(user.user_assigned) }}
											</span>
										</div>
									</template>
									<span v-else class="text-gray-400 text-sm">-</span>
								</div>

								<!-- Tags -->
								<div v-else-if="column.key === '_user_tags'"
									class="flex items-center gap-1 cursor-pointer hover:bg-gray-50 p-1 rounded transition-colors"
									@mouseenter="showTagsPopupFn($event, issue._user_tags)"
									@mouseleave="hideTagsPopupFn">
									<template v-if="issue._user_tags && issue._user_tags.length > 0">
										<!-- Show first tag, truncated if needed -->
										<span :style="getTagStyle(issue._user_tags[0])"
											class="inline-flex items-center px-2 py-1 text-xs font-medium rounded-full border transition-colors max-w-16"
											:title="issue._user_tags[0]">
											<span class="truncate">{{ issue._user_tags[0] }}</span>
										</span>
										<!-- Always show +X more if there are more tags -->
										<span v-if="issue._user_tags.length > 1"
											class="inline-flex items-center px-1 py-1 text-xs font-medium text-gray-500">
											+{{ issue._user_tags.length - 1 }}
										</span>
									</template>
									<span v-else class="text-gray-400 text-sm">-</span>
								</div>

								<!-- Created At with date and time -->
								<div v-else-if="column.key === 'creation'" class="flex flex-col">
									<span class="text-sm">{{ formatDate(item) }}</span>
									<span class="text-xs text-gray-400">{{ formatTime(item) }}</span>
								</div>

								<!-- Status badge -->
								<span v-else-if="column.key === 'status'"
									:class="getStatusBadgeClass(issue.status?.label || issue.status || 'New')"
									class="inline-flex px-2 py-1 text-xs font-semibold rounded-full">
									{{ issue.status?.label || issue.status || 'New' }}
								</span>
							</template>
						</ListRowItem>
					</template>
				</ListRow>
			</ListRows>

			<ListSelectBanner>
				<template #actions="{ unselectAll }">
					<div class="flex gap-2">
						<Button variant="ghost" label="Delete" />
						<Button variant="ghost" label="Unselect all" @click="unselectAll" />
					</div>
				</template>
			</ListSelectBanner>

		</ListView>

		<!-- User Popup -->
		<div v-if="showPopup && popupUser"
			class="fixed z-50 bg-white border border-gray-200 rounded-lg shadow-lg p-3 min-w-48" :style="{
				left: popupPosition.x + 'px',
				top: popupPosition.y + 'px',
				transform: 'translateX(-50%) translateY(-100%)'
			}">
			<div class="text-sm">
				<div class="font-semibold text-gray-900 mb-1">
					{{ popupUser.user_assigned || 'Unknown User' }}
				</div>
				<div class="text-gray-600 flex items-center gap-1">
					<span class="inline-block w-2 h-2 bg-blue-500 rounded-full"></span>
					{{ popupUser.team || 'No Team' }}
				</div>
				<div class="text-xs text-gray-500 mt-1">
					Assigned: {{ formatDate(popupUser.assigned_date) }}
				</div>
			</div>
		</div>

		<!-- Tags Popup -->
		<div v-if="showTagsPopup && tagsPopupData"
			class="fixed z-50 bg-white border border-gray-200 rounded-lg shadow-lg p-3 min-w-48 max-w-xs" :style="{
				left: tagsPopupPosition.x + 'px',
				top: tagsPopupPosition.y + 'px',
				transform: 'translateX(-50%) translateY(-100%)'
			}">
			<div class="text-sm">
				<div class="font-semibold text-gray-900 mb-2">All Tags</div>
				<div class="flex flex-wrap gap-1">
					<span v-for="tag in tagsPopupData" :key="tag" :style="getTagStyle(tag)"
						class="inline-flex items-center px-2 py-1 text-xs font-medium rounded-full border">
						{{ tag }}
					</span>
				</div>
			</div>
		</div>

		<!-- Communication Dialog -->
		<Dialog 
			v-model="showCommunicationDialog" 
			:options="{
				title: `Communications - ${selectedIssue?.name || ''}`,
				size: 'xl'
			}"
		>
			<template #body>
				<div v-if="loadingCommunications" class="flex items-center justify-center py-8">
					<div class="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
					<span class="ml-2 text-gray-600">Loading communications...</span>
				</div>
				
				<div v-else-if="communications.length === 0" class="text-center py-8 text-gray-500">
					<FeatherIcon name="mail" class="h-12 w-12 mx-auto mb-4 text-gray-300" />
					<p>No communications found for this issue</p>
				</div>

				<div v-else class="space-y-4 p-4 max-h-96 overflow-y-auto">
					<div v-if="selectedIssue?.name" class="mb-4 flex justify-end">
						<button 
							@click="openIssue"
							class="px-3 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 flex items-center gap-2"
						>
							<FeatherIcon name="external-link" class="h-4 w-4" />
							Open Issue
						</button>
					</div>


					<div 
						v-for="(comm, index) in communications" 
						:key="comm.name"
						class="border rounded-lg p-4 hover:bg-gray-50 transition-colors"
						:class="{
							'border-blue-200 bg-blue-50': comm.sent_or_received === 'Sent',
							'border-green-200 bg-green-50': comm.sent_or_received === 'Received'
						}"
					>
						<!-- Header -->
						<div class="flex items-start justify-between mb-3">
							<div class="flex-1">
								<div class="flex items-center gap-2 mb-1">
									<FeatherIcon 
										:name="comm.sent_or_received === 'Sent' ? 'arrow-up' : 'arrow-down'" 
										class="h-4 w-4"
										:class="{
											'text-blue-600': comm.sent_or_received === 'Sent',
											'text-green-600': comm.sent_or_received === 'Received'
										}"
									/>
									<h4 class="font-medium text-gray-900 truncate">
										{{ comm.subject || 'No Subject' }}
									</h4>
								</div>
								<div class="text-sm text-gray-600 flex items-center gap-4">
									<span>{{ comm.sender || '-' }}</span>
									<span>{{ comm.relative_time || formatDateTime(comm.creation) }}</span>
									<Badge
										:label="comm.sent_or_received"
										:theme="getCommunicationStatusTheme(comm.sent_or_received)"
										variant="subtle"
										size="sm"
									/>
								</div>
							</div>
						</div>

						<!-- Content -->
						<div class="prose prose-sm max-w-none">
							<div 
								class="text-gray-800 leading-relaxed whitespace-pre-wrap"
								v-html="sanitizeContent(comm.content) || 'No content'">
							</div>
						</div>


						<!-- Footer -->
						<div class="mt-3 pt-3 border-t border-gray-200 text-xs text-gray-500 flex items-center justify-between">
							<span>
								{{ comm.communication_medium || 'Email' }} • 
								{{ formatDateTime(comm.creation) }}
							</span>
							<span v-if="comm.seen" class="text-green-600">
								<FeatherIcon name="check" class="h-3 w-3 inline" /> Seen
							</span>
						</div>
					</div>
				</div>
			</template>
			
			<template #actions>
				<Button 
					variant="ghost" 
					@click="showCommunicationDialog = false"
				>
					Close
				</Button>
			</template>
		</Dialog>
	</div>
</template>

<script>
import { Avatar, Badge, Button, FeatherIcon, ListView, Tooltip, Dialog } from "frappe-ui"
import ListHeader from "frappe-ui/src/components/ListView/ListHeader.vue"
import ListHeaderItem from "frappe-ui/src/components/ListView/ListHeaderItem.vue"
import ListRow from "frappe-ui/src/components/ListView/ListRow.vue"
import ListRowItem from "frappe-ui/src/components/ListView/ListRowItem.vue"
import ListRows from "frappe-ui/src/components/ListView/ListRows.vue"
import ListSelectBanner from "frappe-ui/src/components/ListView/ListSelectBanner.vue"
import { computed, ref, shallowRef, watchEffect } from "vue"
import { getTagColor } from "../data/issues"
import { call } from "frappe-ui"

// Enhanced status badge component with custom status values




const StatusBadge = {
	props: ["status"],
	template: `
    <Badge :label="displayStatus" :theme="statusTheme" variant="subtle" />
  `,
	computed: {
		displayStatus() {
			return this.status || "New"
		},
		statusTheme() {
			const status = this.status || "New"
			// Color mapping from issue_list.js to maintain consistency
			const statusThemes = {
				New: "blue", // 🔵 New issues - blue for fresh/attention needed
				"In Review": "orange", // 🟠 Under review - orange for active progress
				"Waiting on Customer": "yellow", // 🟡 Customer action needed - yellow for pause/wait
				Confirmed: "purple", // 🟣 Confirmed and validated - purple for approval
				"In Transit": "blue", // 🔷 Active transit - light-blue mapped to blue in Frappe UI
				"In Transit Unmanaged": "gray", // ⚫ Unmanaged transit - grey for limited control
				Delivered: "green", // 🟢 Successfully delivered - green for success
				Closed: "green", // 🟢 Fully completed - darkgreen mapped to green in Frappe UI

				// Legacy Status Support (backward compatibility)
				Open: "red", // 🔴 Legacy open state
				Replied: "orange", // 🟠 Legacy replied state
				"On Hold": "yellow", // 🟡 Legacy hold state
				Resolved: "green", // 🟢 Legacy resolved state
			}
			return statusThemes[status] || "gray"
		},
	},
	components: { Badge },
}

// Enhanced priority badge component with visual indicators
const PriorityBadge = {
	props: ["priority"],
	template: `
    <div class="flex items-center gap-2">
      <div :class="priorityIndicatorClass" class="w-2 h-2 rounded-full"></div>
      <Badge :label="displayPriority" :theme="priorityTheme" variant="subtle" />
    </div>
  `,
	computed: {
		displayPriority() {
			return this.priority || "Medium"
		},
		priorityTheme() {
			const priority = this.priority || "Medium"
			const priorityThemes = {
				Critical: "red",
				High: "red",
				Medium: "yellow",
				Low: "green",
			}
			return priorityThemes[priority] || "yellow"
		},
		priorityIndicatorClass() {
			const priority = this.priority || "Medium"
			return {
				"bg-red-500": priority === "Critical",
				"bg-red-400": priority === "High",
				"bg-yellow-400": priority === "Medium",
				"bg-green-400": priority === "Low",
			}
		},
	},
	components: { Badge },
}



export default {
	components: {
		ListView,
		Avatar,
		Badge,
		Button,
		FeatherIcon,
		ListHeader,
		ListHeaderItem,
		ListRow,
		ListRowItem,
		ListRows,
		ListSelectBanner,
		StatusBadge,
		PriorityBadge,
		Tooltip,
		Dialog,
	},
	props: {
		issues: {
			type: Array,
			default: () => [],
		},
		loading: {
			type: Boolean,
			default: false,
		},
		sortField: {
			type: String,
			default: "creation",
		},
		sortDirection: {
			type: String,
			default: "desc",
		},
	},
	emits: ["sort"],
	setup(props, { emit }) {
		// Popup state management
		const showPopup = ref(false)
		const popupUser = ref(null)
		const popupPosition = ref({ x: 0, y: 0 })

		// Tags popup state management
		const showTagsPopup = ref(false)
		const tagsPopupPosition = ref({ x: 0, y: 0 })
		const tagsPopupData = ref(null)

		// Communication dialog state management
		const showCommunicationDialog = ref(false)
		const selectedIssue = ref(null)
		const communications = ref([])
		const loadingCommunications = ref(false)

		// Helper methods
		const getInitials = (name) => {
			if (!name || typeof name !== "string") {
				return "?"
			}

			// If it's an email address, extract the part before @
			if (name.includes("@")) {
				const emailPart = name.split("@")[0]

				// If email part has dots or underscores, use those as separators
				if (emailPart.includes(".") || emailPart.includes("_")) {
					const parts = emailPart.split(/[._]/)
					return parts
						.map((part) => part[0])
						.join("")
						.toUpperCase()
						.slice(0, 2)
				}
				// Otherwise, take first 2 characters of email part
				return emailPart.slice(0, 2).toUpperCase()
			}

			// For regular names with spaces
			if (name.includes(" ")) {
				return name
					.split(" ")
					.map((n) => n[0])
					.join("")
					.toUpperCase()
					.slice(0, 2)
			}

			// For single words, take first 2 characters
			return name.slice(0, 2).toUpperCase()
		}

		// Format issue ID to show only year and serial number
		const formatIssueId = (issueId) => {
			if (!issueId) return ""
			// Extract year and serial from ISS-2025-000016 format
			const match = issueId.match(/ISS-(\d{4}-\d+)/)
			return match ? match[1] : issueId
		}


		const stripHtml = (html) => {
			if (!html) return "";
			
			// Handle string input that might not be HTML
			if (typeof html !== 'string') {
				return String(html);
			}
			
			try {
				// Create a temporary element to parse HTML
				const tmp = document.createElement("div");
				tmp.innerHTML = html;
				
				// Get all text content, which strips all HTML tags and attributes
				let textContent = tmp.textContent || tmp.innerText || "";
				
				// Clean up whitespace and return
				return textContent.replace(/\s+/g, ' ').trim();
			} catch (error) {
				// If there's any error, just return the original string
				console.warn('Error stripping HTML:', error);
				return String(html).replace(/\s+/g, ' ').trim();
			}
		}


		const formatDate = (dateString) => {
			if (!dateString) return "-"
			return new Date(dateString).toLocaleDateString("en-US", {
				year: "numeric",
				month: "short",
				day: "numeric",
			})
		}

		const formatTime = (dateString) => {
			if (!dateString) return ""
			return new Date(dateString).toLocaleTimeString("en-US", {
				hour: "2-digit",
				minute: "2-digit",
			})
		}

		// Helper function to get status color
		const getStatusBadgeColor = (status) => {
			const statusColors = {
				New: "blue",
				"In Review": "orange",
				"Waiting on Customer": "yellow",
				Confirmed: "purple",
				"In Transit": "blue",
				"In Transit Unmanaged": "gray",
				Delivered: "green",
				Closed: "green",
				Open: "red",
				Replied: "orange",
				"On Hold": "yellow",
				Resolved: "green",
			}
			return statusColors[status] || "gray"
		}

		// Helper function to get priority color
		const getPriorityBadgeColor = (priority) => {
			const priorityColors = {
				Critical: "red",
				High: "red",
				Medium: "yellow",
				Low: "green",
			}
			return priorityColors[priority] || "yellow"
		}

		// Memoized transformation cache to prevent unnecessary re-computations
		const transformationCache = new Map()
		
		// Transform issues data to include badge structure for ListView with memoization
		const transformedIssues = computed(() => {
			return props.issues.map((issue) => {
				// Use issue name as cache key since it's unique
				const cacheKey = issue.name
				
				// Check if we have a cached transformation for this issue
				if (transformationCache.has(cacheKey)) {
					const cached = transformationCache.get(cacheKey)
					// Verify the cached data is still valid (check all important fields)
					if (cached.originalStatus === issue.status && 
					    cached.originalPriority === issue.priority &&
					    cached.originalSubject === issue.subject &&
					    cached.originalUsersAssigned === JSON.stringify(issue.custom_users_assigned)) {
						return cached.transformed
					}
				}
				
				// Create new transformation
				const transformed = {
					...issue,
					status: {
						label: issue.status || "New",
						color: getStatusBadgeColor(issue.status),
					},
					priority: {
						label: issue.priority || "Medium",
						color: getPriorityBadgeColor(issue.priority),
					},
				}
				
				// Cache the transformation
				transformationCache.set(cacheKey, {
					transformed,
					originalStatus: issue.status,
					originalPriority: issue.priority,
					originalSubject: issue.subject,
					originalUsersAssigned: JSON.stringify(issue.custom_users_assigned)
				})
				
				return transformed
			})
		})

		// Static columns configuration (memoized since it never changes)
		const columns = shallowRef([
			{
				label: "Issue ID",
				key: "name",
				width: "110px",
				sortable: true,
			},
			{
				label: "Title",
				key: "subject",
				width: 4,
				sortable: true,
			},
			{
				label: "Status",
				key: "status",
				width: "160px",
				sortable: true,
			},
			{
				label: "Assignee",
				key: "raised_by",
				width: "150px",
				sortable: true,
			},
			{
				label: "Assigned Users",
				key: "custom_users_assigned",
				width: "180px",
				sortable: false,
			},
			{
				label: "Tags",
				key: "_user_tags",
				width: "120px",
				sortable: false,
			},
			{
				label: "Created At",
				key: "creation",
				width: "120px",
				sortable: true,
			},
		])

		// Static ListView options (memoized since they rarely change)
		const listOptions = shallowRef({
			showTooltip: true,
			selectable: true,
			resizeColumn: false,
			rowHeight: 60,
			emptyState: {
				title: "No issues found",
				description: "Try adjusting your search or filter criteria",
			},
			onRowClick: (row) => {
				// Handle row click
				console.log("Row clicked:", row)
			},
		})

		// Handle selections
		const handleSelections = (selections) => {
			console.log("Selected rows:", selections)
		}

		// Handle issue click
		const handleIssueClick = (issue) => {
			console.log("Issue clicked:", issue)
			// Navigate to Frappe issue page
			const hostname = window.location.origin
			const issueUrl = `${hostname}/app/issue/${issue.name}`
			window.open(issueUrl, '_blank')
		}

		// Get status color classes for indicator dots
		const getStatusColor = (status) => {
			const statusValue = status || "New"
			// Color mapping from issue_list.js to maintain consistency
			return {
				"bg-blue-500": statusValue === "New", // 🔵 New issues - blue for fresh/attention needed
				"bg-orange-500": statusValue === "In Review", // 🟠 Under review - orange for active progress
				"bg-yellow-500": statusValue === "Waiting on Customer", // 🟡 Customer action needed - yellow for pause/wait
				"bg-purple-500": statusValue === "Confirmed", // 🟣 Confirmed and validated - purple for approval
				"bg-blue-500": statusValue === "In Transit", // 🔷 Active transit - light-blue mapped to blue in Tailwind
				"bg-gray-500": statusValue === "In Transit Unmanaged", // ⚫ Unmanaged transit - grey for limited control
				"bg-green-500": statusValue === "Delivered", // 🟢 Successfully delivered - green for success
				"bg-green-500": statusValue === "Closed", // 🟢 Fully completed - darkgreen mapped to green in Tailwind

				// Legacy Status Support (backward compatibility)
				"bg-red-500": statusValue === "Open", // 🔴 Legacy open state
				"bg-orange-500": statusValue === "Replied", // 🟠 Legacy replied state
				"bg-yellow-500": statusValue === "On Hold", // 🟡 Legacy hold state
				"bg-green-500": statusValue === "Resolved", // 🟢 Legacy resolved state
			}
		}

		// Get priority color classes
		const getPriorityColor = (priority) => {
			const priorityValue = priority || "Medium"
			return {
				"bg-red-500": priorityValue === "Critical" || priorityValue === "High",
				"bg-yellow-500": priorityValue === "Medium",
				"bg-green-500": priorityValue === "Low",
			}
		}

		// Get status badge CSS classes
		const getStatusBadgeClass = (status) => {
			const statusValue = status || "New"
			const statusClasses = {
				New: "bg-blue-100 text-blue-800",
				"In Review": "bg-orange-100 text-orange-800",
				"Waiting on Customer": "bg-yellow-100 text-yellow-800",
				Confirmed: "bg-purple-100 text-purple-800",
				"In Transit": "bg-blue-100 text-blue-800",
				"In Transit Unmanaged": "bg-gray-100 text-gray-800",
				Delivered: "bg-green-100 text-green-800",
				Closed: "bg-green-100 text-green-800",
				Open: "bg-red-100 text-red-800",
				Replied: "bg-orange-100 text-orange-800",
				"On Hold": "bg-yellow-100 text-yellow-800",
				Resolved: "bg-green-100 text-green-800",
			}
			return statusClasses[statusValue] || "bg-gray-100 text-gray-800"
		}

		// Get priority badge CSS classes
		const getPriorityBadgeClass = (priority) => {
			const priorityValue = priority || "Medium"
			const priorityClasses = {
				Critical: "bg-red-100 text-red-800",
				High: "bg-red-100 text-red-800",
				Medium: "bg-yellow-100 text-yellow-800",
				Low: "bg-green-100 text-green-800",
			}
			return priorityClasses[priorityValue] || "bg-yellow-100 text-yellow-800"
		}

		// Get priority indicator dot CSS classes
		const getPriorityIndicatorClass = (priority) => {
			const priorityValue = priority || "Medium"
			return {
				"bg-red-500": priorityValue === "Critical",
				"bg-red-400": priorityValue === "High",
				"bg-yellow-400": priorityValue === "Medium",
				"bg-green-400": priorityValue === "Low",
			}
		}

		// Popup functions for user hover
		const showUserPopup = (event, user) => {
			const rect = event.target.getBoundingClientRect()
			popupPosition.value = {
				x: rect.left + rect.width / 2,
				y: rect.top - 10,
			}
			popupUser.value = user
			showPopup.value = true
		}

		const hideUserPopup = () => {
			showPopup.value = false
			popupUser.value = null
		}

		// Tags popup functions
		const showTagsPopupFn = (event, tags) => {
			if (!tags || tags.length === 0) return

			const rect = event.target.getBoundingClientRect()
			tagsPopupPosition.value = {
				x: rect.left + rect.width / 2,
				y: rect.top - 10,
			}
			tagsPopupData.value = tags
			showTagsPopup.value = true
		}

		const hideTagsPopupFn = () => {
			showTagsPopup.value = false
			tagsPopupData.value = null
		}

		// Communication dialog functions
		const openCommunicationDialog = async (issue) => {
			selectedIssue.value = issue
			showCommunicationDialog.value = true
			loadingCommunications.value = true
			communications.value = []
			
			try {
				const result = await call('force_trans_customization.api.issues.get_issue_communications', {
					issue_name: issue.name,
					limit: 5
				})
				
				communications.value = result || []
			} catch (error) {
				console.error('Error fetching communications:', error)
				communications.value = []
			} finally {
				loadingCommunications.value = false
			}
		}

		// Open issue in Frappe
		const openIssue = () => {
			if (selectedIssue.value?.name) {
				window.open(`/app/issue/${selectedIssue.value.name}`, '_blank');
			}

		}

		// Sorting functionality
		const handleColumnSort = (field) => {
			let newDirection = "asc"

			// If clicking the same field, toggle direction
			if (props.sortField === field) {
				newDirection = props.sortDirection === "asc" ? "desc" : "asc"
			}

			// Emit sort event to parent component
			emit("sort", { field, direction: newDirection })
		}

		const getSortIcon = (field) => {
			if (props.sortField !== field) {
				return "arrow-up-down" // Default unsorted icon
			}

			return props.sortDirection === "asc" ? "arrow-up" : "arrow-down"
		}

		const getSortIconClass = (field) => {
			if (props.sortField !== field) {
				return "text-gray-400" // Inactive sort icon
			}

			return "text-blue-600" // Active sort icon
		}

		const getSortButtonClass = (field) => {
			if (props.sortField === field) {
				return "bg-blue-50" // Active sort button background
			}

			return "" // Default button styling
		}

		// Memoized tag styling function to prevent recalculating colors
		const tagStyleCache = new Map()
		const getTagStyle = (tag) => {
			// Check cache first
			if (tagStyleCache.has(tag)) {
				return tagStyleCache.get(tag)
			}
			
			// Get tag color from API
			const hexColor = getTagColor(tag)
			let style

			if (hexColor) {
				// Convert hex color to RGB for background and text colors
				const hex = hexColor.replace('#', '')
				const r = parseInt(hex.substr(0, 2), 16)
				const g = parseInt(hex.substr(2, 2), 16)
				const b = parseInt(hex.substr(4, 2), 16)

				// Create background color (lighter version with opacity)
				const bgColor = `rgba(${r}, ${g}, ${b}, 0.1)`

				// Create text color (darker version for contrast)
				const textColor = `rgb(${Math.max(r - 50, 0)}, ${Math.max(g - 50, 0)}, ${Math.max(b - 50, 0)})`

				style = {
					backgroundColor: bgColor,
					color: textColor,
					borderColor: textColor
				}
			} else {
				// Fallback to default styling
				style = {
					backgroundColor: '#f3f4f6',
					color: '#374151',
					borderColor: '#d1d5db'
				}
			}
			
			// Cache the result
			tagStyleCache.set(tag, style)
			return style
		}

		// Get communication status theme for Frappe UI Badge
		const getCommunicationStatusTheme = (status) => {
			if (status === 'Sent') {
				return 'blue'
			} else if (status === 'Received') {
				return 'green'
			}
			return 'gray'
		}

		// Format date and time together
		const formatDateTime = (dateString) => {
			if (!dateString) return "-"
			const date = new Date(dateString)
			return date.toLocaleString("en-US", {
				year: "numeric",
				month: "short",
				day: "numeric",
				hour: "2-digit",
				minute: "2-digit",
			})
		}

		// Sanitize HTML content for communication display
		const sanitizeContent = (content) => {
			if (!content) return "";

			// Remove blockquote tags & their content
			let cleaned = content.replace(/<blockquote[\s\S]*?<\/blockquote>/gi, "");

			// Remove &nbsp;
			cleaned = cleaned.replace(/&nbsp;/gi, " ");

			// Remove multiple spaces & extra <p><br></p>
			cleaned = cleaned
				.replace(/\s+/g, " ") // collapse multiple spaces
				.replace(/<p><br><\/p>/gi, ""); // remove empty paragraphs

			// Optional: trim leading/trailing spaces
			cleaned = cleaned.trim();

			return cleaned;
		}

		return {
			columns,
			listOptions,
			transformedIssues,
			handleSelections,
			handleIssueClick,
			getStatusColor,
			getPriorityColor,
			getStatusBadgeClass,
			getPriorityBadgeClass,
			getPriorityIndicatorClass,
			getInitials,
			formatIssueId,
			stripHtml,
			formatDate,
			formatTime,
			showPopup,
			popupUser,
			popupPosition,
			showUserPopup,
			hideUserPopup,
			handleColumnSort,
			getSortIcon,
			getSortIconClass,
			getSortButtonClass,
			getTagStyle,
			getCommunicationStatusTheme,
			formatDateTime,
			sanitizeContent,
			showTagsPopup,
			tagsPopupPosition,
			tagsPopupData,
			showTagsPopupFn,
			hideTagsPopupFn,
			showCommunicationDialog,
			selectedIssue,
			communications,
			loadingCommunications,
			openCommunicationDialog,
			openIssue,
		}
	},
}
</script>

<style scoped>
.line-clamp-2 {
	display: -webkit-box;
	-webkit-line-clamp: 2;
	-webkit-box-orient: vertical;
	overflow: hidden;
}

/* Enhanced truncate for better ellipsis display */
.truncate {
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}

/* Ensure proper text display in description */
.description-text {
	max-width: 100%;
	display: block;
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
	line-height: 1.4;
}
</style>