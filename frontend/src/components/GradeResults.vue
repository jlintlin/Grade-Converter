<script setup>
import { ref, computed } from 'vue'
import axios from 'axios'
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, LineElement, PointElement, Title, Tooltip, Legend, Filler } from 'chart.js'
import { Bar } from 'vue-chartjs'

// Register Chart.js components
ChartJS.register(CategoryScale, LinearScale, BarElement, LineElement, PointElement, Title, Tooltip, Legend, Filler)

const props = defineProps({
  results: { type: Object, required: true },
  sessionId: { type: String, required: true },
  passingThreshold: { type: Number, default: 60 },
  categories: { type: Array, required: true },
  gradingScale: { type: Object, required: true },
  originalFilename: { type: String, default: '' },
  gradeData: { type: Object, default: null }
})

const emit = defineEmits(['export-success', 'export-error'])

const API_URL = import.meta.env.VITE_API_URL || ''
const isExporting = ref(false)
const searchQuery = ref('')
const currentPage = ref(1)
const pageSize = ref(25)
const showPercentChart = ref(false)
const failOnly = ref(false)
const sortKey = ref('final_percentage')
const sortDir = ref('desc')

// Toggle for detailed view
const showDetailedView = ref(false)

// Computed data - map API response structure
const students = computed(() => {
  const results = props.results?.results || []
  return results.map(r => ({
    name: r.Student,
    id: r.ID?.toString() || r['SIS User ID'] || '',
    final_percentage: r.final_percentage,
    letter_grade: r.letter_grade,
    category_scores: r.category_scores || {},
    replacement_info: r.replacement_info || null
  }))
})
const gradeDistribution = computed(() => props.results?.summary?.grade_distribution || {})

// Non-extra-credit categories for display
const displayCategories = computed(() =>
  props.categories.filter(c => !c.extra_credit)
)

// Calculate weighted contribution for a category
function getWeightedContribution(categoryScore, categoryWeight) {
  if (!categoryScore || !categoryWeight) return 0
  return (categoryScore * categoryWeight / 100)
}

// Get category weight by name
function getCategoryWeight(categoryName) {
  const cat = props.categories.find(c => c.name === categoryName)
  return cat?.weight || 0
}

// Statistics calculations
const classAverage = computed(() => {
  if (students.value.length === 0) return 0
  const sum = students.value.reduce((acc, s) => acc + (s.final_percentage || 0), 0)
  return sum / students.value.length
})

const classMedian = computed(() => {
  if (students.value.length === 0) return 0
  const sorted = [...students.value].sort((a, b) => (a.final_percentage || 0) - (b.final_percentage || 0))
  const mid = Math.floor(sorted.length / 2)
  if (sorted.length % 2 === 0) {
    return ((sorted[mid - 1]?.final_percentage || 0) + (sorted[mid]?.final_percentage || 0)) / 2
  }
  return sorted[mid]?.final_percentage || 0
})

const classMode = computed(() => {
  if (students.value.length === 0) return 'N/A'
  const gradeCounts = {}
  for (const s of students.value) {
    if (s.letter_grade) {
      gradeCounts[s.letter_grade] = (gradeCounts[s.letter_grade] || 0) + 1
    }
  }
  let maxCount = 0
  let mode = 'N/A'
  for (const [grade, count] of Object.entries(gradeCounts)) {
    if (count > maxCount) {
      maxCount = count
      mode = grade
    }
  }
  return mode
})

const standardDeviation = computed(() => {
  if (students.value.length <= 1) return 0
  const avg = classAverage.value
  const squaredDiffs = students.value.map(s => Math.pow((s.final_percentage || 0) - avg, 2))
  const variance = squaredDiffs.reduce((sum, d) => sum + d, 0) / students.value.length
  return Math.sqrt(variance)
})

// Chart configuration
const gradeOrder = ['A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D+', 'D', 'D-', 'F']
const gradeColors = {
  'A': '#22c55e', 'A-': '#4ade80',
  'B+': '#3b82f6', 'B': '#60a5fa', 'B-': '#93c5fd',
  'C+': '#eab308', 'C': '#facc15', 'C-': '#fde047',
  'D+': '#f97316', 'D': '#fb923c', 'D-': '#fdba74',
  'F': '#ef4444'
}

