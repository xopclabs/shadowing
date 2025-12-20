<script setup lang="ts">
import { RouterView } from "vue-router";
</script>

<template>
  <div class="min-h-screen flex flex-col safe-top safe-bottom">
    <!-- Header -->
    <header
      class="px-4 py-3 border-b border-noche-800 bg-noche-900/80 backdrop-blur-sm sticky top-0 z-50"
    >
      <div class="max-w-2xl mx-auto flex items-center justify-between">
        <router-link to="/" class="flex items-center gap-2">
          <img src="/vite.svg" alt="Logo" class="w-8 h-8" />
          <span class="font-display font-bold text-xl text-sol-400"
            >Shadowing</span
          >
        </router-link>
        <nav class="flex items-center gap-4">
          <router-link
            to="/"
            class="text-noche-400 hover:text-noche-100 transition-colors"
            active-class="text-sol-400"
          >
            Practice
          </router-link>
          <router-link
            to="/history"
            class="text-noche-400 hover:text-noche-100 transition-colors"
            active-class="text-sol-400"
          >
            History
          </router-link>
          <router-link
            to="/settings"
            class="text-noche-400 hover:text-noche-100 transition-colors"
            active-class="text-sol-400"
          >
            <svg
              class="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
              />
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
              />
            </svg>
          </router-link>
        </nav>
      </div>
    </header>

    <!-- Main Content -->
    <main class="flex-1 px-4 py-6">
      <RouterView />
    </main>
  </div>
</template>
