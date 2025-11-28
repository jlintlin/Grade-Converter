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
  originalFilename: { type: String, default: '' }
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
      // Bar chart dataset
      {
        type: 'bar',
        label: showPercentChart.value ? 'Percent of Students' : 'Number of Students',
        data,
        backgroundColor: colors,
        borderColor: colors.map(c => c),
        borderWidth: 1,
        borderRadius: 4,
        order: 2
      },
      // Line chart overlay (curve)
      {
        type: 'line',
        label: 'Trend',
        data,
        borderColor: '#6366f1',
        backgroundColor: 'rgba(99, 102, 241, 0.1)',
        borderWidth: 3,
        fill: true,
        tension: 0.4,
        pointBackgroundColor: '#6366f1',
        pointBorderColor: '#fff',
        pointBorderWidth: 2,
        pointRadius: 5,
        pointHoverRadius: 7,
        order: 1
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
          if (context.dataset.type === 'line') {
            return showPercentChart.value ? `Trend: ${count}%` : `Trend: ${count} students`
          }
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
  <div class="space-y-6">
    <!-- Header with Export Button -->
    <div class="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
      <div>
        <h2 class="text-2xl font-bold">📊 Grade Results & Export</h2>
        <p class="text-base-content/60 mt-1">
          Review calculated grades and export to CSV
        </p>
      </div>
      <button @click="exportGrades" :disabled="isExporting" class="btn btn-primary btn-lg gap-2">
        <svg v-if="!isExporting" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
        </svg>
        <span v-if="isExporting" class="loading loading-spinner loading-sm"></span>
        {{ isExporting ? 'Exporting...' : 'Export CSV' }}
      </button>
    </div>

    <!-- Summary Cards - 6 columns with statistics -->
    <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
      <div class="card bg-base-100 border border-base-300 shadow-sm">
        <div class="card-body p-4">
          <h3 class="text-xs text-base-content/60">Mean (Average)</h3>
          <p class="text-2xl font-bold">{{ classAverage.toFixed(1) }}%</p>
        </div>
      </div>
      <div class="card bg-base-100 border border-base-300 shadow-sm">
        <div class="card-body p-4">
          <h3 class="text-xs text-base-content/60">Median</h3>
          <p class="text-2xl font-bold">{{ classMedian.toFixed(1) }}%</p>
        </div>
      </div>
      <div class="card bg-base-100 border border-base-300 shadow-sm">
        <div class="card-body p-4">
          <h3 class="text-xs text-base-content/60">Mode</h3>
          <p class="text-2xl font-bold">{{ classMode }}</p>
        </div>
      </div>
      <div class="card bg-base-100 border border-base-300 shadow-sm">
        <div class="card-body p-4">
          <h3 class="text-xs text-base-content/60">Std Dev</h3>
          <p class="text-2xl font-bold">{{ standardDeviation.toFixed(1) }}</p>
        </div>
      </div>
      <div class="card bg-base-100 border border-base-300 shadow-sm">
        <div class="card-body p-4">
          <h3 class="text-xs text-base-content/60">Passing (≥{{ passingThreshold }}%)</h3>
          <p class="text-2xl font-bold text-success">{{ students.filter(s => s.final_percentage >= passingThreshold).length }}</p>
        </div>
      </div>
      <div class="card bg-base-100 border border-base-300 shadow-sm">
        <div class="card-body p-4">
          <h3 class="text-xs text-base-content/60">Failing (&lt;{{ passingThreshold }}%)</h3>
          <p class="text-2xl font-bold text-error">{{ students.filter(s => s.final_percentage < passingThreshold).length }}</p>
        </div>
      </div>
    </div>

    <!-- Grade Distribution Chart - Full Width -->
    <div class="card bg-base-100 shadow-xl">
      <div class="card-body">
        <div class="flex flex-col xl:flex-row gap-6">
          <!-- Bar Chart - Larger -->
          <div class="flex-1 xl:flex-[2]">
            <div class="flex items-center justify-between gap-2 mb-4">
              <h3 class="card-title">📊 Grade Distribution</h3>
              <label class="label cursor-pointer gap-2 text-sm bg-base-200 px-3 py-1 rounded-lg">
                <span class="text-base-content/70">Show %</span>
                <input type="checkbox" v-model="showPercentChart" class="toggle toggle-xs toggle-primary" />
              </label>
            </div>
            <div class="h-80">
              <Bar :data="chartData" :options="chartOptions" />
            </div>
          </div>

          <!-- Grade Breakdown by Letter -->
          <div class="xl:w-80 space-y-3">
            <h4 class="font-semibold text-base-content/70">Grade Breakdown</h4>
            <div class="grid grid-cols-2 xl:grid-cols-1 gap-2">
              <div v-for="grade in gradeOrder.filter(g => gradeDistribution[g])" :key="grade"
                   class="flex items-center justify-between p-2 rounded-lg bg-base-200">
                <span class="font-bold" :style="{ color: gradeColors[grade] }">{{ grade }}</span>
                <div class="flex items-center gap-2">
                  <span class="text-lg font-semibold">{{ gradeDistribution[grade] }}</span>
                  <span class="text-xs opacity-60">({{ ((gradeDistribution[grade] / students.length) * 100).toFixed(0) }}%)</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Student Results Table with Category Breakdown -->
    <div class="bg-base-100 rounded-box border border-base-300 shadow-xl overflow-hidden">
      <!-- Table Header -->
      <div class="bg-base-200/50 px-4 py-3 border-b border-base-300">
        <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div class="flex items-center gap-3">
            <h3 class="font-bold text-lg flex items-center gap-2">
              <svg class="w-5 h-5 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
              Student Grades
            </h3>
            <!-- Toggle for detailed view -->
            <label class="label cursor-pointer gap-2 bg-base-100 px-3 py-1 rounded-lg border border-base-300">
              <span class="text-sm text-base-content/70">Detailed</span>
              <input type="checkbox" v-model="showDetailedView" class="toggle toggle-sm toggle-primary" />
            </label>
            <label class="label cursor-pointer gap-2 bg-base-100 px-3 py-1 rounded-lg border border-base-300">
              <span class="text-sm text-base-content/70">Failing only</span>
              <input type="checkbox" v-model="failOnly" class="toggle toggle-sm toggle-warning" />
            </label>
          </div>
          <input v-model="searchQuery" type="text" placeholder="Search students..."
                 class="input input-bordered input-sm w-full md:w-64" />
        </div>
      </div>

      <!-- Excel-like scrollable table container -->
      <div class="relative overflow-auto bg-base-100 border-x border-base-300 max-h-[500px]">
        <table class="w-full border-collapse">
          <thead class="sticky top-0 z-30">
            <tr class="bg-base-200/95 backdrop-blur-sm">
              <!-- Frozen student name column -->
              <th class="sticky left-0 z-40 bg-base-200/95 backdrop-blur-sm min-w-[200px] px-3 py-2 text-left border-b-2 border-r-2 border-base-300 shadow-[2px_0_4px_rgba(0,0,0,0.1)] cursor-pointer" @click="toggleSort('name')">
                <div class="flex items-center gap-1 font-semibold">
                  <svg class="w-4 h-4 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                  </svg>
                  Student
                  <span class="text-[10px] text-base-content/50">{{ sortKey === 'name' ? (sortDir === 'asc' ? '▲' : '▼') : '' }}</span>
                </div>
              </th>
              <!-- ID column -->
              <th class="bg-base-200/95 backdrop-blur-sm min-w-[80px] px-2 py-2 text-left border-b-2 border-r border-base-300 cursor-pointer" @click="toggleSort('id')">
                <span class="font-semibold text-xs">ID</span>
                <span class="text-[10px] text-base-content/50 ml-1">{{ sortKey === 'id' ? (sortDir === 'asc' ? '▲' : '▼') : '' }}</span>
              </th>
              <!-- Category columns (only in detailed view) -->
              <template v-if="showDetailedView">
                <th v-for="cat in displayCategories" :key="cat.name"
                    class="bg-base-200/95 backdrop-blur-sm min-w-[100px] px-2 py-2 text-center border-b-2 border-r border-base-300">
                  <div class="flex flex-col gap-0.5">
                    <span class="font-semibold text-xs">{{ cat.name }}</span>
                    <span class="text-[10px] font-normal opacity-50">({{ cat.weight }}%)</span>
                  </div>
                </th>
              </template>
              <!-- Replacement column (only in detailed view when replacements exist) -->
              <th v-if="showDetailedView && hasReplacements"
                  class="bg-base-200/95 backdrop-blur-sm min-w-[120px] px-2 py-2 text-center border-b-2 border-r border-base-300">
                <div class="flex flex-col gap-0.5">
                  <span class="font-semibold text-xs">🔄 Replaced</span>
                  <span class="text-[10px] font-normal opacity-50">(impact)</span>
                </div>
              </th>
              <!-- Final % column -->
              <th class="bg-base-200/95 backdrop-blur-sm min-w-[90px] px-2 py-2 text-right border-b-2 border-r border-base-300 cursor-pointer" @click="toggleSort('final_percentage')">
                <span class="font-semibold text-xs">Final %</span>
                <span class="text-[10px] text-base-content/50 ml-1">{{ sortKey === 'final_percentage' ? (sortDir === 'asc' ? '▲' : '▼') : '' }}</span>
              </th>
              <!-- Grade column -->
              <th class="bg-base-200/95 backdrop-blur-sm min-w-[70px] px-2 py-2 text-center border-b-2 border-base-300 cursor-pointer" @click="toggleSort('letter_grade')">
                <span class="font-semibold text-xs">Grade</span>
                <span class="text-[10px] text-base-content/50 ml-1">{{ sortKey === 'letter_grade' ? (sortDir === 'asc' ? '▲' : '▼') : '' }}</span>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(student, idx) in paginatedStudents" :key="student.id"
                :class="[
                  'hover:bg-primary/5 transition-colors',
                  idx % 2 === 0 ? 'bg-base-100' : 'bg-base-50',
                  (student.final_percentage || 0) < passingThreshold ? 'border-l-4 border-error/70' : ''
                ]">
              <!-- Frozen student name -->
              <td class="sticky left-0 z-20 px-3 py-1.5 font-medium border-r-2 border-b border-base-300 shadow-[2px_0_4px_rgba(0,0,0,0.05)]"
                  :class="idx % 2 === 0 ? 'bg-base-100' : 'bg-base-50'">
                <div class="tooltip tooltip-right" :data-tip="getStudentTooltip(student)">
                  {{ student.name }}
                </div>
              </td>
              <!-- ID -->
              <td class="px-2 py-1.5 text-xs text-base-content/60 border-r border-b border-base-200 tabular-nums">
                {{ student.id }}
              </td>
              <!-- Category score columns (only in detailed view) -->
              <template v-if="showDetailedView">
                <td v-for="cat in displayCategories" :key="cat.name"
                    class="px-2 py-1.5 text-center border-r border-b border-base-200">
                  <div class="tooltip tooltip-top"
                       :data-tip="`${cat.name}: ${(student.category_scores?.[cat.name] || 0).toFixed(1)}% × ${cat.weight}% = ${getWeightedContribution(student.category_scores?.[cat.name], cat.weight).toFixed(1)}%`">
                    <div class="flex flex-col items-center">
                      <span class="font-mono text-sm tabular-nums" :class="getPercentageClass(student.category_scores?.[cat.name] || 0)">
                        {{ (student.category_scores?.[cat.name] || 0).toFixed(0) }}%
                      </span>
                      <span class="text-[10px] text-base-content/50 tabular-nums">
                        (+{{ getWeightedContribution(student.category_scores?.[cat.name], cat.weight).toFixed(1) }})
                      </span>
                    </div>
                  </div>
                </td>
              </template>
              <!-- Replacement info column (only in detailed view when replacements exist) -->
              <td v-if="showDetailedView && hasReplacements" class="px-2 py-1.5 text-center border-r border-b border-base-200">
                <template v-if="student.replacement_info && student.replacement_info.length > 0">
                  <div v-for="(rep, idx) in student.replacement_info" :key="idx"
                       class="tooltip tooltip-left"
                       :data-tip="`${cleanAssignmentName(rep.replacer)} replaced ${cleanAssignmentName(rep.replaced)}: ${rep.original_score}% → ${rep.new_score}%`">
                    <div class="flex flex-col items-center gap-0.5">
                      <span class="badge badge-info badge-xs whitespace-nowrap">
                        {{ cleanAssignmentName(rep.replaced).substring(0, 12) }}{{ cleanAssignmentName(rep.replaced).length > 12 ? '...' : '' }}
                      </span>
                      <div class="flex items-center gap-1 text-[10px] tabular-nums">
                        <span class="text-error line-through">{{ rep.original_score }}%</span>
                        <span>→</span>
                        <span class="text-success font-medium">{{ rep.new_score }}%</span>
                      </div>
                      <span class="text-[10px] text-success font-bold tabular-nums">+{{ rep.improvement }}%</span>
                    </div>
                  </div>
                </template>
                <span v-else class="text-base-content/30">—</span>
              </td>
              <!-- Final % -->
              <td class="px-2 py-1.5 text-right border-r border-b border-base-200">
                <div class="tooltip tooltip-left" :data-tip="getStudentTooltip(student)">
                  <span class="font-mono font-bold tabular-nums" :class="getPercentageClass(student.final_percentage)">
                    {{ student.final_percentage?.toFixed(1) }}%
                  </span>
                </div>
              </td>
              <!-- Grade -->
              <td class="px-2 py-1.5 text-center border-b border-base-200">
                <div class="tooltip tooltip-left" :data-tip="getGradeTooltip(student)">
                  <span :class="['badge badge-sm', getGradeColor(student.letter_grade)]">
                    {{ student.letter_grade }}
                  </span>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Pagination footer -->
      <div class="bg-base-100 rounded-b-box border border-t-0 border-base-300 p-3">
        <div class="flex flex-col sm:flex-row items-center justify-between gap-3">
          <div class="text-sm text-base-content/60">
            Showing {{ (currentPage - 1) * pageSize + 1 }}-{{ Math.min(currentPage * pageSize, filteredStudents.length) }} of {{ filteredStudents.length }} students
          </div>
          <div class="join">
            <button class="join-item btn btn-sm" :disabled="currentPage === 1" @click="currentPage = 1">«</button>
            <button class="join-item btn btn-sm" :disabled="currentPage === 1" @click="currentPage--">‹</button>
            <button class="join-item btn btn-sm btn-active">{{ currentPage }} / {{ totalPages }}</button>
            <button class="join-item btn btn-sm" :disabled="currentPage >= totalPages" @click="currentPage++">›</button>
            <button class="join-item btn btn-sm" :disabled="currentPage >= totalPages" @click="currentPage = totalPages">»</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