const chartData = computed(() => {
  const labels = gradeOrder.filter(g => gradeDistribution.value[g] !== undefined)
  const data = labels.map(g => {
    const raw = gradeDistribution.value[g] || 0
    if (showPercentChart.value && students.value.length) {
      return Number(((raw / students.value.length) * 100).toFixed(1))
    }
    return raw
  })
  const colors = labels.map(g => gradeColors[g] || '#888888')

  return {
    labels,
    datasets: [
      {
        type: 'bar',
        label: showPercentChart.value ? 'Percent of Students' : 'Number of Students',
        data,
        backgroundColor: colors,
        borderColor: colors.map(c => c),
        borderWidth: 1,
        borderRadius: 4,
        barPercentage: 0.6,
        categoryPercentage: 0.8
      }
    ]
  }
})

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  interaction: {
    mode: 'index',
    intersect: false
  },
  plugins: {
    legend: {
      display: true,
      position: 'top',
      labels: {
        usePointStyle: true,
        boxWidth: 8
      }
    },
    tooltip: {
      callbacks: {
        label: (context) => {
          const count = context.raw
          if (showPercentChart.value) return `${count}% of class`
          const pct = ((count / students.value.length) * 100).toFixed(1)
          return `${count} students (${pct}%)`
        }
      }
    }
  },
  scales: {
    y: {
      beginAtZero: true,
      ticks: { stepSize: showPercentChart.value ? 5 : 1 },
      title: {
        display: true,
        text: 'Number of Students'
      }
    },
    x: {
      title: {
        display: true,
        text: 'Letter Grade'
      }
    }
  }
}

// Filtered and paginated students
function getSortValue(student, key) {
  if (key === 'name') return student.name?.toLowerCase() || ''
  if (key === 'id') return student.id?.toLowerCase() || ''
  if (key === 'letter_grade') return student.letter_grade || ''
  return student.final_percentage || 0
}

const filteredStudents = computed(() => {
  let list = students.value
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    list = list.filter(s =>
      s.name?.toLowerCase().includes(query) ||
      s.id?.toLowerCase().includes(query)
    )
  }
  if (failOnly.value) {
    list = list.filter(s => (s.final_percentage || 0) < props.passingThreshold)
  }
  const sorted = [...list].sort((a, b) => {
    const aVal = getSortValue(a, sortKey.value)
    const bVal = getSortValue(b, sortKey.value)
    if (aVal === bVal) return 0
    return sortDir.value === 'asc' ? (aVal > bVal ? 1 : -1) : (aVal < bVal ? 1 : -1)
  })
  return sorted
})

const paginatedStudents = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return filteredStudents.value.slice(start, start + pageSize.value)
})

const totalPages = computed(() => Math.ceil(filteredStudents.value.length / pageSize.value))

// Grade color helper
function getGradeColor(grade) {
  if (!grade) return 'badge-ghost'
  if (grade.startsWith('A')) return 'badge-success'
  if (grade.startsWith('B')) return 'badge-info'
  if (grade.startsWith('C')) return 'badge-warning'
  if (grade.startsWith('D')) return 'badge-error'
  return 'badge-error'
}

// Percentage color helper
function getPercentageClass(pct) {
  if (pct >= 90) return 'text-success'
  if (pct >= 80) return 'text-info'
  if (pct >= 70) return 'text-warning'
  if (pct >= 60) return 'text-error'
  return 'text-error'
}

// Check if any student has replacement info
const hasReplacements = computed(() =>
  students.value.some(s => s.replacement_info && s.replacement_info.length > 0)
)

// Clean assignment name for display
function cleanAssignmentName(name) {
  if (!name) return ''
  let cleaned = name
  // Remove Canvas assignment IDs like (12345)
  cleaned = cleaned.replace(/\s*\(\d+\)\s*$/g, '')
  // Remove "- Requires Respondus LockDown Browser" and similar
  cleaned = cleaned.replace(/[-–]\s*Requires\s+Respondus.*$/i, '')
  // Remove "(Required)" suffix
  cleaned = cleaned.replace(/\s*\(Required\)\s*/gi, ' ')
  // Remove extra whitespace
  cleaned = cleaned.replace(/\s+/g, ' ').trim()
  return cleaned
}

// Generate student summary tooltip
function getStudentTooltip(student) {
  const parts = []
  // Add category breakdown
  if (student.category_scores && displayCategories.value.length > 0) {
    displayCategories.value.forEach(cat => {
      const score = student.category_scores?.[cat.name] || 0
      const contrib = getWeightedContribution(score, cat.weight)
      parts.push(`${cat.name}: ${score.toFixed(0)}% × ${cat.weight}% = ${contrib.toFixed(1)}%`)
    })
  }
  // Add replacement info if any
  if (student.replacement_info && student.replacement_info.length > 0) {
    student.replacement_info.forEach(rep => {
      parts.push(`🔄 ${cleanAssignmentName(rep.replaced)}: ${rep.original_score}% → ${rep.new_score}% (+${rep.improvement}%)`)
    })
  }
  // Add final grade
  parts.push(`Final: ${student.final_percentage?.toFixed(1)}% = ${student.letter_grade}`)
  return parts.join(' | ')
}

