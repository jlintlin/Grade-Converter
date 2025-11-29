<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  gradeData: { type: Object, required: true }
})

const searchQuery = ref('')
const sortColumn = ref('Student')
const sortDirection = ref('asc')
const currentPage = ref(1)
const pageSize = ref(50)
const sectionFilter = ref('all')

// Columns to always display (in order)
const primaryColumns = ['Student', 'ID', 'Section']

// All assignment columns
const assignmentColumns = computed(() => props.gradeData.assignment_columns || [])

// Unique sections from data
const sections = computed(() => props.gradeData.sections || [])

// Assignment info
const assignmentInfo = computed(() => props.gradeData.assignment_info || {})



// Filtered and sorted students
const filteredStudents = computed(() => {
  let students = [...props.gradeData.students]

  // Filter by section
  if (sectionFilter.value !== 'all') {
    students = students.filter(s => s.Section === sectionFilter.value)
  }

  // Filter by search query
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    students = students.filter(s =>
      Object.values(s).some(v => String(v).toLowerCase().includes(query))
    )
  }

  // Sort
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
  // For assignment columns, try to extract a cleaner name
  if (!primaryColumns.includes(col)) {
    // Remove common Canvas suffixes like (12345) assignment IDs
    const cleaned = col.replace(/\s*\(\d+\)\s*$/, '').trim()
    return cleaned.length > 25 ? cleaned.substring(0, 25) + '...' : cleaned
  }
  return col
}

function getPointsPossible(col) {
  return assignmentInfo.value[col]?.points_possible
}

// Calculate percentage for a cell value
function calculatePercentage(value, col) {
  if (value === null || value === undefined || value === '') return null
  const pointsPossible = getPointsPossible(col)
  if (!pointsPossible || pointsPossible <= 0) return null
  const num = Number.parseFloat(value)
  if (Number.isNaN(num)) return null
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
  return percentage.toFixed(0) + '%'
}

// Get color class based on percentage
function getPercentageClass(value, col) {
  if (primaryColumns.includes(col)) return ''
  const percentage = calculatePercentage(value, col)
  if (percentage === null) return 'text-base-content/40'
  if (percentage >= 90) return 'text-success font-semibold'
  if (percentage >= 80) return 'text-info'
  if (percentage >= 70) return 'text-warning'
  if (percentage >= 60) return 'text-orange-500'
  return 'text-error'
}

function goToPage(page) {
  if (page >= 1 && page <= totalPages.value) currentPage.value = page
}
</script>

