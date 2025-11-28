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
  <div class="w-full">
    <!-- Header with summary and filters -->
    <div class="bg-base-100 rounded-t-box border border-base-300 p-4">
      <div class="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <!-- Title and summary -->
        <div>
          <h2 class="text-2xl font-bold flex items-center gap-2">
            📋 Grade Overview
          </h2>
          <p class="text-base-content/60 mt-1">
            {{ filteredStudents.length }} of {{ gradeData.row_count }} students •
            {{ assignmentColumns.length }} assignments •
            {{ sections.length }} section(s)
          </p>
        </div>

        <!-- Filters row -->
        <div class="flex flex-wrap items-center gap-3">
          <!-- Section filter -->
          <div v-if="sections.length > 1" class="flex items-center gap-2">
            <span class="text-sm text-base-content/60">Section:</span>
            <select v-model="sectionFilter" class="select select-bordered select-sm">
              <option value="all">All Sections</option>
              <option v-for="sec in sections" :key="sec" :value="sec">{{ sec }}</option>
            </select>
          </div>

          <!-- Search -->
          <div class="join">
            <div class="join-item flex items-center px-3 bg-base-200">
              <svg class="h-4 w-4 opacity-70" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
            <input v-model="searchQuery" type="text"
                   class="input input-bordered input-sm join-item w-48 lg:w-64"
                   placeholder="Search students..." />
          </div>
        </div>
      </div>

      <!-- Section badges summary -->
      <div v-if="sections.length > 0" class="flex flex-wrap items-center gap-2 mt-3 pt-3 border-t border-base-200">
        <span class="text-sm text-base-content/60">Sections:</span>
        <button v-for="sec in sections" :key="sec"
                @click="sectionFilter = sectionFilter === sec ? 'all' : sec"
                :class="['badge gap-1 cursor-pointer transition-all', sectionFilter === sec ? 'badge-primary' : 'badge-outline hover:badge-primary/50']">
          {{ sec }}
          <span class="opacity-60">({{ gradeData.students.filter(s => s.Section === sec).length }})</span>
        </button>
      </div>
    </div>

    <!-- Excel-like scrollable table container -->
    <div class="relative overflow-auto bg-base-100 border-x border-base-300 max-h-[600px]">
      <table class="w-full border-collapse">
        <thead class="sticky top-0 z-30">
          <tr class="bg-base-200/95 backdrop-blur-sm">
            <!-- Frozen student name column -->
            <th class="sticky left-0 z-40 bg-base-200/95 backdrop-blur-sm min-w-[220px] px-3 py-2 text-left border-b-2 border-r-2 border-base-300 shadow-[2px_0_4px_rgba(0,0,0,0.1)]">
              <button @click="toggleSort('Student')" class="flex items-center gap-1 hover:text-primary font-semibold">
                <svg class="w-4 h-4 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
                Student
                <svg v-if="sortColumn === 'Student'" class="h-3 w-3 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path v-if="sortDirection === 'asc'" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 15l7-7 7 7" />
                  <path v-else stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                </svg>
              </button>
            </th>
            <!-- ID column -->
            <th class="bg-base-200/95 backdrop-blur-sm min-w-[80px] px-2 py-2 text-left border-b-2 border-r border-base-300">
              <button @click="toggleSort('ID')" class="flex items-center gap-1 hover:text-primary font-semibold text-xs">
                ID
                <svg v-if="sortColumn === 'ID'" class="h-3 w-3 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path v-if="sortDirection === 'asc'" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 15l7-7 7 7" />
                  <path v-else stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                </svg>
              </button>
            </th>
            <!-- Section column -->
            <th v-if="sections.length > 0" class="bg-base-200/95 backdrop-blur-sm min-w-[100px] px-2 py-2 text-left border-b-2 border-r border-base-300">
              <button @click="toggleSort('Section')" class="flex items-center gap-1 hover:text-primary font-semibold text-xs">
                Section
                <svg v-if="sortColumn === 'Section'" class="h-3 w-3 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path v-if="sortDirection === 'asc'" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 15l7-7 7 7" />
                  <path v-else stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                </svg>
              </button>
            </th>
            <!-- Assignment columns -->
            <th v-for="col in assignmentColumns" :key="col"
                @click="toggleSort(col)"
                class="bg-base-200/95 backdrop-blur-sm cursor-pointer hover:bg-base-300/95 transition px-2 py-2 text-center border-b-2 border-r border-base-300 min-w-[85px]">
              <div class="flex flex-col gap-0.5">
                <span class="flex items-center justify-center gap-1 text-xs font-semibold" :title="col">
                  {{ getShortColumnName(col) }}
                  <svg v-if="sortColumn === col" class="h-3 w-3 text-primary flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path v-if="sortDirection === 'asc'" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 15l7-7 7 7" />
                    <path v-else stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                  </svg>
                </span>
                <span v-if="getPointsPossible(col)" class="text-[10px] font-normal opacity-50">
                  {{ getPointsPossible(col) }} pts
                </span>
              </div>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(student, idx) in paginatedStudents" :key="idx"
              :class="['hover:bg-primary/5 transition-colors', idx % 2 === 0 ? 'bg-base-100' : 'bg-base-50']">
            <!-- Frozen student name -->
            <td class="sticky left-0 z-20 px-3 py-1.5 font-medium border-r-2 border-b border-base-300 shadow-[2px_0_4px_rgba(0,0,0,0.05)]"
                :class="idx % 2 === 0 ? 'bg-base-100' : 'bg-base-50'">
              {{ student.Student || '-' }}
            </td>
            <!-- ID -->
            <td class="px-2 py-1.5 text-xs text-base-content/60 border-r border-b border-base-200 tabular-nums">
              {{ student.ID || '-' }}
            </td>
            <!-- Section -->
            <td v-if="sections.length > 0" class="px-2 py-1.5 text-xs text-base-content/70 border-r border-b border-base-200">
              {{ student.Section || '-' }}
            </td>
            <!-- Assignment scores -->
            <td v-for="col in assignmentColumns" :key="col"
                class="px-2 py-1.5 text-center tabular-nums text-sm border-r border-b border-base-200"
                :class="getPercentageClass(student[col], col)">
              {{ formatCellValue(student[col], col) }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Pagination footer -->
    <div class="bg-base-100 rounded-b-box border border-t-0 border-base-300 p-3">
      <div class="flex flex-col sm:flex-row items-center justify-between gap-3">
        <div class="flex items-center gap-2">
          <span class="text-sm text-base-content/60">Show</span>
          <select v-model="pageSize" @change="currentPage = 1" class="select select-bordered select-xs w-20">
            <option :value="25">25</option>
            <option :value="50">50</option>
            <option :value="100">100</option>
            <option :value="200">200</option>
          </select>
          <span class="text-sm text-base-content/60">per page</span>
        </div>
        <div class="join">
          <button @click="goToPage(1)" :disabled="currentPage === 1" class="join-item btn btn-xs">«</button>
          <button @click="goToPage(currentPage - 1)" :disabled="currentPage === 1" class="join-item btn btn-xs">‹</button>
          <span class="join-item btn btn-xs btn-active pointer-events-none">{{ currentPage }} / {{ totalPages || 1 }}</span>
          <button @click="goToPage(currentPage + 1)" :disabled="currentPage >= totalPages" class="join-item btn btn-xs">›</button>
          <button @click="goToPage(totalPages)" :disabled="currentPage >= totalPages" class="join-item btn btn-xs">»</button>
        </div>
        <span class="badge badge-ghost badge-sm">{{ filteredStudents.length }} students</span>
      </div>
    </div>
  </div>
</template>