// Generate grade tooltip
function getGradeTooltip(student) {
  const pct = student.final_percentage?.toFixed(1)
  const grade = student.letter_grade
  const isPassing = student.final_percentage >= props.passingThreshold
  return `${pct}% → ${grade} (${isPassing ? '✓ Passing' : '✗ Failing'})`
}

function toggleSort(key) {
  if (sortKey.value === key) {
    sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortKey.value = key
    sortDir.value = key === 'name' ? 'asc' : 'desc'
  }
}

// Generate smart export filename based on original Canvas filename
function generateExportFilename() {
  const today = new Date().toISOString().slice(0, 10)

  if (!props.originalFilename) {
    return `grades_export_${today}.csv`
  }

  try {
    // Example input: "2025-11-27T1702_Grades-CIS3360-25Fall_0001.csv"
    // Expected output: "Processed_CIS3360-25Fall_0001_2025-11-28.csv"
    const filename = props.originalFilename

    // Remove .csv extension
    const baseName = filename.replace(/\.csv$/i, '')

    // Try to extract course info (pattern: Grades-COURSEID-TERM_SECTION)
    // Match patterns like "Grades-CIS3360-25Fall_0001" or just the course part
    const courseMatch = baseName.match(/Grades[-_](.+)/i)

    if (courseMatch) {
      // Found course info after "Grades-"
      const courseInfo = courseMatch[1]
      return `Processed_${courseInfo}_${today}.csv`
    }

    // Try to extract just the meaningful part (remove timestamp prefix)
    // Pattern: "YYYY-MM-DDTHHMM_" at the start
    const withoutTimestamp = baseName.replace(/^\d{4}-\d{2}-\d{2}T\d{4}_/, '')

    if (withoutTimestamp && withoutTimestamp !== baseName) {
      return `Processed_${withoutTimestamp}_${today}.csv`
    }

    // Fallback: use the original basename
    return `Processed_${baseName}_${today}.csv`
  } catch {
    // If parsing fails, use generic name
    return `grades_export_${today}.csv`
  }
}

// State for UI toggles and modals
const showStats = ref(false)
const selectedCategory = ref(null)
const selectedStudent = ref(null)
const showStudentModal = ref(false)

// Drill-down methods
function openCategoryDetails(student, category) {
  selectedStudent.value = student
  selectedCategory.value = category
}

function openStudentDetails(student) {
  selectedStudent.value = student
  showStudentModal.value = true
}

// Helper to get assignment details for a student in a category
function getCategoryDetails(student, category) {
  if (!props.gradeData || !student || !category) return { assignments: [], totalPoints: 0, totalPossible: 0 }

  // Find the raw student record
  const rawStudent = props.gradeData.students.find(s => s.ID == student.id || s['SIS User ID'] == student.id)
  if (!rawStudent) return { assignments: [], totalPoints: 0, totalPossible: 0 }

  const assignments = []
  let totalPoints = 0
  let totalPossible = 0

  category.assignments.forEach(assignName => {
    const score = rawStudent[assignName]
    const possible = props.gradeData.assignment_info?.[assignName]?.points_possible || 0
    
    // Check if numeric
    const numScore = parseFloat(score)
    const isValid = !isNaN(numScore)

    if (isValid && possible > 0) {
      totalPoints += numScore
      totalPossible += possible
    }

    assignments.push({
      name: assignName,
      score: isValid ? numScore : '-',
      possible: possible,
      percentage: (isValid && possible > 0) ? (numScore / possible * 100) : null
    })
  })

  return { assignments, totalPoints, totalPossible }
}

// Helper to find which category an assignment belongs to
function getAssignmentCategory(assignmentName) {
  for (const cat of props.categories) {
    if (cat.assignments.includes(assignmentName)) {
      return cat.name
    }
  }
  return 'Unknown Category'
}

// Helper to get raw details for an assignment
function getRawAssignmentDetails(student, assignmentName) {
  if (!props.gradeData || !student || !assignmentName) return null
  
  const rawStudent = props.gradeData.students.find(s => s.ID == student.id || s['SIS User ID'] == student.id)
  if (!rawStudent) return null

  const score = rawStudent[assignmentName]
  const possible = props.gradeData.assignment_info?.[assignmentName]?.points_possible || 0
  
  return {
    score: score,
    possible: possible,
    percentage: (parseFloat(score) / possible * 100) || 0
  }
}

