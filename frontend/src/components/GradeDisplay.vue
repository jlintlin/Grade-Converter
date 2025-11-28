<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  gradeData: { type: Object, required: true }
})

const searchQuery = ref('')
const sortColumn = ref('Student')
const sortDirection = ref('asc')
const currentPage = ref(1)
const pageSize = ref(25)
const visibleAssignmentCount = ref(8)

// Columns to always display (in order)
const primaryColumns = ['Student', 'ID', 'SIS User ID', 'SIS Login ID']

// Display columns - metadata + visible assignments
const displayColumns = computed(() => {
  const cols = primaryColumns.filter(c => props.gradeData.metadata_columns?.includes(c))
  const assignments = props.gradeData.assignment_columns?.slice(0, visibleAssignmentCount.value) || []
  return [...cols, ...assignments]
})

// All assignment columns
const assignmentColumns = computed(() => props.gradeData.assignment_columns || [])

// Unique sections from data
const sections = computed(() => props.gradeData.sections || [])

// Assignment info
const assignmentInfo = computed(() => props.gradeData.assignment_info || {})

// Filtered and sorted students
const filteredStudents = computed(() => {
  let students = [...props.gradeData.students]
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    students = students.filter(s =>
      Object.values(s).some(v => String(v).toLowerCase().includes(query))
    )
  }
  students.sort((a, b) => {
    const valA = a[sortColumn.value] || ''
    const valB = b[sortColumn.value] || ''
    const comparison = String(valA).localeCompare(String(valB), undefined, { numeric: true })
    return sortDirection.value === 'asc' ? comparison : -comparison
  })
  return students
})

// Paginated students
const paginatedStudents = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return filteredStudents.value.slice(start, start + pageSize.value)
})

const totalPages = computed(() => Math.ceil(filteredStudents.value.length / pageSize.value))

// Check if there are more assignments to show
const hasMoreAssignments = computed(() =>
  visibleAssignmentCount.value < assignmentColumns.value.length
)

// Check if showing all assignments
const showingAllAssignments = computed(() =>
  visibleAssignmentCount.value >= assignmentColumns.value.length
)

function toggleSort(column) {
  if (sortColumn.value === column) {
    sortDirection.value = sortDirection.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortColumn.value = column
    sortDirection.value = 'asc'
  }
  currentPage.value = 1
}

function getShortColumnName(col) {
  return col.length > 20 ? col.substring(0, 20) + '...' : col
}

function getPointsPossible(col) {
  return assignmentInfo.value[col]?.points_possible
}

// Calculate percentage for a cell value
function calculatePercentage(value, col) {
  if (value === null || value === undefined || value === '') return null
  const pointsPossible = getPointsPossible(col)
  if (!pointsPossible || pointsPossible <= 0) return null
  const num = parseFloat(value)
  if (isNaN(num)) return null
  return (num / pointsPossible) * 100
}

// Format cell value as percentage or dash
function formatCellValue(value, col) {
  // Check if this is a metadata column
  if (primaryColumns.includes(col)) {
    return value === null || value === undefined || value === '' ? '-' : value
  }

  // For assignment columns, show percentage
  const percentage = calculatePercentage(value, col)
  if (percentage === null) return '-'
  return percentage.toFixed(1) + '%'
}

// Get color class based on percentage
function getPercentageClass(value, col) {
  if (primaryColumns.includes(col)) return ''
  const percentage = calculatePercentage(value, col)
  if (percentage === null) return 'text-gray-400'
  if (percentage >= 90) return 'text-emerald-600 font-medium'
  if (percentage >= 80) return 'text-blue-600'
  if (percentage >= 70) return 'text-yellow-600'
  if (percentage >= 60) return 'text-orange-600'
  return 'text-red-600'
}

function showMoreAssignments() {
  visibleAssignmentCount.value = Math.min(
    visibleAssignmentCount.value + 8,
    assignmentColumns.value.length
  )
}

function showFewerAssignments() {
  visibleAssignmentCount.value = Math.max(8, visibleAssignmentCount.value - 8)
}

function goToPage(page) {
  if (page >= 1 && page <= totalPages.value) currentPage.value = page
}
</script>

