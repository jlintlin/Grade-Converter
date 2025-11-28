<script setup>
import { ref, computed, watch } from 'vue'
import axios from 'axios'
import FileUpload from './components/FileUpload.vue'
import GradeDisplay from './components/GradeDisplay.vue'
import CategoryManager from './components/CategoryManager.vue'
import GradingScale from './components/GradingScale.vue'
import GradeResults from './components/GradeResults.vue'

// API base URL
const API_URL = import.meta.env.VITE_API_URL || ''

// Theme management
const themes = ['light', 'dark', 'corporate']
const currentTheme = ref(localStorage.getItem('theme') || 'light')
watch(currentTheme, (theme) => {
  document.documentElement.setAttribute('data-theme', theme)
  localStorage.setItem('theme', theme)
}, { immediate: true })

// Workflow steps - 5 steps with separate grading scale
const steps = [
  { id: 'upload', label: 'Upload', icon: '📤', helper: 'Canvas CSV' },
  { id: 'review', label: 'Review', icon: '👀', helper: 'Check columns' },
  { id: 'configure', label: 'Categories', icon: '⚙️', helper: 'Weights & EC' },
  { id: 'scale', label: 'Grading', icon: '📏', helper: 'Letter thresholds' },
  { id: 'results', label: 'Results', icon: '📊', helper: 'Export CSV' }
]
const currentStep = ref('upload')
const currentStepIndex = computed(() => steps.findIndex(s => s.id === currentStep.value))

// Application state
const gradeData = ref(null)
const sessionId = ref(null)
const originalFilename = ref('')
const categories = ref([])
const gradingScale = ref({})
const calculatedResults = ref(null)
const isCalculating = ref(false)
const passingThreshold = ref(70)
const extraCreditEnabled = ref(false)
const maxExtraCreditPercent = ref(5)
const replacementEnabled = ref(false)
const replacementRules = ref({})
const showUploadHelp = ref(false)

// Toast notifications
const toasts = ref([])
function showToast(message, type = 'info', duration = 4000) {
  const id = Date.now()
  toasts.value.push({ id, message, type })
  setTimeout(() => {
    toasts.value = toasts.value.filter(t => t.id !== id)
  }, duration)
}

// Computed state
const totalWeight = computed(() => categories.value.reduce((sum, c) => sum + (c.weight || 0), 0))
const isWeightValid = computed(() => Math.abs(totalWeight.value - 100) < 0.01)
const assignmentColumns = computed(() => gradeData.value?.assignment_columns || [])
const assignmentInfo = computed(() => gradeData.value?.assignment_info || {})
const hasAssignedCategories = computed(() => categories.value.some(c => c.assignments.length > 0))

// Step navigation
function canGoToStep(stepId) {
  const stepIndex = steps.findIndex(s => s.id === stepId)
  if (stepIndex === 0) return true // upload
  if (stepIndex === 1) return !!gradeData.value // review
  if (stepIndex === 2) return !!gradeData.value // configure
  if (stepIndex === 3) return !!gradeData.value && hasAssignedCategories.value // scale
  if (stepIndex === 4) return !!calculatedResults.value // results
  return false
}

function goToStep(stepId) {
  if (canGoToStep(stepId)) {
    currentStep.value = stepId
  }
}

function nextStep() {
  const nextIndex = currentStepIndex.value + 1
  if (nextIndex < steps.length) {
    goToStep(steps[nextIndex].id)
  }
}

function prevStep() {
  const prevIndex = currentStepIndex.value - 1
  if (prevIndex >= 0) {
    goToStep(steps[prevIndex].id)
  }
}

// Event handlers
function handleUploadSuccess(data) {
  gradeData.value = data
  sessionId.value = data.session_id
  originalFilename.value = data.original_filename || ''
  showToast(`Loaded ${data.row_count} students with ${data.assignment_columns.length} assignments`, 'success')

  // Start with no categories - user will create their own
  categories.value = []
  nextStep()
}

function handleUploadError(message) {
  showToast(message, 'error')
}

async function calculateGrades() {
  if (!isWeightValid.value) {
    showToast('Category weights must sum to 100% (excluding extra credit)', 'error')
    return
  }
  if (!hasAssignedCategories.value) {
    showToast('Please assign at least one assignment to a category', 'error')
    return
  }

  isCalculating.value = true
  try {
    const response = await axios.post(`${API_URL}/api/calculate`, {
      session_id: sessionId.value,
      categories: categories.value,
      grading_scale: gradingScale.value,
      replacement_rules: replacementEnabled.value ? replacementRules.value : {}
    })
    calculatedResults.value = response.data
    showToast('Grades calculated successfully!', 'success')
    goToStep('results')
  } catch (error) {
    showToast(error.response?.data?.detail || 'Failed to calculate grades', 'error')
  } finally {
    isCalculating.value = false
  }
}

