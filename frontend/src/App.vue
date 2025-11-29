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
const themes = ['light', 'dark']
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
    <!-- Modern Glass Header -->
    <header class="flex-none z-50 bg-base-100/80 backdrop-blur-md border-b border-base-200/50">
      <div class="max-w-screen-2xl w-full mx-auto px-4 h-16 flex items-center justify-between gap-4">
        <!-- Logo Area -->
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-secondary flex items-center justify-center text-primary-content shadow-lg shadow-primary/20">
            <span class="text-xl">📊</span>
          </div>
          <div class="hidden md:flex flex-col leading-tight">
            <span class="font-bold text-lg tracking-tight text-base-content">Canvas Grade Converter</span>
            <span class="text-[10px] font-medium text-base-content/50 uppercase tracking-wider">Local Processing</span>
          </div>
        </div>

        <!-- Central Stepper (Desktop) -->
        <nav class="hidden lg:flex items-center bg-base-200/50 p-1 rounded-full border border-base-200">
          <button
            v-for="(step, index) in steps"
            :key="step.id"
            @click="goToStep(step.id)"
            :disabled="!canGoToStep(step.id)"
            class="relative px-4 py-1.5 rounded-full text-sm font-medium transition-all duration-200"
            :class="[
              currentStep === step.id
                ? 'bg-base-100 text-primary shadow-sm ring-1 ring-black/5 font-bold'
                : index < currentStepIndex
                  ? 'text-base-content hover:text-primary'
                  : 'text-base-content/40 cursor-not-allowed'
            ]"
          >
            <span class="flex items-center gap-2">
              <span v-if="index < currentStepIndex" class="text-xs">✓</span>
              {{ step.label }}
            </span>
          </button>
        </nav>

        <!-- Right Actions -->
        <div class="flex items-center gap-2">
          <div v-if="sessionId" class="badge badge-success badge-sm gap-1 hidden sm:flex">
            <span class="w-1.5 h-1.5 rounded-full bg-success-content animate-pulse"></span>
            Active
          </div>

          <!-- Theme toggle -->
          <div class="dropdown dropdown-end">
            <div tabindex="0" role="button" class="btn btn-ghost btn-sm btn-circle">
              <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01" />
              </svg>
            </div>
            <ul tabindex="0" class="dropdown-content z-50 menu p-2 shadow-lg bg-base-100 rounded-box w-40 border border-base-200">
              <li v-for="theme in themes" :key="theme">
                <a @click="currentTheme = theme" :class="{ 'active': currentTheme === theme }">
                  {{ theme.charAt(0).toUpperCase() + theme.slice(1) }}
                </a>
              </li>
            </ul>
          </div>

          <!-- Reset button -->
          <button v-if="gradeData" @click="resetWorkflow" class="btn btn-ghost btn-sm text-error" title="Reset Workflow">
            <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        </div>
      </div>
      <!-- Mobile Progress Bar -->
      <div class="lg:hidden h-1 bg-base-200 w-full">
        <div class="h-full bg-primary transition-all duration-300" :style="{ width: `${((currentStepIndex + 1) / steps.length) * 100}%` }"></div>
      </div>
    </header>

    <!-- Main Content -->
    <main class="flex-1 overflow-hidden relative flex flex-col">
      <Transition name="fade-slide" mode="out-in">
        <div :key="currentStep" class="flex-1 flex flex-col h-full w-full overflow-hidden">
          
          <!-- Step: Upload -->
          <div v-if="currentStep === 'upload'" class="flex-1 flex flex-col p-6 lg:p-10 overflow-hidden">
            <div class="h-full max-w-6xl mx-auto w-full grid xl:grid-cols-2 gap-8 items-center justify-items-center">
               <!-- Intro -->
               <div class="flex flex-col justify-center gap-6 bg-base-100 rounded-2xl border border-base-200 shadow-sm p-8">
                 <div class="space-y-2">
                   <h2 class="text-4xl font-extrabold tracking-tight text-base-content text-left">Upload Gradebook</h2>
                   <p class="text-lg text-base-content/70 leading-relaxed">
                     Drag in your Canvas CSV and we will keep everything local while you map categories and grading rules.
                   </p>
                 </div>
                 <div class="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm text-base-content/70">
                   <div class="flex items-start gap-2 bg-base-200/60 rounded-lg p-3 border border-base-200">
                     <span class="text-primary font-bold text-lg">1</span>
                     <div class="leading-tight">Use the Canvas export CSV (no Excel edits needed).</div>
                   </div>
                   <div class="flex items-start gap-2 bg-base-200/60 rounded-lg p-3 border border-base-200">
                     <span class="text-primary font-bold text-lg">2</span>
                     <div class="leading-tight">We’ll validate headers and prep assignments for grouping.</div>
                   </div>
                   <div class="flex items-start gap-2 bg-base-200/60 rounded-lg p-3 border border-base-200">
                     <span class="text-primary font-bold text-lg">3</span>
                     <div class="leading-tight">Optional homework rule is supported later in Categories.</div>
                   </div>
                   <div class="flex items-start gap-2 bg-base-200/60 rounded-lg p-3 border border-base-200">
                     <span class="text-primary font-bold text-lg">4</span>
                     <div class="leading-tight">All processing stays on this device; nothing is uploaded elsewhere.</div>
                   </div>
                 </div>
                 <div class="flex items-center gap-3 text-sm text-base-content/60 border-t border-base-200 pt-4">
                   <span class="badge badge-outline">Accepted: CSV</span>
                   <span class="badge badge-outline">Local-only</span>
                   <span class="badge badge-outline">Large screens friendly</span>
                 </div>
               </div>

               <!-- Upload Area -->
               <div class="card bg-base-100 shadow-xl border border-base-200 overflow-hidden h-full w-full max-w-3xl">
                 <div class="card-body p-0 h-full flex flex-col">
                   <FileUpload @upload-success="handleUploadSuccess" @upload-error="handleUploadError" class="h-full" />
                 </div>
               </div>
            </div>
          </div>

          <!-- Step: Review -->
          <div v-else-if="currentStep === 'review'" class="flex-1 flex flex-col min-h-0 bg-base-100/50">
            <div class="sticky top-0 z-20 px-4 py-3 bg-base-100 border-b border-base-200 flex items-center justify-between">
              <div class="flex items-center gap-3">
                <button @click="prevStep" class="btn btn-secondary btn-outline btn-sm">← Back</button>
                <div class="flex flex-col leading-tight">
                  <span class="text-sm font-bold">Review raw Canvas data</span>
                  <span class="text-xs text-base-content/60">Verify student counts and assignment headers</span>
                </div>
              </div>
              <button @click="nextStep" class="btn btn-primary btn-sm px-6 shadow-md">Continue to Configure →</button>
            </div>
            <GradeDisplay :gradeData="gradeData" class="flex-1 min-h-0" />
          </div>

          <!-- Step: Configure -->
          <div v-else-if="currentStep === 'configure'" class="flex-1 flex flex-col min-h-0">
            <div class="flex-1 overflow-hidden relative">
               <div class="absolute inset-0 overflow-y-auto p-4 lg:p-6">
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
            </div>
            <div class="p-4 border-t border-base-200 bg-base-100/80 backdrop-blur-md flex justify-between items-center z-10">
              <button @click="prevStep" class="btn btn-ghost hover:bg-base-200">← Back</button>
              <button
                @click="nextStep"
                :disabled="!isWeightValid || !hasAssignedCategories"
                class="btn btn-primary px-8 shadow-lg shadow-primary/20">
                Continue to Grading Scale →
              </button>
            </div>
          </div>

          <div v-else-if="currentStep === 'scale'" class="flex-1 flex flex-col min-h-0 overflow-y-auto">
             <div class="w-full h-full flex flex-col p-6 space-y-6">
                <div class="text-center space-y-2">
                  <h2 class="text-3xl font-bold tracking-tight">Grading Scale</h2>
                  <p class="text-base-content/60">Define the percentage thresholds for each letter grade.</p>
                </div>
                
                <div class="card bg-base-100 shadow-xl border border-base-200">
                  <div class="card-body p-6 sm:p-8">
                    <GradingScale
                      v-model="gradingScale"
                      :passingThreshold="passingThreshold"
                      :extraCreditEnabled="extraCreditEnabled"
                      :maxExtraCreditPercent="maxExtraCreditPercent"
                      @update:passingThreshold="passingThreshold = $event"
                    />
                  </div>
                </div>

                <!-- Summary -->
                 <div class="stats shadow-lg w-full bg-base-100 border border-base-200">
                    <div class="stat place-items-center">
                      <div class="stat-title">Categories</div>
                      <div class="stat-value text-primary">{{ categories.length }}</div>
                    </div>
                    <div class="stat place-items-center">
                      <div class="stat-title">Assignments</div>
                      <div class="stat-value text-secondary">{{ categories.reduce((sum, c) => sum + c.assignments.length, 0) }}</div>
                      <div class="stat-desc">of {{ assignmentColumns.length }} total</div>
                    </div>
                    <div class="stat place-items-center">
                      <div class="stat-title">Total Weight</div>
                      <div class="stat-value" :class="totalWeight === 100 ? 'text-success' : 'text-warning'">{{ totalWeight }}%</div>
                    </div>
                 </div>
             </div>
             <div class="p-4 border-t border-base-200 bg-base-100/80 backdrop-blur-md flex justify-between items-center mt-auto sticky bottom-0 z-10">
               <button @click="prevStep" class="btn btn-ghost hover:bg-base-200">← Back</button>
               <button
                 @click="calculateGrades"
                 :disabled="!isWeightValid || !hasAssignedCategories || isCalculating"
                 class="btn btn-primary px-8 gap-2 shadow-lg shadow-primary/20">
                 <span v-if="isCalculating" class="loading loading-spinner loading-sm"></span>
                 {{ isCalculating ? 'Calculating...' : 'Calculate Grades' }}
               </button>
             </div>
          </div>

          <!-- Step: Results -->
          <div v-else-if="currentStep === 'results'" class="flex-1 flex flex-col min-h-0">
             <div class="flex-1 overflow-y-auto p-4 lg:p-6">
                <GradeResults
                  :results="calculatedResults"
                  :sessionId="sessionId"
                  :passingThreshold="passingThreshold"
                  :categories="categories"
                  :gradingScale="gradingScale"
                  :originalFilename="originalFilename"
                  :gradeData="gradeData"
                  @export-success="showToast('Export downloaded successfully!', 'success')"
                  @export-error="(msg) => showToast(msg, 'error')"
                />
             </div>
             <div class="p-4 border-t border-base-200 bg-base-100/80 backdrop-blur-md flex justify-between items-center">
               <button @click="prevStep" class="btn btn-ghost hover:bg-base-200">← Back</button>
               <button @click="resetWorkflow" class="btn btn-secondary btn-outline">Start New Conversion</button>
             </div>
          </div>

        </div>
      </Transition>
    </main>

    <!-- Toast Notifications - mobile bottom, desktop top-right -->
    <div class="fixed z-50 flex flex-col gap-2 max-w-sm right-4 md:top-20 bottom-4 md:bottom-auto">
      <TransitionGroup name="toast">
        <div v-for="toast in toasts" :key="toast.id"
             :class="[
               'alert shadow-lg rounded-xl px-4 py-3 flex items-center gap-3 border border-base-200',
               toast.type === 'success' ? 'bg-success/10 text-success-content border-success/20' : '',
               toast.type === 'error' ? 'bg-error/10 text-error-content border-error/20' : '',
               toast.type === 'warning' ? 'bg-warning/10 text-warning-content border-warning/20' : '',
               toast.type === 'info' ? 'bg-info/10 text-info-content border-info/20' : ''
             ]">
          <span v-if="toast.type === 'success'" class="text-success text-lg">✓</span>
          <span v-else-if="toast.type === 'error'" class="text-error text-lg">✕</span>
          <span v-else-if="toast.type === 'warning'" class="text-warning text-lg">⚠</span>
          <span v-else class="text-info text-lg">ℹ</span>
          <span class="flex-1 font-medium text-sm">{{ toast.message }}</span>
          <button @click="toasts = toasts.filter(t => t.id !== toast.id)" class="btn btn-ghost btn-xs btn-circle opacity-50 hover:opacity-100">×</button>
        </div>
      </TransitionGroup>
    </div>
  </div>
</template>

<style>
.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: opacity 0.3s ease, transform 0.3s ease;
}

.fade-slide-enter-from {
  opacity: 0;
  transform: translateY(10px);
}

.fade-slide-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

.toast-enter-active, .toast-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.toast-enter-from {
  opacity: 0;
  transform: translateX(20px);
}
.toast-leave-to {
  opacity: 0;
  transform: translateX(20px);
}
</style>
