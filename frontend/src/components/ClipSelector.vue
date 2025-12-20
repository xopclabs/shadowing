<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, computed } from "vue";

const props = defineProps<{
  videoPath: string;
  initialTime?: number;
}>();

const emit = defineEmits<{
  (e: "clip-selected", start: number, end: number): void;
}>();

// Constants
const SKIP_SECONDS = 5;
const DEFAULT_SELECTION_DURATION = 5;
const DEFAULT_VISIBLE_DURATION = 20; // Default: 20 seconds visible
const MIN_VISIBLE_DURATION = 5; // Most zoomed in: 5 seconds visible
const MAX_VISIBLE_DURATION = 60; // Most zoomed out: 60 seconds visible
const ZOOM_SPEED = 0.003;
const SNAP_THRESHOLD_PX = 15; // Snap to playhead within 15 pixels

// Refs
const videoRef = ref<HTMLVideoElement | null>(null);
const videoContainerRef = ref<HTMLDivElement | null>(null);
const timelineRef = ref<HTMLDivElement | null>(null);
const seekbarRef = ref<HTMLDivElement | null>(null);

// State
const isLoading = ref(true);
const duration = ref(0);
const currentTime = ref(0);
const isPlaying = ref(false);
const isPreviewMode = ref(false);
const selectionStart = ref<number | null>(null);
const selectionEnd = ref<number | null>(null);
const isDragging = ref(false);
const dragType = ref<"start" | "end" | "region" | "seekbar" | null>(null);
const dragStartX = ref(0);
const dragStartTime = ref(0);

// Timeline zoom state - store visible duration directly
const visibleSeconds = ref(DEFAULT_VISIBLE_DURATION);
const timelineOffset = ref(0); // Start time visible in timeline

// Double tap detection
let lastTapTime = 0;

// Computed
const hasSelection = computed(
  () => selectionStart.value !== null && selectionEnd.value !== null,
);

const selectionDuration = computed(() => {
  if (!hasSelection.value) return 0;
  return (selectionEnd.value! - selectionStart.value!).toFixed(1);
});

// Visible time range in timeline
const visibleDuration = computed(() => {
  // Clamp to video duration if video is shorter than visible seconds
  return Math.min(visibleSeconds.value, duration.value);
});

const visibleStart = computed(() => timelineOffset.value);
const visibleEnd = computed(() =>
  Math.min(timelineOffset.value + visibleDuration.value, duration.value),
);

// Format time helper
const formatTime = (seconds: number): string => {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  const ms = Math.floor((seconds % 1) * 10);
  return `${mins}:${secs.toString().padStart(2, "0")}.${ms}`;
};

