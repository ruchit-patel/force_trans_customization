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
    <ListView v-else :columns="columns" :rows="issues" row-key="name" :options="listOptions"
      @update:selections="handleSelections">

      <ListHeader>
        <ListHeaderItem v-for="column in columns" :key="column.key" :item="column">
          <template v-if="column.icon" #prefix="{ item }">
            <FeatherIcon :name="item.icon" class="h-4 w-4" />
          </template>
        </ListHeaderItem>
      </ListHeader>

      <ListRows>
        <ListRow v-for="issue in issues" :key="issue.name" :row="issue">
          <template #default="{ column, item }">
            <ListRowItem :item="item" :align="column.align">
              <template #prefix>
                <!-- Avatar for assignee column -->
                <Avatar v-if="column.key === 'raised_by'" :size="'sm'" :label="getInitials(issue.raised_by)"
                  class="mr-3" />
                <!-- Status indicator dot -->
                <div v-else-if="column.key === 'status'" class="h-3 w-3 rounded-full mr-2"
                  :class="getStatusColor(issue.status)" />
                <!-- Priority indicator dot -->
                <div v-else-if="column.key === 'priority'" class="h-3 w-3 rounded-full mr-2"
                  :class="getPriorityColor(issue.priority)" />
              </template>

              <!-- Custom content for each column -->
              <template #default>
                <!-- Issue ID with link -->
                <a v-if="column.key === 'name'" href="#"
                  class="text-blue-600 hover:text-blue-800 hover:underline font-medium"
                  @click.prevent="handleIssueClick(issue)">
                  {{ formatIssueId(item) }}
                </a>

                <!-- Title with description -->
                <div v-else-if="column.key === 'subject'" class="max-w-xs">
                  <div class="font-medium truncate" :title="issue.subject">{{ issue.subject }}</div>
                  <div v-if="issue.description" class="text-gray-500 text-xs mt-1 truncate" :title="issue.description">
                    {{ stripHtml(issue.description) }}
                  </div>
                </div>

                <!-- Status badge -->
                <StatusBadge v-else-if="column.key === 'status'" :status="item" />

                <!-- Priority badge -->
                <PriorityBadge v-else-if="column.key === 'priority'" :priority="item" />

                <!-- Assignee name -->
                <span v-else-if="column.key === 'raised_by'" class="text-sm font-medium text-gray-900">
                  {{ item || '-' }}
                </span>

                <!-- Project -->
                <span v-else-if="column.key === 'project'">{{ item || '-' }}</span>

                <!-- Tags -->
                <IssueTypeBadge v-else-if="column.key === 'issue_type'" :issueType="item" />

                <!-- Created At with date and time -->
                <div v-else-if="column.key === 'creation'" class="flex flex-col">
                  <span>{{ formatDate(item) }}</span>
                  <span class="text-xs text-gray-400">{{ formatTime(item) }}</span>
                </div>

                <!-- Default fallback -->
                <span v-else>{{ item }}</span>
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
  </div>
</template>

<script>
import { computed } from 'vue'
import { ListView, Avatar, Badge, Button, FeatherIcon } from 'frappe-ui'
import ListHeader from 'frappe-ui/src/components/ListView/ListHeader.vue'
import ListHeaderItem from 'frappe-ui/src/components/ListView/ListHeaderItem.vue'
import ListRow from 'frappe-ui/src/components/ListView/ListRow.vue'
import ListRowItem from 'frappe-ui/src/components/ListView/ListRowItem.vue'
import ListRows from 'frappe-ui/src/components/ListView/ListRows.vue'
import ListSelectBanner from 'frappe-ui/src/components/ListView/ListSelectBanner.vue'

// Enhanced status badge component with improved color coding
const StatusBadge = {
  props: ['status'],
  template: `
    <Badge :label="displayStatus" :theme="statusTheme" variant="subtle" />
  `,
  computed: {
    displayStatus() {
      return this.status || 'Open'
    },
    statusTheme() {
      const status = this.status || 'Open'
      const statusThemes = {
        'Open': 'blue',
        'Replied': 'yellow', 
        'On Hold': 'orange',
        'Resolved': 'green',
        'Closed': 'gray'
      }
      return statusThemes[status] || 'blue'
    }
  },
  components: { Badge }
}

// Enhanced priority badge component with visual indicators
const PriorityBadge = {
  props: ['priority'],
  template: `
    <div class="flex items-center gap-2">
      <div :class="priorityIndicatorClass" class="w-2 h-2 rounded-full"></div>
      <Badge :label="displayPriority" :theme="priorityTheme" variant="subtle" />
    </div>
  `,
  computed: {
    displayPriority() {
      return this.priority || 'Medium'
    },
    priorityTheme() {
      const priority = this.priority || 'Medium'
      const priorityThemes = {
        'Critical': 'red',
        'High': 'red',
        'Medium': 'yellow',
        'Low': 'green'
      }
      return priorityThemes[priority] || 'yellow'
    },
    priorityIndicatorClass() {
      const priority = this.priority || 'Medium'
      return {
        'bg-red-500': priority === 'Critical',
        'bg-red-400': priority === 'High',
        'bg-yellow-400': priority === 'Medium',
        'bg-green-400': priority === 'Low'
      }
    }
  },
  components: { Badge }
}