// Replacement details helpers
function getReplacementsForCategory(student, categoryName) {
  if (!student.replacement_info || !Array.isArray(student.replacement_info)) return []
  return student.replacement_info.filter(rep =>
    getAssignmentCategory(rep.replaced) === categoryName ||
    getAssignmentCategory(rep.replacer) === categoryName
  )
}

// Computed for the currently selected category modal
const selectedCategoryDetails = computed(() => {
  return getCategoryDetails(selectedStudent.value, selectedCategory.value)
})

function closeModals() {
  selectedCategory.value = null
  showStudentModal.value = false
  // Don't clear selectedStudent immediately to prevent UI flicker during transition
  setTimeout(() => {
    if (!selectedCategory.value && !showStudentModal.value) {
      selectedStudent.value = null
    }
  }, 300)
}

// Export functionality
async function exportGrades() {
  isExporting.value = true
  try {
    const response = await axios.post(`${API_URL}/api/export`, {
      session_id: props.sessionId,
      categories: props.categories,
      grading_scale: props.gradingScale
    }, {
      responseType: 'blob'
    })

    // Create download link with smart filename
    const url = globalThis.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', generateExportFilename())
    document.body.appendChild(link)
    link.click()
    link.remove()
    globalThis.URL.revokeObjectURL(url)

    emit('export-success')
  } catch (error) {
    emit('export-error', error.response?.data?.detail || 'Failed to export grades')
  } finally {
    isExporting.value = false
  }
}
</script>