<template>
  <div class="w-full h-full flex flex-col gap-4">
    <!-- Header with summary and filters -->
    <div class="bg-base-100 rounded-xl border border-base-200 p-4 shadow-sm shrink-0">
      <div class="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <!-- Title and summary -->
        <div>
          <h2 class="text-xl font-bold flex items-center gap-2">
            📋 Grade Overview
          </h2>
          <p class="text-sm text-base-content/60 mt-1">
            {{ filteredStudents.length }} of {{ gradeData.row_count }} students •
            {{ assignmentColumns.length }} assignments •
            {{ sections.length }} section(s)
          </p>
        </div>

        <!-- Filters row -->
        <div class="flex flex-wrap items-center gap-3">
          <!-- Search -->
          <div class="join shadow-sm">
            <div class="join-item flex items-center px-3 bg-base-200 border border-base-300 border-r-0">
              <svg class="h-4 w-4 opacity-70" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
            <input v-model="searchQuery" type="text"
                   class="input input-bordered input-sm join-item w-48 lg:w-64 focus:outline-none"
                   placeholder="Search students..." />
          </div>
        </div>
      </div>

      <!-- Section badges summary -->
      <div v-if="sections.length > 0" class="flex flex-wrap items-center gap-2 mt-3 pt-3 border-t border-base-200">
        <span class="text-xs font-medium text-base-content/50 uppercase tracking-wider">Quick Filter:</span>
        <button v-for="sec in sections" :key="sec"
                @click="sectionFilter = sectionFilter === sec ? 'all' : sec"
                :class="['badge gap-1 cursor-pointer transition-all', sectionFilter === sec ? 'badge-primary shadow-md' : 'badge-ghost hover:bg-base-200']">
          {{ sec }}
          <span class="opacity-60 text-xs">({{ gradeData.students.filter(s => s.Section === sec).length }})</span>
        </button>
      </div>
    </div>

    <!-- Excel-like scrollable table container -->
    <div class="flex-1 min-h-0 relative overflow-hidden bg-base-100 border border-base-200 rounded-xl shadow-sm flex flex-col">
      <div class="flex-1 overflow-auto custom-scrollbar">
        <table class="w-full border-collapse text-sm">
          <thead class="sticky top-0 z-30">
            <tr class="bg-base-100 shadow-sm">
              <!-- Frozen student name column -->
              <th class="sticky left-0 z-40 bg-base-100 min-w-[200px] max-w-[250px] px-4 py-3 text-left border-b border-r border-base-200 shadow-[4px_0_8px_-2px_rgba(0,0,0,0.05)]">
                <button @click="toggleSort('Student')" class="flex items-center gap-1 hover:text-primary font-bold transition-colors w-full">
                  <span class="truncate">Student</span>
                  <svg v-if="sortColumn === 'Student'" class="h-3 w-3 text-primary transition-transform duration-200 flex-shrink-0" :class="sortDirection === 'desc' ? 'rotate-180' : ''" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 15l7-7 7 7" />
                  </svg>
                  <svg v-else class="h-3 w-3 opacity-20 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
                  </svg>
                </button>
              </th>
              <!-- ID column -->
              <th class="bg-base-100 min-w-[100px] px-3 py-3 text-left border-b border-r border-base-200">
                <button @click="toggleSort('ID')" class="flex items-center gap-1 hover:text-primary font-semibold text-xs transition-colors">
                  ID
                  <svg v-if="sortColumn === 'ID'" class="h-3 w-3 text-primary transition-transform duration-200" :class="sortDirection === 'desc' ? 'rotate-180' : ''" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 15l7-7 7 7" />
                  </svg>
                </button>
              </th>
              <!-- Assignment columns -->
              <th v-for="col in assignmentColumns" :key="col"
                  @click="toggleSort(col)"
                  class="bg-base-100 cursor-pointer hover:bg-base-200/50 transition-colors px-2 py-2 text-center border-b border-r border-base-200 min-w-[120px] max-w-[150px] group relative">
                <div class="flex flex-col gap-0.5 items-center w-full">
                  <div class="flex items-center justify-center gap-1 text-xs font-semibold w-full" :title="col">
                    <span class="truncate block max-w-full">{{ getShortColumnName(col) }}</span>
                    <svg v-if="sortColumn === col" class="h-3 w-3 text-primary flex-shrink-0 transition-transform duration-200" :class="sortDirection === 'desc' ? 'rotate-180' : ''" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 15l7-7 7 7" />
                    </svg>
                  </div>
                  <span v-if="getPointsPossible(col)" class="badge badge-xs badge-ghost font-normal opacity-70">
                    {{ getPointsPossible(col) }} pts
                  </span>
                </div>
              </th>
            </tr>
          </thead>
          <tbody class="bg-base-100">
            <tr v-for="(student, idx) in paginatedStudents" :key="idx"
                class="group hover:bg-base-200/50 transition-colors border-b border-base-100 last:border-0">
              <!-- Frozen student name -->
              <td class="sticky left-0 z-20 px-4 py-2 font-medium border-r border-base-200 bg-base-100 group-hover:bg-base-200/50 transition-colors shadow-[4px_0_8px_-2px_rgba(0,0,0,0.05)] truncate max-w-[250px]" :title="student.Student">
                {{ student.Student || '-' }}
              </td>
              <!-- ID -->
              <td class="px-3 py-2 text-xs text-base-content/60 border-r border-base-200 tabular-nums font-mono">
                {{ student.ID || '-' }}
              </td>
              <!-- Assignment scores -->
              <td v-for="col in assignmentColumns" :key="col"
                  class="px-2 py-2 text-center tabular-nums text-sm border-r border-base-200/50">
                <span :class="['font-medium', getPercentageClass(student[col], col)]">
                  {{ formatCellValue(student[col], col) }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Pagination footer -->
      <div class="bg-base-100 border-t border-base-200 p-4 shrink-0">
        <div class="flex flex-col sm:flex-row items-center justify-between gap-4">
          <div class="flex items-center gap-2">
            <span class="text-sm text-base-content/60">Rows:</span>
            <select v-model="pageSize" @change="currentPage = 1" class="select select-bordered select-sm w-20 bg-base-100">
              <option :value="25">25</option>
              <option :value="50">50</option>
              <option :value="100">100</option>
              <option :value="200">200</option>
            </select>
            <span class="text-sm text-base-content/60 ml-2">
              Page {{ currentPage }} of {{ totalPages }} ({{ filteredStudents.length }} total)
            </span>
          </div>
          <div class="flex items-center gap-2">
            <button @click="goToPage(1)" :disabled="currentPage === 1" class="btn btn-sm btn-outline border-base-300 hover:border-primary hover:bg-primary hover:text-white" title="First Page">
              <span class="hidden sm:inline">First</span>
              <span class="sm:hidden">«</span>
            </button>
            <button @click="goToPage(currentPage - 1)" :disabled="currentPage === 1" class="btn btn-sm btn-outline border-base-300 hover:border-primary hover:bg-primary hover:text-white" title="Previous Page">
              <span class="hidden sm:inline">Previous</span>
              <span class="sm:hidden">‹</span>
            </button>
            
            <div class="flex items-center px-2 font-mono text-sm font-bold">
               {{ currentPage }} / {{ totalPages }}
            </div>

            <button @click="goToPage(currentPage + 1)" :disabled="currentPage >= totalPages" class="btn btn-sm btn-outline border-base-300 hover:border-primary hover:bg-primary hover:text-white" title="Next Page">
              <span class="hidden sm:inline">Next</span>
              <span class="sm:hidden">›</span>
            </button>
            <button @click="goToPage(totalPages)" :disabled="currentPage >= totalPages" class="btn btn-sm btn-outline border-base-300 hover:border-primary hover:bg-primary hover:text-white" title="Last Page">
              <span class="hidden sm:inline">Last</span>
              <span class="sm:hidden">»</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