const formatTimeShort = (seconds: number): string => {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, "0")}`;
};

// Timeline position helpers (relative to visible area)
const timeToPosition = (time: number, containerWidth: number): number => {
  const relativeTime = time - timelineOffset.value;
  return (relativeTime / visibleDuration.value) * containerWidth;
};

const positionToTime = (x: number, containerWidth: number): number => {
  const relativeTime = (x / containerWidth) * visibleDuration.value;
  return Math.max(
    0,
    Math.min(timelineOffset.value + relativeTime, duration.value),
  );
};

// Seekbar helpers (full duration)
const timeToSeekbarPosition = (
  time: number,
  containerWidth: number,
): number => {
  return (time / duration.value) * containerWidth;
};

const seekbarPositionToTime = (x: number, containerWidth: number): number => {
  return Math.max(
    0,
    Math.min((x / containerWidth) * duration.value, duration.value),
  );
};

// Video event handlers
const onLoadedMetadata = () => {
  if (videoRef.value) {
    duration.value = videoRef.value.duration;
    isLoading.value = false;

    // If initial time is provided, seek to it and set selection there
    const startTime = props.initialTime ?? 0;
    const clampedStart = Math.min(
      startTime,
      duration.value - DEFAULT_SELECTION_DURATION,
    );

    selectionStart.value = Math.max(0, clampedStart);
    selectionEnd.value = Math.min(
      selectionStart.value + DEFAULT_SELECTION_DURATION,
      duration.value,
    );

    // Seek video to initial time
    if (props.initialTime && props.initialTime > 0) {
      videoRef.value.currentTime = clampedStart;
      currentTime.value = clampedStart;
      // Center timeline on initial position
      timelineOffset.value = Math.max(
        0,
        clampedStart - visibleDuration.value / 2,
      );
    }
  }
};

const onTimeUpdate = () => {
  if (videoRef.value) {
    currentTime.value = videoRef.value.currentTime;

    // Loop within selection ONLY in preview mode
    if (isPreviewMode.value && hasSelection.value) {
      if (currentTime.value >= selectionEnd.value!) {
        videoRef.value.currentTime = selectionStart.value!;
      }
    }

    // Auto-adjust timeline offset to keep playhead visible
    if (isPlaying.value && !isDragging.value) {
      const margin = visibleDuration.value * 0.1; // 10% margin

      if (currentTime.value > visibleEnd.value - margin) {
        // Playhead is near right edge, shift timeline forward
        timelineOffset.value = Math.min(
          currentTime.value - visibleDuration.value * 0.2,
          duration.value - visibleDuration.value,
        );
      } else if (currentTime.value < visibleStart.value + margin) {
        // Playhead is near left edge, shift timeline backward
        timelineOffset.value = Math.max(0, currentTime.value - margin);
      }
    }
  }
};

// Video controls
const togglePlay = () => {
  if (!videoRef.value) return;

  if (isPlaying.value) {
    videoRef.value.pause();
    isPlaying.value = false;
  } else {
    videoRef.value.play();
    isPlaying.value = true;
  }
};

const exitPreviewMode = () => {
  isPreviewMode.value = false;
};

const seek = (time: number) => {
  if (videoRef.value) {
    const clampedTime = Math.max(0, Math.min(time, duration.value));
    videoRef.value.currentTime = clampedTime;
    currentTime.value = clampedTime;
    exitPreviewMode();

    // Adjust timeline if seeked position is outside visible range
    if (clampedTime < visibleStart.value || clampedTime > visibleEnd.value) {
      // Center timeline on the seeked position
      const halfVisible = visibleDuration.value / 2;
      timelineOffset.value = Math.max(
        0,
        Math.min(
          clampedTime - halfVisible,
          duration.value - visibleDuration.value,
        ),
      );
    }
  }
};

const skipForward = () => seek(currentTime.value + SKIP_SECONDS);
const skipBackward = () => seek(currentTime.value - SKIP_SECONDS);

// Keyboard controls
const onKeydown = (e: KeyboardEvent) => {
  if (e.target instanceof HTMLInputElement) return;

  switch (e.key) {
    case "ArrowLeft":
      e.preventDefault();
      skipBackward();
      break;
    case "ArrowRight":
      e.preventDefault();
      skipForward();
      break;
    case " ":
      e.preventDefault();
      togglePlay();
      break;
  }
};

// Double tap detection for mobile
const onVideoTap = (e: TouchEvent | MouseEvent) => {
  if (!videoContainerRef.value) return;

  const now = Date.now();
  const rect = videoContainerRef.value.getBoundingClientRect();
  const x = "touches" in e ? e.changedTouches[0].clientX : e.clientX;
  const relativeX = x - rect.left;
  const isLeftHalf = relativeX < rect.width / 2;

  if (now - lastTapTime < 300) {
    if (isLeftHalf) {
      skipBackward();
      showSkipIndicator("left");
    } else {
      skipForward();
      showSkipIndicator("right");
    }
    lastTapTime = 0;
  } else {
    lastTapTime = now;
    setTimeout(() => {
      if (lastTapTime === now) {
        togglePlay();
      }
    }, 300);
  }
};

// Skip indicators
const skipIndicatorLeft = ref(false);
const skipIndicatorRight = ref(false);

const showSkipIndicator = (side: "left" | "right") => {
  if (side === "left") {
    skipIndicatorLeft.value = true;
    setTimeout(() => (skipIndicatorLeft.value = false), 500);
  } else {
    skipIndicatorRight.value = true;
    setTimeout(() => (skipIndicatorRight.value = false), 500);
  }
};

// Seekbar interaction
const onSeekbarMouseDown = (e: MouseEvent) => {
  if (!seekbarRef.value) return;

  const rect = seekbarRef.value.getBoundingClientRect();
  const x = e.clientX - rect.left;
  const time = seekbarPositionToTime(x, rect.width);
  seek(time);

  dragType.value = "seekbar";
  isDragging.value = true;

  window.addEventListener("mousemove", onSeekbarMouseMove);
  window.addEventListener("mouseup", onSeekbarMouseUp);
};

const onSeekbarMouseMove = (e: MouseEvent) => {
  if (!isDragging.value || dragType.value !== "seekbar" || !seekbarRef.value)
    return;

  const rect = seekbarRef.value.getBoundingClientRect();
  const x = e.clientX - rect.left;
  const time = seekbarPositionToTime(x, rect.width);
  seek(time);
};

const onSeekbarMouseUp = () => {
  if (dragType.value === "seekbar") {
    isDragging.value = false;
    dragType.value = null;
  }
  window.removeEventListener("mousemove", onSeekbarMouseMove);
  window.removeEventListener("mouseup", onSeekbarMouseUp);
};

// Timeline zoom with scroll wheel
const onTimelineWheel = (e: WheelEvent) => {
  e.preventDefault();

  if (!timelineRef.value) return;

  const rect = timelineRef.value.getBoundingClientRect();
  const mouseX = e.clientX - rect.left;
  const mouseTimeBeforeZoom = positionToTime(mouseX, rect.width);

  // Adjust visible duration (scroll up = zoom in = less seconds visible)
  const delta = e.deltaY * ZOOM_SPEED;
  const currentVisible = visibleSeconds.value;
  const newVisible = Math.max(
    MIN_VISIBLE_DURATION,
    Math.min(MAX_VISIBLE_DURATION, currentVisible * (1 + delta)),
  );

  if (newVisible !== currentVisible) {
    visibleSeconds.value = newVisible;

    // Adjust offset to keep mouse position at same time
    const mouseRatio = mouseX / rect.width;
    const newOffset = mouseTimeBeforeZoom - mouseRatio * newVisible;

    // Clamp offset
    timelineOffset.value = Math.max(
      0,
      Math.min(newOffset, duration.value - newVisible),
    );
  }
};

// Timeline interaction
const onTimelineMouseDown = (e: MouseEvent) => {
  if (!timelineRef.value) return;

  const rect = timelineRef.value.getBoundingClientRect();
  const x = e.clientX - rect.left;
  const time = positionToTime(x, rect.width);

  const startPos =
    selectionStart.value !== null
      ? timeToPosition(selectionStart.value, rect.width)
      : null;
  const endPos =
    selectionEnd.value !== null
      ? timeToPosition(selectionEnd.value, rect.width)
      : null;

  const handleThreshold = 15;

  if (startPos !== null && Math.abs(x - startPos) < handleThreshold) {
    dragType.value = "start";
  } else if (endPos !== null && Math.abs(x - endPos) < handleThreshold) {
    dragType.value = "end";
  } else if (
    hasSelection.value &&
    time >= selectionStart.value! &&
    time <= selectionEnd.value!
  ) {
    dragType.value = "region";
    dragStartX.value = x;
    dragStartTime.value = selectionStart.value!;
  } else {
    // Click outside selection - do nothing (use seekbar to seek)
    return;
  }

  isDragging.value = true;

  window.addEventListener("mousemove", onTimelineMouseMove);
  window.addEventListener("mouseup", onTimelineMouseUp);
};

const onTimelineMouseMove = (e: MouseEvent) => {
  if (!isDragging.value || !timelineRef.value) return;
  if (dragType.value === "seekbar") return;

  const rect = timelineRef.value.getBoundingClientRect();
  const x = e.clientX - rect.left;
  let time = positionToTime(x, rect.width);

  // Check for snap to playhead
  const playheadX = timeToPosition(currentTime.value, rect.width);
  const shouldSnap = Math.abs(x - playheadX) < SNAP_THRESHOLD_PX;

  if (dragType.value === "start") {
    if (shouldSnap) {
      time = currentTime.value;
    }
    selectionStart.value = Math.max(
      0,
      Math.min(time, selectionEnd.value! - 0.5),
    );
  } else if (dragType.value === "end") {
    if (shouldSnap) {
      time = currentTime.value;
    }
    selectionEnd.value = Math.min(
      duration.value,
      Math.max(time, selectionStart.value! + 0.5),
    );
  } else if (dragType.value === "region") {
    const startTime = positionToTime(dragStartX.value, rect.width);
    const delta = time - startTime;
    const selDur = selectionEnd.value! - selectionStart.value!;

    let newStart = dragStartTime.value + delta;
    newStart = Math.max(0, Math.min(newStart, duration.value - selDur));

    selectionStart.value = newStart;
    selectionEnd.value = newStart + selDur;
  }
};

const onTimelineMouseUp = () => {
  if (dragType.value !== "seekbar") {
    isDragging.value = false;
    dragType.value = null;
  }

  window.removeEventListener("mousemove", onTimelineMouseMove);
  window.removeEventListener("mouseup", onTimelineMouseUp);
};

// Touch events for timeline
const onTimelineTouchStart = (e: TouchEvent) => {
  if (e.touches.length === 1) {
    const touch = e.touches[0];
    onTimelineMouseDown({ clientX: touch.clientX } as MouseEvent);
  }
};

const onTimelineTouchMove = (e: TouchEvent) => {
  if (e.touches.length === 1 && isDragging.value) {
    e.preventDefault();
    const touch = e.touches[0];
    onTimelineMouseMove({ clientX: touch.clientX } as MouseEvent);
  }
};

const onTimelineTouchEnd = () => {
  onTimelineMouseUp();
};

// Generate timeline markers based on zoom level
const timelineMarkers = computed(() => {
  const markers = [];
  const visDur = visibleDuration.value;

  // Determine step based on visible duration
  let step: number;
  if (visDur > 600)
    step = 60; // 1 minute
  else if (visDur > 300)
    step = 30; // 30 seconds
  else if (visDur > 120)
    step = 15; // 15 seconds
  else if (visDur > 60)
    step = 10; // 10 seconds
  else if (visDur > 30)
    step = 5; // 5 seconds
  else if (visDur > 10)
    step = 2; // 2 seconds
  else step = 1; // 1 second

  const startTime = Math.floor(visibleStart.value / step) * step;

  for (let t = startTime; t <= visibleEnd.value; t += step) {
    if (t >= visibleStart.value) {
      markers.push({
        time: t,
        label: formatTimeShort(t),
        isMajor: t % (step * 2) === 0,
      });
    }
  }
  return markers;
});

// Confirm selection
const confirmSelection = () => {
  if (hasSelection.value) {
    emit("clip-selected", selectionStart.value!, selectionEnd.value!);
  }
};

// Toggle preview mode
const togglePreview = () => {
  if (!hasSelection.value || !videoRef.value) return;

  if (isPreviewMode.value) {
    isPreviewMode.value = false;
    videoRef.value.pause();
    isPlaying.value = false;
  } else {
    isPreviewMode.value = true;
    videoRef.value.currentTime = selectionStart.value!;
    videoRef.value.play();
    isPlaying.value = true;
  }
};

const onVideoPause = () => {
  isPlaying.value = false;
};

const onVideoPlay = () => {
  isPlaying.value = true;
};

// Set selection starting at current time
const setSelectionAtCurrentTime = () => {
  const start = currentTime.value;
  const end = Math.min(duration.value, start + DEFAULT_SELECTION_DURATION);
  selectionStart.value = start;
  selectionEnd.value = end;
};

// Center timeline on current time
const centerTimelineOnPlayhead = () => {
  const halfVisible = visibleDuration.value / 2;
  timelineOffset.value = Math.max(
    0,
    Math.min(
      currentTime.value - halfVisible,
      duration.value - visibleDuration.value,
    ),
  );
};

onMounted(() => {
  window.addEventListener("keydown", onKeydown);
});

onUnmounted(() => {
  window.removeEventListener("keydown", onKeydown);
  window.removeEventListener("mousemove", onTimelineMouseMove);
  window.removeEventListener("mouseup", onTimelineMouseUp);
  window.removeEventListener("mousemove", onSeekbarMouseMove);
  window.removeEventListener("mouseup", onSeekbarMouseUp);
});
</script>

<template>
  <div class="space-y-2">
    <!-- Video Player -->
    <div
      ref="videoContainerRef"
      class="relative bg-noche-900 rounded-xl overflow-hidden"
      @click="onVideoTap"
      @touchend="onVideoTap"
    >
      <video
        ref="videoRef"
        :src="`/api/files/stream?path=${encodeURIComponent(videoPath)}`"
        class="w-full aspect-video"
        @loadedmetadata="onLoadedMetadata"
        @timeupdate="onTimeUpdate"
        @ended="
          isPlaying = false;
          isPreviewMode = false;
        "
        @pause="onVideoPause"
        @play="onVideoPlay"
        preload="metadata"
        playsinline
      />

      <!-- Loading overlay -->
      <div
        v-if="isLoading"
        class="absolute inset-0 flex items-center justify-center bg-noche-900/80"
      >
        <div
          class="w-8 h-8 border-4 border-sol-500 border-t-transparent rounded-full animate-spin"
        ></div>
      </div>

      <!-- Skip indicators -->
      <div
        v-if="skipIndicatorLeft"
        class="absolute left-4 top-1/2 -translate-y-1/2 flex items-center gap-1 text-white/80 animate-pulse"
      >
        <svg class="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
          <path d="M11 18V6l-8.5 6 8.5 6zm.5-6l8.5 6V6l-8.5 6z" />
        </svg>
        <span class="text-sm font-bold">{{ SKIP_SECONDS }}s</span>
      </div>
      <div
        v-if="skipIndicatorRight"
        class="absolute right-4 top-1/2 -translate-y-1/2 flex items-center gap-1 text-white/80 animate-pulse"
      >
        <span class="text-sm font-bold">{{ SKIP_SECONDS }}s</span>
        <svg class="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
          <path d="M4 18l8.5-6L4 6v12zm9-12v12l8.5-6L13 6z" />
        </svg>
      </div>

      <!-- Center play button (visual only, clicks handled by container) -->
      <div
        v-if="!isLoading && !isPlaying"
        class="absolute inset-0 flex items-center justify-center pointer-events-none"
      >
        <div
          class="w-14 h-14 rounded-full bg-sol-500/90 flex items-center justify-center shadow-lg"
        >
          <svg
            class="w-7 h-7 text-noche-950 ml-0.5"
            fill="currentColor"
            viewBox="0 0 24 24"
          >
            <path d="M8 5v14l11-7z" />
          </svg>
        </div>
      </div>
    </div>

    <!-- Compact Control Bar -->
    <div class="flex items-center gap-2 px-1">
      <!-- Time display -->
      <span class="font-mono text-xs text-noche-400 w-20">
        {{ formatTime(currentTime) }}
      </span>

      <!-- Seekbar -->
      <div
        ref="seekbarRef"
        class="flex-1 relative h-2 bg-noche-800 rounded-full cursor-pointer group"
        @mousedown="onSeekbarMouseDown"
      >
        <div
          class="absolute top-0 left-0 h-full bg-noche-600 rounded-full"
          :style="{ width: `${(currentTime / duration) * 100}%` }"
        />
        <div
          v-if="hasSelection"
          class="absolute top-0 h-full bg-sol-500/40 rounded-full"
          :style="{
            left: `${(selectionStart! / duration) * 100}%`,
            width: `${((selectionEnd! - selectionStart!) / duration) * 100}%`,
          }"
        />
        <div
          class="absolute top-1/2 -translate-y-1/2 w-3 h-3 bg-sol-400 rounded-full opacity-0 group-hover:opacity-100 transition-opacity shadow"
          :style="{ left: `calc(${(currentTime / duration) * 100}% - 6px)` }"
        />
      </div>

      <!-- Duration -->
      <span class="font-mono text-xs text-noche-500 w-20 text-right">
        {{ formatTime(duration) }}
      </span>

      <!-- Play controls -->
      <div class="flex items-center gap-1 ml-2">
        <button
          @click.stop="skipBackward"
          class="p-1.5 rounded-lg hover:bg-noche-800 transition-colors"
        >
          <svg
            class="w-4 h-4 text-noche-400"
            fill="currentColor"
            viewBox="0 0 24 24"
          >
            <path d="M11 18V6l-8.5 6 8.5 6zm.5-6l8.5 6V6l-8.5 6z" />
          </svg>
        </button>
        <button
          @click.stop="togglePlay"
          class="p-2 rounded-lg bg-sol-500 hover:bg-sol-400 transition-colors"
        >
          <svg
            v-if="!isPlaying"
            class="w-4 h-4 text-noche-950"
            fill="currentColor"
            viewBox="0 0 24 24"
          >
            <path d="M8 5v14l11-7z" />
          </svg>
          <svg
            v-else
            class="w-4 h-4 text-noche-950"
            fill="currentColor"
            viewBox="0 0 24 24"
          >
            <rect x="6" y="4" width="4" height="16" rx="1" />
            <rect x="14" y="4" width="4" height="16" rx="1" />
          </svg>
        </button>
        <button
          @click.stop="skipForward"
          class="p-1.5 rounded-lg hover:bg-noche-800 transition-colors"
        >
          <svg
            class="w-4 h-4 text-noche-400"
            fill="currentColor"
            viewBox="0 0 24 24"
          >
            <path d="M4 18l8.5-6L4 6v12zm9-12v12l8.5-6L13 6z" />
          </svg>
        </button>
      </div>
    </div>

    <!-- Timeline controls row -->
    <div class="flex items-center justify-between px-1">
      <div class="flex items-center gap-3">
        <button
          @click="setSelectionAtCurrentTime"
          class="text-xs text-sol-400 hover:text-sol-300 transition-colors"
        >
          Set clip here
        </button>
        <button
          @click="centerTimelineOnPlayhead"
          class="text-xs text-noche-400 hover:text-noche-200 transition-colors"
        >
          Center view
        </button>
      </div>
      <span class="text-xs text-noche-500">
        {{ visibleDuration.toFixed(0) }}s visible
      </span>
    </div>

    <!-- Timeline -->
    <div
      ref="timelineRef"
      class="relative h-16 rounded-lg bg-noche-800 cursor-crosshair select-none overflow-hidden"
      @mousedown="onTimelineMouseDown"
      @touchstart="onTimelineTouchStart"
      @touchmove="onTimelineTouchMove"
      @touchend="onTimelineTouchEnd"
      @wheel="onTimelineWheel"
    >
      <!-- Time markers -->
      <div
        v-for="marker in timelineMarkers"
        :key="marker.time"
        class="absolute top-0 bottom-0 border-l"
        :class="marker.isMajor ? 'border-noche-600' : 'border-noche-700'"
        :style="{
          left: `${timeToPosition(marker.time, timelineRef?.clientWidth || 300)}px`,
        }"
      >
        <span
          v-if="marker.isMajor"
          class="absolute top-1 left-1 text-[10px] text-noche-500 whitespace-nowrap"
        >
          {{ marker.label }}
        </span>
      </div>

      <!-- Selection region -->
      <div
        v-if="hasSelection"
        class="absolute top-0 bottom-0 bg-sol-500/30 border-l-2 border-r-2 border-sol-500"
        :style="{
          left: `${timeToPosition(selectionStart!, timelineRef?.clientWidth || 300)}px`,
          width: `${timeToPosition(selectionEnd!, timelineRef?.clientWidth || 300) - timeToPosition(selectionStart!, timelineRef?.clientWidth || 300)}px`,
        }"
      >
        <!-- Start Handle -->
        <div
          class="absolute left-0 top-0 bottom-0 w-4 -ml-2 bg-sol-500 cursor-ew-resize flex items-center justify-center hover:bg-sol-400 transition-colors"
        >
          <div class="w-0.5 h-5 bg-noche-950/50 rounded-full"></div>
        </div>

        <!-- End Handle -->
        <div
          class="absolute right-0 top-0 bottom-0 w-4 -mr-2 bg-sol-500 cursor-ew-resize flex items-center justify-center hover:bg-sol-400 transition-colors"
        >
          <div class="w-0.5 h-5 bg-noche-950/50 rounded-full"></div>
        </div>

        <!-- Selection duration label -->
        <div
          class="absolute inset-0 flex items-center justify-center pointer-events-none"
        >
          <span
            class="bg-sol-500 text-noche-950 text-xs font-bold px-2 py-0.5 rounded"
          >
            {{ selectionDuration }}s
          </span>
        </div>
      </div>

      <!-- Playhead -->
      <div
        class="absolute top-0 bottom-0 w-0.5 bg-tierra-400 pointer-events-none z-10"
        :style="{
          left: `${timeToPosition(currentTime, timelineRef?.clientWidth || 300)}px`,
        }"
      >
        <div
          class="absolute -top-0.5 left-1/2 -translate-x-1/2 w-2.5 h-2.5 bg-tierra-400 rounded-full"
        ></div>
      </div>
    </div>

    <!-- Spacer for fixed footer -->
    <div class="pb-16"></div>

    <!-- Fixed Footer -->
    <Teleport to="body">
      <div
        class="fixed bottom-0 left-0 right-0 bg-noche-950/95 backdrop-blur-sm border-t border-noche-800 px-4 py-3 z-50"
      >
        <div class="max-w-2xl mx-auto flex items-center gap-3">
          <!-- Loop/Preview button -->
          <button
            @click="togglePreview"
            :disabled="!hasSelection"
            class="flex items-center gap-2 px-4 py-2.5 rounded-xl transition-colors"
            :class="
              isPreviewMode
                ? 'bg-tierra-500 hover:bg-tierra-400 text-white'
                : 'bg-noche-800 hover:bg-noche-700 text-noche-300 disabled:opacity-40 disabled:cursor-not-allowed'
            "
          >
            <svg
              v-if="!isPreviewMode"
              class="w-5 h-5"
              fill="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                d="M12 5V1L7 6l5 5V7c3.31 0 6 2.69 6 6s-2.69 6-6 6-6-2.69-6-6H4c0 4.42 3.58 8 8 8s8-3.58 8-8-3.58-8-8-8z"
              />
            </svg>
            <svg v-else class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
              <rect x="6" y="4" width="4" height="16" rx="1" />
              <rect x="14" y="4" width="4" height="16" rx="1" />
            </svg>
            <span class="text-sm font-medium">{{
              isPreviewMode ? "Stop" : "Loop"
            }}</span>
          </button>

          <!-- Use Clip button -->
          <button
            @click="confirmSelection"
            :disabled="!hasSelection"
            class="flex-1 btn btn-primary py-2.5 text-base font-semibold disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Use This Clip
          </button>
        </div>
      </div>
    </Teleport>
  </div>
</template>