<template>
  <div class="bg-white rounded-xl shadow-lg p-6">
    <!-- Header with summary info -->
    <div class="flex flex-col md:flex-row md:items-center justify-between mb-6 gap-4">
      <div>
        <h2 class="text-2xl font-bold text-gray-800">Grade Overview</h2>
        <p class="text-sm text-gray-500 mt-1">
          {{ gradeData.row_count }} students • {{ assignmentColumns.length }} assignments
        </p>
      </div>
      <div class="relative">
        <input v-model="searchQuery" type="text" placeholder="Search students..."
          class="pl-10 pr-4 py-2.5 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 w-72 bg-gray-50" />
        <svg class="absolute left-3 top-3 h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
      </div>
    </div>

    <!-- Section Summary -->
    <div v-if="sections.length > 0" class="mb-4 p-4 bg-gradient-to-r from-gray-50 to-gray-100 rounded-lg border border-gray-200">
      <div class="flex items-center gap-2">
        <svg class="w-5 h-5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
        </svg>
        <span class="text-sm font-semibold text-gray-700">Sections:</span>
        <div class="flex flex-wrap gap-2">
          <span v-for="sec in sections" :key="sec"
                class="px-3 py-1 bg-white text-sm text-gray-600 rounded-full border border-gray-200 shadow-sm">
            {{ sec }}
          </span>
        </div>
      </div>
    </div>

    <!-- Assignment Summary -->
    <div class="mb-6 p-4 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg border border-blue-100">
      <div class="flex items-center justify-between mb-3">
        <div class="flex items-center gap-2">
          <svg class="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
          </svg>
          <span class="text-sm font-semibold text-blue-800">
            Assignments ({{ assignmentColumns.length }})
          </span>
        </div>
        <div class="flex items-center gap-2">
          <button v-if="!showingAllAssignments" @click="showMoreAssignments"
            class="px-3 py-1.5 text-xs font-medium text-blue-600 bg-blue-100 hover:bg-blue-200 rounded-lg transition">
            Show More (+8)
          </button>
          <button v-if="visibleAssignmentCount > 8" @click="showFewerAssignments"
            class="px-3 py-1.5 text-xs font-medium text-gray-600 bg-gray-100 hover:bg-gray-200 rounded-lg transition">
            Show Less
          </button>
        </div>
      </div>
      <div class="flex flex-wrap gap-2 max-h-32 overflow-y-auto">
        <span v-for="col in assignmentColumns" :key="col"
              class="px-3 py-1 text-xs bg-white text-blue-700 rounded-full border border-blue-200 shadow-sm cursor-default"
              :title="`${col} (${getPointsPossible(col) || '?'} pts)`">
          {{ col.length > 25 ? col.substring(0, 25) + '...' : col }}
          <span v-if="getPointsPossible(col)" class="text-blue-400 ml-1">({{ getPointsPossible(col) }})</span>
        </span>
      </div>
      <p class="text-xs text-blue-600 mt-3 flex items-center gap-1">
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        Displaying {{ Math.min(visibleAssignmentCount, assignmentColumns.length) }} of {{ assignmentColumns.length }} assignments • Percentages shown below
      </p>
    </div>

    <!-- Table -->
    <div class="overflow-x-auto border border-gray-200 rounded-xl shadow-sm">
      <table class="min-w-full">
        <thead class="bg-gradient-to-r from-gray-50 to-gray-100">
          <tr>
            <th v-for="col in displayColumns" :key="col" @click="toggleSort(col)"
              class="px-4 py-3 text-left text-xs font-bold text-gray-600 uppercase tracking-wider cursor-pointer hover:bg-gray-100 transition whitespace-nowrap border-b border-gray-200">
              <div class="flex flex-col gap-0.5">
                <div class="flex items-center gap-1">
                  <span :title="col">{{ getShortColumnName(col) }}</span>
                  <svg v-if="sortColumn === col" class="h-3 w-3 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path v-if="sortDirection === 'asc'" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 15l7-7 7 7" />
                    <path v-else stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                  </svg>
                </div>
                <span v-if="getPointsPossible(col)" class="text-[10px] font-normal text-gray-400 normal-case">
                  {{ getPointsPossible(col) }} pts
                </span>
              </div>
            </th>
          </tr>
        </thead>
        <tbody class="bg-white divide-y divide-gray-100">
          <tr v-for="(student, idx) in paginatedStudents" :key="idx"
              class="hover:bg-blue-50/50 transition-colors"
              :class="idx % 2 === 0 ? 'bg-white' : 'bg-gray-50/50'">
            <td v-for="col in displayColumns" :key="col"
                class="px-4 py-3 text-sm whitespace-nowrap"
                :class="getPercentageClass(student[col], col)">
              {{ formatCellValue(student[col], col) }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Pagination -->
    <div class="mt-6 flex flex-col sm:flex-row items-center justify-between gap-4 p-4 bg-gray-50 rounded-lg">
      <div class="flex items-center gap-3">
        <span class="text-sm text-gray-600">Show</span>
        <select v-model="pageSize" @change="currentPage = 1"
          class="border border-gray-200 rounded-lg px-3 py-2 text-sm bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
          <option :value="25">25</option>
          <option :value="50">50</option>
          <option :value="100">100</option>
        </select>
        <span class="text-sm text-gray-600">per page</span>
      </div>
      <div class="flex items-center gap-2">
        <button @click="goToPage(1)" :disabled="currentPage === 1"
          class="px-3 py-2 text-sm border border-gray-200 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-white transition bg-white">
          First
        </button>
        <button @click="goToPage(currentPage - 1)" :disabled="currentPage === 1"
          class="px-3 py-2 text-sm border border-gray-200 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-white transition bg-white">
          Prev
        </button>
        <span class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-200 rounded-lg">
          {{ currentPage }} / {{ totalPages }}
        </span>
        <button @click="goToPage(currentPage + 1)" :disabled="currentPage >= totalPages"
          class="px-3 py-2 text-sm border border-gray-200 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-white transition bg-white">
          Next
        </button>
        <button @click="goToPage(totalPages)" :disabled="currentPage >= totalPages"
          class="px-3 py-2 text-sm border border-gray-200 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-white transition bg-white">
          Last
        </button>
      </div>
      <span class="text-sm text-gray-500 font-medium">{{ filteredStudents.length }} total students</span>
    </div>
  </div>
</template>