<template>
  <div class="h-full flex flex-col gap-4 overflow-hidden">
    <!-- Header with Actions -->
    <div class="flex flex-col lg:flex-row lg:items-center justify-between gap-4 shrink-0 bg-base-100 p-4 rounded-xl border border-base-200 shadow-sm">
      <div class="flex items-center gap-4">
        <div>
          <h2 class="text-2xl font-bold flex items-center gap-2">
            📊 Grade Results
          </h2>
          <p class="text-sm text-base-content/60 mt-1">
            {{ students.length }} students • Passing ≥ {{ passingThreshold }}%
          </p>
          <div class="flex flex-wrap items-center gap-2 text-xs text-base-content/60 mt-1">
            <span class="badge badge-ghost">Categories: {{ displayCategories.length }}</span>
            <span class="badge badge-ghost">Template: {{ originalFilename || 'Canvas CSV' }}</span>
          </div>
        </div>
      </div>

      <div class="flex flex-wrap items-center gap-3">
        <label class="flex items-center gap-2 text-xs bg-base-200 px-2 py-1 rounded-lg border border-base-300">
          <span class="font-medium text-base-content/70">Fail only</span>
          <input type="checkbox" v-model="failOnly" class="toggle toggle-error toggle-xs" aria-label="Show failing only" />
        </label>
        <button class="btn btn-secondary btn-outline btn-xs" @click="showStats = !showStats">
          {{ showStats ? 'Hide Statistics' : 'Show Statistics' }}
        </button>
        <div class="join shadow-sm">
           <div class="join-item flex items-center px-3 bg-base-200 border border-base-300 border-r-0">
             <svg class="h-4 w-4 opacity-70" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
           </div>
           <input v-model="searchQuery" type="text" placeholder="Search students..."
                  class="input input-bordered input-sm join-item w-full sm:w-48 focus:outline-none" />
        </div>
        <button @click="exportGrades" :disabled="isExporting" class="btn btn-primary btn-sm shadow-lg hover:shadow-xl transition-all gap-2">
          <svg v-if="!isExporting" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
          <span v-if="isExporting" class="loading loading-spinner loading-xs"></span>
          {{ isExporting ? 'Exporting...' : 'Export CSV' }}
        </button>
      </div>
    </div>

    <!-- Statistics Section (Collapsible) -->
    <div v-if="showStats" class="grid grid-cols-1 lg:grid-cols-3 gap-4 shrink-0 animate-fade-in-down">
       <!-- Key Metrics -->
       <div class="stats shadow-sm border border-base-200 bg-base-100 lg:col-span-3 xl:col-span-1">
          <div class="stat place-items-center py-2">
            <div class="stat-title text-xs uppercase tracking-wider font-bold opacity-60">Average</div>
            <div class="stat-value text-primary text-3xl">{{ classAverage.toFixed(1) }}%</div>
            <div class="stat-desc text-xs font-medium">Median: {{ classMedian.toFixed(1) }}%</div>
          </div>
          <div class="stat place-items-center py-2 border-l border-base-200">
            <div class="stat-title text-xs uppercase tracking-wider font-bold opacity-60">Passing</div>
            <div class="stat-value text-success text-3xl">{{ students.filter(s => s.final_percentage >= passingThreshold).length }}</div>
            <div class="stat-desc text-xs font-medium">{{ ((students.filter(s => s.final_percentage >= passingThreshold).length / students.length) * 100).toFixed(0) }}% of class</div>
          </div>
          <div class="stat place-items-center py-2 border-l border-base-200">
            <div class="stat-title text-xs uppercase tracking-wider font-bold opacity-60">Failing</div>
            <div class="stat-value text-error text-3xl">{{ students.filter(s => s.final_percentage < passingThreshold).length }}</div>
            <div class="stat-desc text-xs font-medium">{{ ((students.filter(s => s.final_percentage < passingThreshold).length / students.length) * 100).toFixed(0) }}% of class</div>
          </div>
       </div>

       <!-- Grade Distribution Chart -->
       <div class="card bg-base-100 border border-base-200 shadow-sm lg:col-span-3 xl:col-span-2">
          <div class="card-body p-4 h-48">
             <div class="flex items-center justify-between mb-2">
                <h3 class="font-bold text-sm uppercase tracking-wider opacity-70">Grade Distribution</h3>
                <label class="label cursor-pointer gap-2 text-xs bg-base-200 px-2 py-1 rounded-lg border border-base-300">
                  <span class="font-medium text-base-content/70">% mode</span>
                  <input type="checkbox" v-model="showPercentChart" class="toggle toggle-primary toggle-xs" aria-label="Toggle percent chart" />
                </label>
             </div>
             <div class="h-full w-full relative">
                <Bar :data="chartData" :options="chartOptions" />
             </div>
          </div>
       </div>
    </div>

    <!-- Main Student Table -->
    <div class="flex-1 min-h-0 relative overflow-hidden bg-base-100 border border-base-200 rounded-xl shadow-sm flex flex-col">
      <div class="flex-1 overflow-auto custom-scrollbar">
        <table class="w-full border-collapse text-sm">
          <thead class="sticky top-0 z-30">
            <tr class="bg-base-100 shadow-sm">
              <!-- Frozen student name column -->
              <th class="sticky left-0 z-40 bg-base-100 min-w-[200px] px-4 py-3 text-left border-b border-r border-base-200 shadow-[4px_0_8px_-2px_rgba(0,0,0,0.05)] cursor-pointer hover:bg-base-50 transition-colors" @click="toggleSort('name')">
                <div class="flex items-center gap-1 font-bold">
                  Student
                  <span class="text-[10px] text-primary ml-1">{{ sortKey === 'name' ? (sortDir === 'asc' ? '▲' : '▼') : '' }}</span>
                </div>
              </th>
              <!-- ID column -->
              <th class="bg-base-100 min-w-[100px] px-3 py-3 text-left border-b border-r border-base-200 cursor-pointer hover:bg-base-50 transition-colors" @click="toggleSort('id')">
                <span class="font-semibold text-xs">ID</span>
                <span class="text-[10px] text-primary ml-1">{{ sortKey === 'id' ? (sortDir === 'asc' ? '▲' : '▼') : '' }}</span>
              </th>
              
              <!-- Category Columns -->
              <th v-for="cat in displayCategories" :key="cat.name"
                  class="bg-base-100 min-w-[100px] px-2 py-2 text-center border-b border-r border-base-200">
                <div class="flex flex-col gap-0.5 items-center">
                  <span class="font-semibold text-xs truncate max-w-[120px]" :title="cat.name">{{ cat.name }}</span>
                  <span class="badge badge-xs badge-ghost font-normal opacity-70">{{ cat.weight }}%</span>
                </div>
              </th>

              <!-- Final % column -->
              <th class="bg-base-100 min-w-[90px] px-3 py-3 text-right border-b border-r border-base-200 cursor-pointer hover:bg-base-50 transition-colors" @click="toggleSort('final_percentage')">
                <span class="font-semibold text-xs">Final %</span>
                <span class="text-[10px] text-primary ml-1">{{ sortKey === 'final_percentage' ? (sortDir === 'asc' ? '▲' : '▼') : '' }}</span>
              </th>
              <!-- Grade column -->
              <th class="bg-base-100 min-w-[80px] px-3 py-3 text-center border-b border-base-200 cursor-pointer hover:bg-base-50 transition-colors" @click="toggleSort('letter_grade')">
                <span class="font-semibold text-xs">Grade</span>
                <span class="text-[10px] text-primary ml-1">{{ sortKey === 'letter_grade' ? (sortDir === 'asc' ? '▲' : '▼') : '' }}</span>
              </th>
            </tr>
          </thead>
          <tbody class="bg-base-100">
            <tr v-for="(student, idx) in paginatedStudents" :key="student.id"
                :class="[
                  'group hover:bg-base-200/50 transition-colors border-b border-base-100 last:border-0',
                  (student.final_percentage || 0) < passingThreshold ? 'bg-error/5 border-l-4 border-error/50' : 'border-l-4 border-transparent'
                ]">
              <!-- Frozen student name -->
              <td class="sticky left-0 z-20 px-4 py-2 font-medium border-r border-base-200 bg-base-100 group-hover:bg-base-200/50 transition-colors shadow-[4px_0_8px_-2px_rgba(0,0,0,0.05)]"
                  :class="(student.final_percentage || 0) < passingThreshold ? 'bg-error/5 group-hover:bg-error/10' : ''">
                <div class="truncate max-w-[200px]" :title="student.name">{{ student.name }}</div>
              </td>
              <!-- ID -->
              <td class="px-3 py-2 text-xs text-base-content/60 border-r border-base-200 tabular-nums font-mono">
                {{ student.id }}
              </td>
              
              <!-- Category Scores (Clickable for Drill-down) -->
              <td v-for="cat in displayCategories" :key="cat.name"
                  class="px-2 py-2 text-center border-r border-base-200 cursor-pointer hover:bg-base-200 transition-colors"
                  @click="openCategoryDetails(student, cat)">
                <div class="flex flex-col items-center gap-0.5">
                  <span class="font-mono text-sm tabular-nums font-medium" :class="getPercentageClass(student.category_scores?.[cat.name] || 0)">
                    {{ (student.category_scores?.[cat.name] || 0).toFixed(0) }}%
                  </span>
                  <span class="text-[10px] text-base-content/40 tabular-nums">
                    {{ getWeightedContribution(student.category_scores?.[cat.name], cat.weight).toFixed(1) }} pts
                  </span>
                  <template v-if="getReplacementsForCategory(student, cat.name).length">
                    <span class="badge badge-info badge-xs mt-1">Replaced</span>
                    <span class="text-[10px] text-base-content/60 truncate max-w-[120px]">
                      Dropped {{ cleanAssignmentName(getReplacementsForCategory(student, cat.name)[0].replaced) }} → {{ cleanAssignmentName(getReplacementsForCategory(student, cat.name)[0].replacer) }}
                    </span>
                  </template>
                </div>
              </td>

              <!-- Final % (Clickable for Full Breakdown) -->
              <td class="px-3 py-2 text-right border-r border-base-200 cursor-pointer hover:bg-base-200 transition-colors"
                  @click="openStudentDetails(student)">
                <span class="font-mono font-bold tabular-nums text-base" :class="getPercentageClass(student.final_percentage)">
                  {{ student.final_percentage?.toFixed(1) }}%
                </span>
              </td>
              <!-- Grade -->
              <td class="px-3 py-2 text-center border-b border-base-200 cursor-pointer hover:bg-base-200 transition-colors"
                  @click="openStudentDetails(student)">
                <span :class="['badge font-bold shadow-sm', getGradeColor(student.letter_grade)]">
                  {{ student.letter_grade }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Pagination footer -->
      <div class="bg-base-100 border-t border-base-200 p-3 shrink-0">
        <div class="flex flex-col sm:flex-row items-center justify-between gap-3">
          <div class="flex items-center gap-2">
            <span class="text-xs text-base-content/60">Rows:</span>
            <select v-model="pageSize" @change="currentPage = 1" class="select select-bordered select-xs w-16 bg-base-100">
              <option :value="25">25</option>
              <option :value="50">50</option>
              <option :value="100">100</option>
              <option :value="200">200</option>
            </select>
            <span class="text-xs text-base-content/60 ml-2">
              Page {{ currentPage }} of {{ totalPages }} ({{ filteredStudents.length }} total)
            </span>
          </div>
          <div class="join shadow-sm">
            <button class="join-item btn btn-xs btn-ghost" :disabled="currentPage === 1" @click="currentPage = 1">«</button>
            <button class="join-item btn btn-xs btn-ghost" :disabled="currentPage === 1" @click="currentPage--">‹</button>
            <button class="join-item btn btn-xs btn-active pointer-events-none font-mono min-w-[3rem]">{{ currentPage }} / {{ totalPages }}</button>
            <button class="join-item btn btn-xs btn-ghost" :disabled="currentPage >= totalPages" @click="currentPage++">›</button>
            <button class="join-item btn btn-xs btn-ghost" :disabled="currentPage >= totalPages" @click="currentPage = totalPages">»</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Modals -->
    <Teleport to="body">
      <!-- Category Details Modal -->
      <div v-if="selectedCategory && selectedStudent" class="fixed inset-0 z-[9999] flex items-center justify-center p-4">
        <div class="fixed inset-0 bg-black/60 backdrop-blur-sm" @click="closeModals"></div>
        <div class="relative z-10 bg-base-100 rounded-2xl shadow-2xl border border-base-200 w-full max-w-lg overflow-hidden flex flex-col max-h-[80vh]">
          <div class="px-6 py-4 border-b border-base-200 bg-base-50/50 flex justify-between items-center shrink-0">
            <div>
              <h3 class="font-bold text-lg">{{ selectedCategory.name }} Details</h3>
              <p class="text-sm text-base-content/60">{{ selectedStudent.name }}</p>
            </div>
            <button @click="closeModals" class="btn btn-ghost btn-sm btn-circle">✕</button>
          </div>
          <div class="p-0 overflow-y-auto">
             <table class="table table-sm w-full">
               <thead class="bg-base-50 sticky top-0 z-10">
                 <tr>
                   <th class="pl-6">Assignment</th>
                   <th class="text-right">Points</th>
                   <th class="text-right pr-6">%</th>
                 </tr>
               </thead>
               <tbody>
                 <tr v-for="assign in selectedCategoryDetails.assignments" :key="assign.name" class="hover:bg-base-50">
                   <td class="pl-6">
                     <div class="font-medium text-xs truncate max-w-[200px]" :title="assign.name">{{ cleanAssignmentName(assign.name) }}</div>
                   </td>
                   <td class="text-right font-mono text-xs">
                     {{ assign.score }} / {{ assign.possible }}
                   </td>
                   <td class="text-right pr-6 font-mono text-xs" :class="getPercentageClass(assign.percentage || 0)">
                     {{ assign.percentage !== null ? assign.percentage.toFixed(1) + '%' : '-' }}
                   </td>
                 </tr>
                 
                 <!-- Calculation Summary Row -->
                 <tr class="bg-base-100 border-t-2 border-base-200 font-bold">
                   <td class="pl-6 text-right text-xs uppercase tracking-wider opacity-70 pt-3">Total</td>
                   <td class="text-right font-mono pt-3">
                     {{ selectedCategoryDetails.totalPoints.toFixed(1) }} / {{ selectedCategoryDetails.totalPossible.toFixed(1) }}
                   </td>
                   <td class="text-right pr-6 font-mono pt-3 text-primary">
                     {{ selectedCategoryDetails.totalPossible > 0 ? ((selectedCategoryDetails.totalPoints / selectedCategoryDetails.totalPossible) * 100).toFixed(1) : '0.0' }}%
                   </td>
                 </tr>
               </tbody>
             </table>
          </div>
          <div class="px-6 py-4 bg-base-50/50 border-t border-base-200 text-right shrink-0">
             <span class="text-sm font-medium mr-2">Weighted Contribution:</span>
             <span class="font-bold text-primary">
               {{ getWeightedContribution(selectedStudent.category_scores?.[selectedCategory.name], selectedCategory.weight).toFixed(2) }} pts
             </span>
             <span class="text-xs text-base-content/50 ml-1">(of {{ selectedCategory.weight }}%)</span>
          </div>
        </div>
      </div>

      <!-- Student Full Breakdown Modal -->
      <div v-if="showStudentModal && selectedStudent" class="fixed inset-0 z-[9999] flex items-center justify-center p-4">
        <div class="fixed inset-0 bg-black/60 backdrop-blur-sm" @click="closeModals"></div>
        <div class="relative z-10 bg-base-100 rounded-2xl shadow-2xl border border-base-200 w-full max-w-2xl overflow-hidden flex flex-col max-h-[85vh]">
          <div class="px-6 py-4 border-b border-base-200 bg-base-50/50 flex justify-between items-center shrink-0">
            <div>
              <h3 class="font-bold text-lg">{{ selectedStudent.name }}</h3>
              <p class="text-sm text-base-content/60">ID: {{ selectedStudent.id }}</p>
            </div>
            <div class="flex items-center gap-3">
               <div class="flex flex-col items-end leading-tight">
                 <span class="text-xs font-bold uppercase tracking-wider opacity-60">Final Grade</span>
                 <span class="text-xl font-bold" :class="getPercentageClass(selectedStudent.final_percentage)">
                   {{ selectedStudent.final_percentage.toFixed(1) }}%
                 </span>
               </div>
               <div class="badge badge-lg font-bold" :class="getGradeColor(selectedStudent.letter_grade)">
                 {{ selectedStudent.letter_grade }}
               </div>
               <button @click="closeModals" class="btn btn-ghost btn-sm btn-circle ml-2">✕</button>
            </div>
          </div>
          
          <div class="p-6 overflow-y-auto space-y-6">
             <!-- Category Breakdown -->
             <div>
               <h4 class="font-bold text-sm uppercase tracking-wider text-base-content/70 mb-3 border-b border-base-200 pb-1">Category Breakdown</h4>
               <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                 <div v-for="cat in displayCategories" :key="cat.name" 
                      class="flex items-center justify-between p-3 rounded-xl bg-base-50 border border-base-200">
                    <div>
                      <div class="font-bold text-sm">{{ cat.name }}</div>
                      <div class="text-xs text-base-content/60">Weight: {{ cat.weight }}%</div>
                    </div>
                    <div class="text-right">
                      <div class="font-bold text-lg" :class="getPercentageClass(selectedStudent.category_scores?.[cat.name] || 0)">
                        {{ (selectedStudent.category_scores?.[cat.name] || 0).toFixed(1) }}%
                      </div>
                      <div class="text-xs font-medium text-primary">
                        +{{ getWeightedContribution(selectedStudent.category_scores?.[cat.name], cat.weight).toFixed(2) }} pts
                      </div>
                    </div>
                 </div>
               </div>
             </div>

             <!-- Replacement Info -->
             <div v-if="selectedStudent.replacement_info && selectedStudent.replacement_info.length > 0">
               <h4 class="font-bold text-sm uppercase tracking-wider text-base-content/70 mb-3 border-b border-base-200 pb-1">Grade Replacements</h4>
               <div class="space-y-3">
                 <div v-for="(rep, idx) in selectedStudent.replacement_info" :key="idx"
                      class="card bg-base-50 border border-base-200 p-3 text-sm">
                    
                    <!-- Header -->
                    <div class="flex items-center gap-2 mb-3">
                      <span class="badge badge-info badge-sm gap-1">
                        <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
                        Replacement Rule Applied
                      </span>
                      <span class="text-xs font-bold opacity-60">
                        Category: {{ getAssignmentCategory(rep.replaced) }}
                      </span>
                    </div>

                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <!-- Dropped Assignment -->
                      <div class="relative p-3 bg-base-100 rounded-lg border border-base-200 overflow-hidden group">
                         <div class="absolute inset-0 bg-base-200/40 z-10 flex items-center justify-center pointer-events-none">
                            <span class="badge badge-error font-bold rotate-12 shadow-sm">DROPPED</span>
                         </div>
                         <div class="opacity-50 blur-[0.5px] group-hover:blur-0 group-hover:opacity-70 transition-all">
                           <div class="font-bold text-xs uppercase tracking-wider mb-1">Original Assignment</div>
                           <div class="font-bold truncate" :title="rep.replaced">{{ cleanAssignmentName(rep.replaced) }}</div>
                           <div class="font-mono text-xs mt-1">
                             <span v-if="getRawAssignmentDetails(selectedStudent, rep.replaced)">
                               {{ getRawAssignmentDetails(selectedStudent, rep.replaced).score }} / {{ getRawAssignmentDetails(selectedStudent, rep.replaced).possible }}
                             </span>
                             <span class="font-bold ml-1">({{ rep.original_score.toFixed(1) }}%)</span>
                           </div>
                         </div>
                      </div>

                      <!-- Replacer Assignment -->
                      <div class="relative p-3 bg-base-100 rounded-lg border border-success/30 shadow-sm">
                         <div class="absolute top-2 right-2 text-success">
                           <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                         </div>
                         <div class="font-bold text-xs uppercase tracking-wider mb-1 text-success">Used Instead</div>
                         <div class="font-bold truncate pr-6" :title="rep.replacer">{{ cleanAssignmentName(rep.replacer) }}</div>
                         <div class="font-mono text-xs mt-1">
                           <span v-if="getRawAssignmentDetails(selectedStudent, rep.replacer)">
                             {{ getRawAssignmentDetails(selectedStudent, rep.replacer).score }} / {{ getRawAssignmentDetails(selectedStudent, rep.replacer).possible }}
                           </span>
                           <span class="font-bold ml-1 text-success">({{ rep.new_score.toFixed(1) }}%)</span>
                         </div>
                         <div class="text-[10px] text-success/80 font-bold mt-2">
                           +{{ rep.improvement.toFixed(1) }}% improvement
                         </div>
                      </div>
                    </div>
                 </div>
               </div>
             </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
