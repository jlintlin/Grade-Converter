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
        <div v-if="!selectedFile" class="flex flex-col items-center justify-center">
          <!-- Upload Icon -->
          <div class="w-24 h-24 rounded-full bg-gradient-to-br from-primary/20 to-secondary/20 flex items-center justify-center mb-6">
            <svg class="w-12 h-12 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round"
                d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
            </svg>
          </div>
          <p class="text-xl font-semibold text-base-content mb-1">Drag and drop your Canvas CSV file here</p>
          <p class="text-sm text-base-content/60 mb-4">Supports gradebook exports from Canvas LMS</p>
          <div class="divider my-4 w-48 mx-auto text-base-content/50 font-medium">OR</div>
          <label class="btn btn-primary btn-lg gap-2">
            <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 16.5V9.75m0 0l3 3m-3-3l-3 3M6.75 19.5a4.5 4.5 0 01-1.41-8.775 5.25 5.25 0 0110.233-2.33 3 3 0 013.758 3.848A3.752 3.752 0 0118 19.5H6.75z" />
            </svg>
            Browse Files
            <input type="file" accept=".csv" class="hidden" @change="handleFileSelect" />
          </label>
        </div>

        <!-- Selected File -->
        <div v-else class="flex flex-col items-center justify-center text-center">
          <!-- Success Icon -->
          <div class="w-24 h-24 rounded-full bg-gradient-to-br from-success/20 to-success/10 flex items-center justify-center mb-6">
            <svg class="w-12 h-12 text-success" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
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

