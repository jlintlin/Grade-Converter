<script setup>
import { ref, computed, onBeforeUnmount } from 'vue'
import axios from 'axios'
import FileUpload from './components/FileUpload.vue'
import GradeDisplay from './components/GradeDisplay.vue'
import CategoryConfig from './components/CategoryConfig.vue'
import AssignmentMapper from './components/AssignmentMapper.vue'
import GradingScale from './components/GradingScale.vue'

// Default grading scale (matches backend)
const DEFAULT_GRADING_SCALE = {
  'A': 90.0, 'A-': 87.0, 'B+': 84.0, 'B': 80.0, 'B-': 77.0,
  'C+': 74.0, 'C': 70.0, 'C-': 67.0, 'D+': 64.0, 'D': 61.0,
  'D-': 57.0, 'F': 0.0
}

// Application state
const gradeData = ref(null)
const sessionId = ref(null)
const isLoading = ref(false)
const error = ref(null)
const categories = ref([])
const activeTab = ref('upload')
const calculatedResults = ref(null)
const gradingScale = ref({ ...DEFAULT_GRADING_SCALE })

// Computed properties
const hasData = computed(() => gradeData.value !== null)
const totalWeight = computed(() =>
  categories.value.reduce((sum, cat) => sum + (cat.weight || 0), 0)
)
const isValidConfig = computed(() => Math.abs(totalWeight.value - 100) < 0.01)
const allAssignmentsMapped = computed(() => {
  if (!gradeData.value) return false
  const mappedCount = categories.value.reduce((sum, cat) => sum + cat.assignments.length, 0)
  return mappedCount === gradeData.value.assignment_columns.length
})

// Handle file upload success - no auto-detection, user defines categories
function handleUploadSuccess(data) {
  gradeData.value = data
  sessionId.value = data.session_id
  error.value = null
  calculatedResults.value = null

  // Start with empty categories - user will create their own
  categories.value = []

  activeTab.value = 'mapper'
}

// Handle upload error
function handleUploadError(err) {
  error.value = err
  gradeData.value = null
  sessionId.value = null
}

// Add a new category
function addCategory(name) {
  categories.value.push({
    name,
    weight: 0,
    drop_lowest: 0,
    assignments: []
  })
}

// Delete session data when leaving
async function cleanupSession() {
  if (sessionId.value) {
    try {
      await axios.delete(`/api/session/${sessionId.value}`)
    } catch (e) {
      // Ignore cleanup errors
    }
  }
}

// Reset application and cleanup session
async function resetApp() {
  await cleanupSession()
  gradeData.value = null
  sessionId.value = null
  categories.value = []
  error.value = null
  calculatedResults.value = null
  activeTab.value = 'upload'
}

// Calculate grades
async function calculateGrades() {
  if (!isValidConfig.value || !sessionId.value) return

  isLoading.value = true
  error.value = null

  try {
    const response = await axios.post('/api/calculate', {
      session_id: sessionId.value,
      categories: categories.value,
      grading_scale: gradingScale.value
    })
    calculatedResults.value = response.data
    activeTab.value = 'results'
  } catch (e) {
    error.value = e.response?.data?.detail || 'Failed to calculate grades'
  } finally {
    isLoading.value = false
  }
}

// Export grades to CSV
async function exportGrades() {
  if (!sessionId.value) return

  try {
    const response = await axios.post('/api/export', {
      session_id: sessionId.value,
      categories: categories.value,
      grading_scale: gradingScale.value
    }, { responseType: 'blob' })

    // Create download link
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `grades_export_${Date.now()}.csv`)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  } catch (e) {
    error.value = 'Failed to export grades'
  }
}

// Helper function to get color class based on percentage
function getPercentageColorClass(percentage) {
  if (percentage >= 90) return 'text-success font-medium'
  if (percentage >= 80) return 'text-info'
  if (percentage >= 70) return 'text-warning'
  if (percentage >= 60) return 'text-orange-500'
  return 'text-error'
}

// Helper function to get grade badge class
function getGradeBadgeClass(grade) {
  if (grade.startsWith('A')) return 'badge-success'
  if (grade.startsWith('B')) return 'badge-info'
  if (grade.startsWith('C')) return 'badge-warning'
  if (grade.startsWith('D')) return 'badge-secondary'
  return 'badge-error'
}

// Helper function to get grade color for stats
function getGradeColor(grade) {
  if (grade.startsWith('A')) return 'text-success'
  if (grade.startsWith('B')) return 'text-info'
  if (grade.startsWith('C')) return 'text-warning'
  if (grade.startsWith('D')) return 'text-secondary'
  return 'text-error'
}

// Cleanup on component unmount (page close/refresh)
onBeforeUnmount(() => {
  cleanupSession()
})

// Also cleanup on page unload
if (typeof window !== 'undefined') {
  window.addEventListener('beforeunload', cleanupSession)
}
</script>