// Issue type badge component for tags display
const IssueTypeBadge = {
  props: ['issueType'],
  template: `
    <div v-if="issueType" class="flex items-center">
      <Badge :label="issueType" :theme="issueTypeTheme" variant="subtle" />
    </div>
    <span v-else class="text-gray-400 text-sm">-</span>
  `,
  computed: {
    issueTypeTheme() {
      const type = this.issueType
      if (!type) return 'gray'
      
      // Color coding based on common issue types
      const typeThemes = {
        'Bug': 'red',
        'Feature': 'blue',
        'Enhancement': 'green',
        'Task': 'purple',
        'Support': 'orange',
        'Question': 'yellow',
        'Documentation': 'gray'
      }
      
      // Check for partial matches if exact match not found
      for (const [key, theme] of Object.entries(typeThemes)) {
        if (type.toLowerCase().includes(key.toLowerCase())) {
          return theme
        }
      }
      
      return 'gray' // Default theme
    }
  },
  components: { Badge }
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
    IssueTypeBadge
  },
  props: {
    issues: {
      type: Array,
      default: () => []
    },
    loading: {
      type: Boolean,
      default: false
    },
    sortField: {
      type: String,
      default: 'creation'
    },
    sortDirection: {
      type: String,
      default: 'desc'
    }
  },
  emits: ['sort'],
  setup(props, { emit }) {
    // Helper methods
    const getInitials = (name) => {
      if (!name) return '?'
      return name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)
    }

    // Format issue ID to show only year and serial number
    const formatIssueId = (issueId) => {
      if (!issueId) return ''
      // Extract year and serial from ISS-2025-000016 format
      const match = issueId.match(/ISS-(\d{4}-\d+)/)
      return match ? match[1] : issueId
    }

    const stripHtml = (html) => {
      if (!html) return ''
      const tmp = document.createElement('div')
      tmp.innerHTML = html
      return tmp.textContent || tmp.innerText || ''
    }

    const formatDate = (dateString) => {
      if (!dateString) return '-'
      return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      })
    }

    const formatTime = (dateString) => {
      if (!dateString) return ''
      return new Date(dateString).toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit'
      })
    }

    // ListView columns configuration
    const columns = computed(() => [
      {
        label: 'Issue ID',
        key: 'name',
        width: '110px'
      },
      {
        label: 'Title',
        key: 'subject',
        width: 4
      },
      {
        label: 'Status',
        key: 'status',
        width: '100px'
      },
      {
        label: 'Priority',
        key: 'priority',
        width: '100px'
      },
      {
        label: 'Assignee',
        key: 'raised_by',
        width: '150px'
      },
      {
        label: 'Project',
        key: 'project',
        width: '120px'
      },
      {
        label: 'Tags',
        key: 'issue_type',
        width: '100px'
      },
      {
        label: 'Created At',
        key: 'creation',
        width: '120px'
      }
    ])

    // ListView options
    const listOptions = computed(() => ({
      showTooltip: true,
      selectable: true,
      resizeColumn: false,
      rowHeight: 60,
      emptyState: {
        title: 'No issues found',
        description: 'Try adjusting your search or filter criteria'
      },
      onRowClick: (row) => {
        // Handle row click
        console.log('Row clicked:', row)
      }
    }))

    // Handle selections
    const handleSelections = (selections) => {
      console.log('Selected rows:', selections)
    }

    // Handle issue click
    const handleIssueClick = (issue) => {
      console.log('Issue clicked:', issue)
      // TODO: Navigate to issue detail or emit event
    }

    // Get status color classes
    const getStatusColor = (status) => {
      const statusValue = status || 'Open'
      return {
        'bg-blue-500': statusValue === 'Open',
        'bg-yellow-500': statusValue === 'Replied',
        'bg-orange-500': statusValue === 'On Hold',
        'bg-green-500': statusValue === 'Resolved',
        'bg-gray-500': statusValue === 'Closed'
      }
    }

    // Get priority color classes
    const getPriorityColor = (priority) => {
      const priorityValue = priority || 'Medium'
      return {
        'bg-red-500': priorityValue === 'Critical' || priorityValue === 'High',
        'bg-yellow-500': priorityValue === 'Medium',
        'bg-green-500': priorityValue === 'Low'
      }
    }

    return {
      columns,
      listOptions,
      handleSelections,
      handleIssueClick,
      getStatusColor,
      getPriorityColor,
      getInitials,
      formatIssueId,
      stripHtml,
      formatDate,
      formatTime
    }
  }
}
</script>
