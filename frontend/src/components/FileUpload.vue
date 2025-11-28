<script setup>
import { ref } from 'vue'
import axios from 'axios'

const emit = defineEmits(['upload-success', 'upload-error'])
const props = defineProps({
  isLoading: Boolean
})

const isDragging = ref(false)
const isUploading = ref(false)
const selectedFile = ref(null)

// API base URL
const API_URL = import.meta.env.VITE_API_URL || ''

function handleDragOver(e) {
  e.preventDefault()
  isDragging.value = true
}

function handleDragLeave() {
  isDragging.value = false
}

function handleDrop(e) {
  e.preventDefault()
  isDragging.value = false
  
  const files = e.dataTransfer.files
  if (files.length > 0) {
    handleFile(files[0])
  }
}

function handleFileSelect(e) {
  const files = e.target.files
  if (files.length > 0) {
    handleFile(files[0])
  }
}

function handleFile(file) {
  if (!file.name.endsWith('.csv')) {
    emit('upload-error', 'Please select a CSV file')
    return
  }
  selectedFile.value = file
}

async function uploadFile() {
  if (!selectedFile.value) return
  
  isUploading.value = true
  
  try {
    const formData = new FormData()
    formData.append('file', selectedFile.value)
    
    const response = await axios.post(`${API_URL}/api/upload`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
    
    emit('upload-success', response.data)
  } catch (error) {
    const message = error.response?.data?.detail || 'Failed to upload file'
    emit('upload-error', message)
  } finally {
    isUploading.value = false
  }
}

function clearFile() {
  selectedFile.value = null
}
</script>

<template>
  <div class="card bg-base-100 shadow-xl">
    <div class="card-body">
      <h2 class="card-title text-2xl mb-2">
        <svg class="w-7 h-7 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
        </svg>
        Upload Canvas Grades
      </h2>
      <p class="text-base-content/60 mb-6">Export your gradebook from Canvas as CSV and upload it here.</p>

      <!-- Drop Zone -->
      <div
        @dragover="handleDragOver"
        @dragleave="handleDragLeave"
        @drop="handleDrop"
        :class="[
          'border-2 border-dashed rounded-2xl p-12 text-center transition-all cursor-pointer',
          isDragging
            ? 'border-primary bg-primary/5'
            : 'border-base-300 hover:border-primary/50 hover:bg-base-200'
        ]"
      >
        <div v-if="!selectedFile">
          <div class="avatar placeholder mb-4">
            <div class="bg-neutral text-neutral-content rounded-full w-20">
              <svg class="w-10 h-10" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                  d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
          </div>
          <p class="text-lg font-medium text-base-content">Drag and drop your Canvas CSV file here</p>
          <div class="divider my-4">OR</div>
          <label class="btn btn-primary btn-lg gap-2">
            <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
            </svg>
            Browse Files
            <input type="file" accept=".csv" class="hidden" @change="handleFileSelect" />
          </label>
        </div>

        <!-- Selected File -->
        <div v-else class="text-center">
          <div class="avatar placeholder mb-4">
            <div class="bg-success text-success-content rounded-full w-20">
              <svg class="w-10 h-10" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
              </svg>
            </div>
          </div>
          <p class="text-xl font-bold text-base-content">{{ selectedFile.name }}</p>
          <p class="text-base-content/60 mt-1">{{ (selectedFile.size / 1024).toFixed(1) }} KB</p>

          <div class="mt-8 flex justify-center gap-4">
            <button
              @click="clearFile"
              class="btn btn-outline btn-neutral"
            >
              Choose Different File
            </button>
            <button
              @click="uploadFile"
              :disabled="isUploading"
              class="btn btn-primary btn-lg gap-2"
            >
              <span v-if="isUploading" class="loading loading-spinner loading-sm"></span>
              <svg v-else class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
              </svg>
              {{ isUploading ? 'Processing...' : 'Upload & Parse' }}
            </button>
          </div>
        </div>
      </div>

      <!-- Info Cards -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
        <div class="flex items-center gap-3 p-4 bg-base-200 rounded-lg">
          <div class="badge badge-success badge-lg p-3">
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
          </div>
          <div>
            <p class="font-semibold text-sm">Privacy First</p>
            <p class="text-xs text-base-content/60">Data stays in memory only</p>
          </div>
        </div>
        <div class="flex items-center gap-3 p-4 bg-base-200 rounded-lg">
          <div class="badge badge-info badge-lg p-3">
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
            </svg>
          </div>
          <div>
            <p class="font-semibold text-sm">Auto-Calculate</p>
            <p class="text-xs text-base-content/60">Weighted grades computed</p>
          </div>
        </div>
        <div class="flex items-center gap-3 p-4 bg-base-200 rounded-lg">
          <div class="badge badge-warning badge-lg p-3">
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
          </div>
          <div>
            <p class="font-semibold text-sm">Easy Export</p>
            <p class="text-xs text-base-content/60">Download grades as CSV</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