<template>
  <div class="min-h-screen bg-base-200" data-theme="corporate">
    <!-- Header -->
    <header class="navbar bg-gradient-to-r from-primary to-primary-focus text-primary-content shadow-xl">
      <div class="max-w-7xl mx-auto w-full px-4">
        <div class="flex-1">
          <div class="flex items-center gap-3">
            <svg class="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <div>
              <h1 class="text-xl font-bold tracking-tight">Canvas Grade Converter</h1>
              <p class="text-xs opacity-80">Transform Canvas exports into graded CSVs</p>
            </div>
          </div>
        </div>
        <div class="flex-none gap-3">
          <div v-if="sessionId" class="badge badge-ghost badge-sm opacity-80">
            <svg class="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
              <circle cx="10" cy="10" r="3"/>
            </svg>
            Session active
          </div>
          <button
            v-if="hasData"
            @click="resetApp"
            class="btn btn-sm btn-ghost hover:bg-primary-focus"
          >
            <svg class="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Start Over
          </button>
        </div>
      </div>
    </header>

    <!-- Main Content -->
    <main class="max-w-7xl mx-auto px-4 py-8">
      <!-- Error Display -->
      <div v-if="error" class="alert alert-error mb-6 shadow-lg">
        <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <div>
          <h3 class="font-bold">Error</h3>
          <div class="text-sm">{{ error }}</div>
        </div>
        <button @click="error = null" class="btn btn-sm btn-ghost">Dismiss</button>
      </div>

      <!-- Tab Navigation (when data is loaded) -->
      <div v-if="hasData" class="mb-8">
        <div role="tablist" class="tabs tabs-boxed bg-base-100 p-1 shadow-md">
          <button
            @click="activeTab = 'grades'"
            role="tab"
            :class="['tab gap-2 transition-all', activeTab === 'grades' ? 'tab-active' : '']"
          >
            <span class="badge badge-primary badge-sm">1</span>
            Grade Overview
          </button>
          <button
            @click="activeTab = 'mapper'"
            role="tab"
            :class="['tab gap-2 transition-all', activeTab === 'mapper' ? 'tab-active' : '']"
          >
            <span class="badge badge-primary badge-sm">2</span>
            Assign Categories
          </button>
          <button
            @click="activeTab = 'config'"
            role="tab"
            :class="['tab gap-2 transition-all', activeTab === 'config' ? 'tab-active' : '']"
          >
            <span class="badge badge-primary badge-sm">3</span>
            Set Weights
          </button>
          <button
            v-if="calculatedResults"
            @click="activeTab = 'results'"
            role="tab"
            :class="['tab gap-2 transition-all', activeTab === 'results' ? 'tab-active' : '']"
          >
            <span class="badge badge-success badge-sm">4</span>
            Results
          </button>
        </div>
      </div>

      <!-- Upload Section (when no data) -->
      <FileUpload
        v-if="!hasData"
        @upload-success="handleUploadSuccess"
        @upload-error="handleUploadError"
        :is-loading="isLoading"
      />

      <!-- Content Sections -->
      <div v-if="hasData">
        <!-- Raw Grade Data -->
        <GradeDisplay
          v-show="activeTab === 'grades'"
          :grade-data="gradeData"
        />

        <!-- Assignment Mapper (user creates and assigns categories) -->
        <AssignmentMapper
          v-show="activeTab === 'mapper'"
          :assignments="gradeData.assignment_columns"
          v-model:categories="categories"
          @add-category="addCategory"
        />

        <!-- Category Weight Configuration -->
        <div v-show="activeTab === 'config'" class="space-y-6">
          <!-- Grading Scale -->
          <GradingScale v-model="gradingScale" />

          <!-- Category Weights -->
          <CategoryConfig
            v-model:categories="categories"
            :total-weight="totalWeight"
            :is-valid="isValidConfig"
            @calculate="calculateGrades"
          />
        </div>

        <!-- Calculated Results -->
        <div v-show="activeTab === 'results'" class="card bg-base-100 shadow-xl">
          <div class="card-body">
            <div class="flex items-center justify-between mb-6">
              <div>
                <h2 class="card-title text-2xl">Calculated Grades</h2>
                <p class="text-sm text-base-content/60" v-if="calculatedResults">
                  {{ calculatedResults.summary.total_students }} students processed
                </p>
              </div>
              <button
                @click="exportGrades"
                class="btn btn-success gap-2"
              >
                <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                Download CSV
              </button>
            </div>

            <div v-if="calculatedResults">
              <!-- Grade Distribution Summary -->
              <div class="mb-6 stats stats-horizontal shadow bg-base-200 w-full">
                <div
                  v-for="(count, grade) in calculatedResults.summary.grade_distribution"
                  :key="grade"
                  class="stat place-items-center"
                >
                  <div class="stat-title">Grade {{ grade }}</div>
                  <div class="stat-value text-2xl" :class="getGradeColor(grade)">{{ count }}</div>
                  <div class="stat-desc">students</div>
                </div>
              </div>

              <!-- Results Table -->
              <div class="overflow-x-auto rounded-lg border border-base-300">
                <table class="table table-zebra">
                  <thead class="bg-base-200">
                    <tr>
                      <th class="font-bold">Student</th>
                      <th class="font-bold">ID</th>
                      <th
                        v-for="cat in categories"
                        :key="cat.name"
                        class="font-bold"
                      >
                        {{ cat.name }}
                      </th>
                      <th class="font-bold">Final %</th>
                      <th class="font-bold">Grade</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(result, idx) in calculatedResults.results" :key="idx" class="hover">
                      <td class="font-medium">{{ result.Student }}</td>
                      <td class="text-base-content/70">{{ result.ID }}</td>
                      <td
                        v-for="cat in categories"
                        :key="cat.name"
                        :class="getPercentageColorClass(result.category_scores[cat.name] || 0)"
                      >
                        {{ result.category_scores[cat.name] || 0 }}%
                      </td>
                      <td class="font-semibold" :class="getPercentageColorClass(result.final_percentage)">
                        {{ result.final_percentage }}%
                      </td>
                      <td>
                        <span class="badge badge-lg" :class="getGradeBadgeClass(result.letter_grade)">
                          {{ result.letter_grade }}
                        </span>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>

    <!-- Footer -->
    <footer class="footer footer-center p-6 bg-base-300 text-base-content mt-8">
      <div class="flex items-center gap-2">
        <svg class="w-5 h-5 text-success" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
        </svg>
        <span>Canvas Grade Converter v1.0 — Privacy focused: all data processed in memory only</span>
      </div>
    </footer>
  </div>
</template>