function resetWorkflow() {
  gradeData.value = null
  sessionId.value = null
  categories.value = []
  calculatedResults.value = null
  replacementEnabled.value = false
  replacementRules.value = {}
  currentStep.value = 'upload'
  showToast('Workflow reset', 'info')
}
</script>

<template>
  <div class="h-screen flex flex-col bg-base-200 overflow-hidden">
    <!-- Compact Header Bar -->
    <header class="bg-base-100 shadow-sm px-4">
      <div class="max-w-screen-2xl w-full mx-auto flex items-center gap-4 h-14">
        <a class="flex items-center gap-2">
          <span class="text-xl">📊</span>
          <span class="font-bold text-lg bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">
            Canvas Grade Converter
          </span>
        </a>

        <!-- Stepper -->
        <div class="flex-1">
          <nav class="hidden md:flex items-center gap-2 text-sm overflow-x-auto" aria-label="Workflow steps">
            <button
              v-for="(step, index) in steps"
              :key="step.id"
              @click="goToStep(step.id)"
              :disabled="!canGoToStep(step.id)"
              :class="[
                'flex items-center gap-2 px-3 py-2 rounded-lg border transition-colors min-w-[140px]',
                currentStep === step.id
                  ? 'bg-primary text-primary-content border-primary'
                  : index < currentStepIndex
                    ? 'border-primary/40 text-primary hover:bg-primary/10'
                    : 'border-base-300 text-base-content/50 cursor-not-allowed'
              ]">
              <span class="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold"
                    :class="index < currentStepIndex ? 'bg-success text-success-content' : 'bg-base-200'">
                {{ index < currentStepIndex ? '✓' : index + 1 }}
              </span>
              <div class="flex flex-col text-left leading-tight">
                <span class="font-semibold">{{ step.icon }} {{ step.label }}</span>
                <span class="text-[11px] text-base-content/60">{{ step.helper }}</span>
              </div>
            </button>
          </nav>
        </div>

        <div class="flex-none flex items-center gap-2">
          <div v-if="sessionId" class="badge badge-success badge-sm gap-1">
            <span class="w-1.5 h-1.5 rounded-full bg-success-content animate-pulse"></span>
            Active
          </div>

          <!-- Theme toggle -->
          <div class="dropdown dropdown-end">
            <div tabindex="0" role="button" class="btn btn-ghost btn-xs btn-circle">
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01" />
              </svg>
            </div>
            <ul tabindex="0" class="dropdown-content z-50 menu p-2 shadow-lg bg-base-100 rounded-box w-40">
              <li v-for="theme in themes" :key="theme">
                <a @click="currentTheme = theme" :class="{ 'active': currentTheme === theme }">
                  {{ theme.charAt(0).toUpperCase() + theme.slice(1) }}
                </a>
              </li>
            </ul>
          </div>

          <!-- Reset button -->
          <button v-if="gradeData" @click="resetWorkflow" class="btn btn-ghost btn-xs text-error">
            Reset
          </button>
        </div>
      </div>
    </header>

    <!-- Main Content -->
    <main class="flex-1 overflow-hidden flex flex-col">
      <div class="flex-1" :class="currentStep === 'upload' ? '' : 'px-4 lg:px-6 py-4'">
        <div class="max-w-screen-2xl w-full mx-auto h-full flex flex-col">
          <!-- Step: Upload - centered with full height -->
          <div v-if="currentStep === 'upload'" class="flex-1 flex items-start">
            <div class="max-w-5xl mx-auto w-full flex flex-col gap-4">
              <div class="flex items-center justify-center gap-3">
                <span class="badge badge-primary badge-sm">Step 1 of 5</span>
                <span class="text-sm text-base-content/60">Upload Canvas CSV</span>
                <button class="btn btn-ghost btn-xs btn-circle" @click="showUploadHelp = !showUploadHelp" :aria-expanded="showUploadHelp" title="How to use">
                  ❔
                </button>
              </div>

              <div class="rounded-3xl border border-base-300 bg-base-100 shadow-lg p-8 flex flex-col gap-6">
                <div class="text-center space-y-2">
                  <h2 class="text-3xl font-bold">📤 Upload Canvas Grades</h2>
                  <p class="text-base-content/70">
                    Export your gradebook from Canvas as CSV and upload it here. Drag-and-drop or use the primary button below.
                  </p>
                </div>

                <div class="flex flex-col gap-4">
                  <div class="grid grid-cols-2 md:grid-cols-5 gap-2 text-sm text-base-content/80 justify-items-center">
                    <span class="badge badge-ghost gap-1 w-full justify-center">1) Upload CSV</span>
                    <span class="badge badge-ghost gap-1 w-full justify-center">2) Review columns</span>
                    <span class="badge badge-ghost gap-1 w-full justify-center">3) Map & weight</span>
                    <span class="badge badge-ghost gap-1 w-full justify-center">4) Set thresholds</span>
                    <span class="badge badge-ghost gap-1 w-full justify-center">5) Preview/export</span>
                  </div>

                  <div class="flex-1 flex items-center justify-center">
                    <FileUpload @upload-success="handleUploadSuccess" @upload-error="handleUploadError" />
                  </div>

                  <div class="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm text-base-content/80">
                    <div class="rounded-xl border border-base-300 bg-base-50 p-3">
                      <div class="font-semibold flex items-center gap-2"><span>🔒</span> Privacy</div>
                      <div class="text-xs text-base-content/60">In-memory only</div>
                    </div>
                    <div class="rounded-xl border border-base-300 bg-base-50 p-3">
                      <div class="font-semibold flex items-center gap-2"><span>🧮</span> Auto-calc</div>
                      <div class="text-xs text-base-content/60">Weights applied</div>
                    </div>
                    <div class="rounded-xl border border-base-300 bg-base-50 p-3">
                      <div class="font-semibold flex items-center gap-2"><span>⬇</span> Export</div>
                      <div class="text-xs text-base-content/60">Template-ready</div>
                    </div>
                    <div class="rounded-xl border border-base-300 bg-base-50 p-3">
                      <div class="font-semibold flex items-center gap-2"><span>🖥</span> Local</div>
                      <div class="text-xs text-base-content/60">Runs on localhost</div>
                    </div>
                  </div>
                </div>

                <div v-if="showUploadHelp" class="rounded-xl border border-primary/40 bg-primary/5 p-4 text-sm text-base-content/80">
                  <div class="font-semibold mb-1">How uploads work</div>
                  <ul class="list-disc list-inside space-y-1">
                    <li>Use a fresh Canvas gradebook CSV export (all sections included).</li>
                    <li>Data stays local in this session; raw CSVs aren’t persisted.</li>
                    <li>After upload: review columns → map categories/weights → set scale → export CSV.</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>

      <!-- Step: Review Data - full height with scrollable table -->
          <div v-else-if="currentStep === 'review'" class="flex-1 flex flex-col min-h-0">
            <GradeDisplay :gradeData="gradeData" class="flex-1 min-h-0" />
            <div class="flex justify-between py-3 flex-shrink-0 border-t border-base-300 mt-2">
              <button @click="prevStep" class="btn btn-outline btn-sm">← Back</button>
              <button @click="nextStep" class="btn btn-primary btn-sm">Continue to Configure →</button>
            </div>
          </div>

      <!-- Step: Configure Categories - scrollable content area -->
          <div v-else-if="currentStep === 'configure'" class="flex-1 flex flex-col min-h-0">
            <div class="flex-1 overflow-y-auto pr-2">
              <CategoryManager
                :assignments="assignmentColumns"
                :assignmentInfo="assignmentInfo"
                :categories="categories"
                :extraCreditEnabled="extraCreditEnabled"
                :maxExtraCreditPercent="maxExtraCreditPercent"
                :replacementEnabled="replacementEnabled"
                :replacementRules="replacementRules"
                @update:categories="categories = $event"
                @update:extraCreditEnabled="extraCreditEnabled = $event"
                @update:maxExtraCreditPercent="maxExtraCreditPercent = $event"
                @update:replacementEnabled="replacementEnabled = $event"
                @update:replacementRules="replacementRules = $event"
              />
            </div>

            <div class="flex justify-between items-center py-3 flex-shrink-0 border-t border-base-300 mt-2">
              <button @click="prevStep" class="btn btn-outline btn-sm">← Back</button>
              <button
                @click="nextStep"
                :disabled="!isWeightValid || !hasAssignedCategories"
                class="btn btn-primary btn-sm">
                Continue to Grading Scale →
              </button>
            </div>
          </div>

      <!-- Step: Grading Scale - dedicated step for scale configuration -->
          <div v-else-if="currentStep === 'scale'" class="flex-1 flex flex-col min-h-0">
            <div class="flex-1 overflow-y-auto pr-2">
              <div class="max-w-screen-xl mx-auto px-2">
                <div class="text-center mb-6">
                  <h2 class="text-2xl font-bold flex items-center justify-center gap-2">
                    📏 Configure Grading Scale
                  </h2>
                  <p class="text-base-content/70 mt-1">
                    Set the minimum percentage thresholds for each letter grade
                  </p>
                </div>

                <div class="card bg-base-100 shadow-lg border border-base-300">
                  <div class="card-body">
                    <GradingScale
                      v-model="gradingScale"
                      :passingThreshold="passingThreshold"
                      :extraCreditEnabled="extraCreditEnabled"
                      :maxExtraCreditPercent="maxExtraCreditPercent"
                      @update:passingThreshold="passingThreshold = $event"
                    />
                  </div>
                </div>

                <!-- Summary of configuration -->
                <div class="mt-6 p-4 bg-base-200 rounded-box">
                  <h3 class="font-semibold mb-2">📋 Configuration Summary</h3>
                  <div class="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                    <div>
                      <span class="text-base-content/60">Categories:</span>
                      <span class="font-medium ml-1">{{ categories.length }}</span>
                    </div>
                    <div>
                      <span class="text-base-content/60">Assignments:</span>
                      <span class="font-medium ml-1">{{ categories.reduce((sum, c) => sum + c.assignments.length, 0) }}/{{ assignmentColumns.length }}</span>
                    </div>
                    <div>
                      <span class="text-base-content/60">Total Weight:</span>
                      <span class="font-medium ml-1" :class="totalWeight === 100 ? 'text-success' : 'text-warning'">{{ totalWeight }}%</span>
                    </div>
                    <div>
                      <span class="text-base-content/60">Passing:</span>
                      <span class="font-medium ml-1">≥{{ passingThreshold }}%</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div class="flex justify-between items-center py-3 flex-shrink-0 border-t border-base-300 mt-2">
              <button @click="prevStep" class="btn btn-outline btn-sm">← Back to Categories</button>
              <button
                @click="calculateGrades"
                :disabled="!isWeightValid || !hasAssignedCategories || isCalculating"
                class="btn btn-primary gap-2">
                <span v-if="isCalculating" class="loading loading-spinner loading-sm"></span>
                {{ isCalculating ? 'Calculating...' : 'Calculate Grades' }}
              </button>
            </div>
          </div>

      <!-- Step: Results - full height with scrollable content -->
          <div v-else-if="currentStep === 'results'" class="flex-1 flex flex-col min-h-0">
            <div class="flex-1 overflow-y-auto">
              <GradeResults
                :results="calculatedResults"
                :sessionId="sessionId"
                :passingThreshold="passingThreshold"
                :categories="categories"
                :gradingScale="gradingScale"
                :originalFilename="originalFilename"
                @export-success="showToast('Export downloaded successfully!', 'success')"
                @export-error="(msg) => showToast(msg, 'error')"
              />
            </div>
            <div class="flex justify-between py-3 flex-shrink-0 border-t border-base-300 mt-2">
              <button @click="prevStep" class="btn btn-outline btn-sm">← Back to Grading Scale</button>
              <button @click="resetWorkflow" class="btn btn-secondary btn-sm">Start New Conversion</button>
            </div>
          </div>
        </div>
      </div>
    </main>

    <!-- Toast Notifications - mobile bottom, desktop top-right -->
    <div class="fixed z-50 flex flex-col gap-2 max-w-sm right-4 md:top-4 bottom-4 md:bottom-auto">
      <TransitionGroup name="toast">
        <div v-for="toast in toasts" :key="toast.id"
             :class="[
               'alert shadow-lg rounded-lg px-4 py-3 flex items-center gap-2',
               toast.type === 'success' ? 'alert-success' : '',
               toast.type === 'error' ? 'alert-error' : '',
               toast.type === 'warning' ? 'alert-warning' : '',
               toast.type === 'info' ? 'alert-info' : ''
             ]">
          <span v-if="toast.type === 'success'">✓</span>
          <span v-else-if="toast.type === 'error'">✕</span>
          <span v-else-if="toast.type === 'warning'">⚠</span>
          <span v-else>ℹ</span>
          <span class="flex-1">{{ toast.message }}</span>
          <button @click="toasts = toasts.filter(t => t.id !== toast.id)" class="btn btn-ghost btn-xs">×</button>
        </div>
      </TransitionGroup>
    </div>

    <!-- Footer - minimal, only on upload page -->
    <footer v-if="currentStep === 'upload'" class="flex-shrink-0 py-2 px-4 bg-base-100 text-center border-t border-base-300">
      <p class="text-xs text-base-content/50">
        🔒 Privacy First: Data processed in memory only · © 2025 TLin Investments LLC
      </p>
    </footer>
  </div>
</template>

<style>
.toast-enter-active, .toast-leave-active {
  transition: all 0.3s ease;
}
.toast-enter-from {
  opacity: 0;
  transform: translateX(100%);
}
.toast-leave-to {
  opacity: 0;
  transform: translateX(100%);
}
.toast-move {
  transition: transform 0.3s ease;
}
</style>
