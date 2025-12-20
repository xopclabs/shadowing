<script setup lang="ts">
import { ref, watch, onMounted, nextTick, computed } from "vue";
import { useSettingsStore } from "@/stores/settings";

const props = defineProps<{
  audioUrl: string;
  maxDuration?: number; // If provided, scale visualization to this duration
  // Playback settings for visual representation
  showPlaybackSettings?: boolean;
}>();

const emit = defineEmits<{
  (e: "duration", duration: number): void;
  (e: "effectiveDuration", duration: number): void;
}>();

const settingsStore = useSettingsStore();
const displayMode = computed(() => settingsStore.displayMode);

// Computed effective duration based on playback settings
const effectiveDuration = computed(() => {
  if (!props.showPlaybackSettings) return null;

  const baseDuration = audioDuration.value;
  if (baseDuration <= 0) return null;

  const speed = settingsStore.speedModifier;
  const silenceStart = settingsStore.silenceAtStart / 1000; // ms to s
  const reps = settingsStore.repetitions;
  const gapMs = settingsStore.silenceBetweenReps / 1000; // ms to s

  // Duration of one playback at the given speed
  const onePlayDuration = baseDuration / speed;
  // Total silence between reps (reps - 1 gaps)
  const totalGaps = (reps - 1) * gapMs;

  return silenceStart + onePlayDuration * reps + totalGaps;
});

// Canvas refs
const canvasRef = ref<HTMLCanvasElement | null>(null);

// State
const isAnalyzing = ref(false);
const error = ref<string | null>(null);
const audioDuration = ref(0);

// Configuration
const FFT_SIZE = 1024;
const HOP_SIZE = 256;

// Simple FFT implementation (Cooley-Tukey radix-2)
function fft(real: Float32Array, imag: Float32Array): void {
  const n = real.length;
  if (n <= 1) return;

  for (let i = 0, j = 0; i < n; i++) {
    if (j > i) {
      [real[i], real[j]] = [real[j], real[i]];
      [imag[i], imag[j]] = [imag[j], imag[i]];
    }
    let m = n >> 1;
    while (m >= 1 && j >= m) {
      j -= m;
      m >>= 1;
    }
    j += m;
  }

  for (let len = 2; len <= n; len <<= 1) {
    const halfLen = len >> 1;
    const angleStep = (-2 * Math.PI) / len;
    for (let i = 0; i < n; i += len) {
      for (let j = 0; j < halfLen; j++) {
        const angle = angleStep * j;
        const cos = Math.cos(angle);
        const sin = Math.sin(angle);
        const evenIdx = i + j;
        const oddIdx = i + j + halfLen;
        const tReal = real[oddIdx] * cos - imag[oddIdx] * sin;
        const tImag = real[oddIdx] * sin + imag[oddIdx] * cos;
        real[oddIdx] = real[evenIdx] - tReal;
        imag[oddIdx] = imag[evenIdx] - tImag;
        real[evenIdx] += tReal;
        imag[evenIdx] += tImag;
      }
    }
  }
}

function hannWindow(size: number): Float32Array {
  const win = new Float32Array(size);
  for (let i = 0; i < size; i++) {
    win[i] = 0.5 * (1 - Math.cos((2 * Math.PI * i) / (size - 1)));
  }
  return win;
}

const getColorForValue = (value: number): [number, number, number] => {
  const v = Math.pow(value, 0.7);

  if (v < 0.25) {
    const t = v / 0.25;
    return [
      Math.floor(10 + 50 * t),
      Math.floor(10 * t),
      Math.floor(30 + 70 * t),
    ];
  } else if (v < 0.5) {
    const t = (v - 0.25) / 0.25;
    return [
      Math.floor(60 + 140 * t),
      Math.floor(10 + 30 * t),
      Math.floor(100 + 50 * t),
    ];
  } else if (v < 0.75) {
    const t = (v - 0.5) / 0.25;
    return [
      Math.floor(200 + 55 * t),
      Math.floor(40 + 100 * t),
      Math.floor(150 - 100 * t),
    ];
  } else {
    const t = (v - 0.75) / 0.25;
    return [
      Math.floor(255),
      Math.floor(140 + 115 * t),
      Math.floor(50 + 150 * t),
    ];
  }
};

// Background color for padding (matches spectrogram's darkest color at v=0)
const BG_COLOR: [number, number, number] = [10, 0, 30];

// Waveform colors
const WAVEFORM_BG: [number, number, number] = [10, 0, 30];
const WAVEFORM_COLOR: [number, number, number] = [255, 180, 100]; // sol-400 ish

/**
 * Determine API endpoint for backend spectrogram based on audio URL
 */
const getSpectrogramApiUrl = (
  audioUrl: string,
  maxDuration?: number,
): string => {
  // Parse the audio URL to determine if it's a clip or recording
  // Clip URLs: /api/clips/{id}/audio
  // Recording URLs: /api/recordings/{filename}
  const url = new URL(audioUrl, window.location.origin);
  const pathParts = url.pathname.split("/").filter(Boolean);

  let apiUrl: string;

  if (pathParts.includes("clips") && pathParts.includes("audio")) {
    // Format: /api/clips/{id}/audio - use clip ID endpoint
    const clipIdIdx = pathParts.indexOf("clips") + 1;
    const clipId = pathParts[clipIdIdx];
    apiUrl = `/api/spectrogram/clip/id/${clipId}`;
  } else if (pathParts.includes("recordings")) {
    // Format: /api/recordings/{filename}
    const filename = pathParts[pathParts.length - 1];
    apiUrl = `/api/spectrogram/recording/${filename}`;
  } else {
    // Fallback: try to extract filename from URL
    const filename = pathParts[pathParts.length - 1];
    // Guess based on extension or default to clip
    if (
      filename.includes("_") &&
      (filename.endsWith(".webm") || filename.endsWith(".ogg"))
    ) {
      apiUrl = `/api/spectrogram/recording/${filename}`;
    } else {
      apiUrl = `/api/spectrogram/clip/${filename}`;
    }
  }

  if (maxDuration) {
    apiUrl += `?max_duration=${maxDuration}`;
  }

  return apiUrl;
};

const generateBackendSpectrogram = async () => {
  await nextTick();

  if (!canvasRef.value) {
    console.error("Backend spectrogram: Canvas ref is null");
    return;
  }

  isAnalyzing.value = true;
  error.value = null;

  const canvas = canvasRef.value;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  try {
    const apiUrl = getSpectrogramApiUrl(props.audioUrl, props.maxDuration);
    console.log(
      "[Spectrogram] Backend fetch:",
      apiUrl,
      "| source:",
      props.audioUrl,
    );

    const response = await fetch(apiUrl);
    console.log("[Spectrogram] Response status:", response.status);

    if (!response.ok) {
      const errorText = await response.text();
      console.error(
        "[Spectrogram] Error response:",
        response.status,
        errorText,
      );
      throw new Error(`${response.status}: ${errorText}`);
    }

    // Get duration from response header (may not be accessible due to CORS)
    const durationHeader = response.headers.get("X-Audio-Duration");
    console.log("[Spectrogram] Duration header:", durationHeader);
    if (durationHeader) {
      audioDuration.value = parseFloat(durationHeader);
      emit("duration", audioDuration.value);
    }

    // Load the PNG image
    const blob = await response.blob();
    console.log("[Spectrogram] Received blob:", blob.size, "bytes");

    if (blob.size === 0) {
      throw new Error("Received empty image");
    }

    const imageUrl = URL.createObjectURL(blob);

    const img = new Image();
    await new Promise<void>((resolve, reject) => {
      img.onload = () => {
        console.log("[Spectrogram] Image loaded:", img.width, "x", img.height);
        resolve();
      };
      img.onerror = (e) => {
        console.error("[Spectrogram] Image load error:", e);
        reject(new Error("Failed to load spectrogram image"));
      };
      img.src = imageUrl;
    });

    // Set canvas size to match image
    canvas.width = img.width;
    canvas.height = img.height;

    // Draw the image
    ctx.drawImage(img, 0, 0);

    // Clean up
    URL.revokeObjectURL(imageUrl);
    console.log("[Spectrogram] Successfully rendered");
  } catch (e) {
    console.error("[Spectrogram] Failed:", e);
    error.value = `Failed: ${e instanceof Error ? e.message : String(e)}`;

    canvas.width = 300;
    canvas.height = 100;
    ctx.fillStyle = "#394053";
    ctx.fillRect(0, 0, 300, 100);
  } finally {
    isAnalyzing.value = false;
  }
};

const generateWaveform = async () => {
  await nextTick();

  if (!canvasRef.value) {
    console.error("Waveform: Canvas ref is null");
    return;
  }

  isAnalyzing.value = true;
  error.value = null;

  const canvas = canvasRef.value;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  let audioContext: AudioContext | null = null;

  try {
    const response = await fetch(props.audioUrl);
    if (!response.ok) {
      throw new Error(`Failed to load audio: ${response.status}`);
    }

    const arrayBuffer = await response.arrayBuffer();

    audioContext = new (window.AudioContext ||
      (window as any).webkitAudioContext)();
    const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);

    audioDuration.value = audioBuffer.duration;
    emit("duration", audioBuffer.duration);

    const channelData = audioBuffer.getChannelData(0);

    const maxWidth = 800;
    const maxHeight = 200;
    const displayHeight = maxHeight;

    // Playback settings
    const useSettings = props.showPlaybackSettings;
    const speed = useSettings ? settingsStore.speedModifier : 1;
    const silenceStartSec = useSettings
      ? settingsStore.silenceAtStart / 1000
      : 0;
    const reps = useSettings ? settingsStore.repetitions : 1;
    const gapSec = useSettings ? settingsStore.silenceBetweenReps / 1000 : 0;

    // Calculate durations
    const baseDuration = audioBuffer.duration;
    const scaledDuration = baseDuration / speed;
    const totalEffectiveDuration =
      silenceStartSec + scaledDuration * reps + (reps - 1) * gapSec;

    if (useSettings) {
      emit("effectiveDuration", totalEffectiveDuration);
    }

    // Determine canvas width based on maxDuration or effective duration
    const referenceDuration = props.maxDuration || totalEffectiveDuration;
    const pixelsPerSecond = maxWidth / referenceDuration;
    const displayWidth = maxWidth;

    canvas.width = displayWidth;
    canvas.height = displayHeight;

    // Fill background
    ctx.fillStyle = `rgb(${WAVEFORM_BG[0]}, ${WAVEFORM_BG[1]}, ${WAVEFORM_BG[2]})`;
    ctx.fillRect(0, 0, displayWidth, displayHeight);

    // Pre-calculate waveform peaks for the base audio
    const baseWaveformWidth = Math.floor(
      baseDuration * pixelsPerSecond * (1 / speed) * speed,
    ); // Original width before scaling
    const samplesPerPixel = Math.floor(
      channelData.length / Math.max(1, baseWaveformWidth),
    );
    const peaks: { min: number; max: number }[] = [];

    for (let x = 0; x < baseWaveformWidth; x++) {
      const startSample = x * samplesPerPixel;
      const endSample = Math.min(
        startSample + samplesPerPixel,
        channelData.length,
      );

      let min = 0;
      let max = 0;

      for (let i = startSample; i < endSample; i++) {
        const sample = channelData[i];
        if (sample < min) min = sample;
        if (sample > max) max = sample;
      }

      peaks.push({ min, max });
    }

    // Draw waveform with playback settings
    ctx.fillStyle = `rgb(${WAVEFORM_COLOR[0]}, ${WAVEFORM_COLOR[1]}, ${WAVEFORM_COLOR[2]})`;
    const centerY = displayHeight / 2;

    const scaledWidthPixels = Math.floor(scaledDuration * pixelsPerSecond);
    const silenceStartPixels = Math.floor(silenceStartSec * pixelsPerSecond);
    const gapPixels = Math.floor(gapSec * pixelsPerSecond);

    let currentX = silenceStartPixels;

    for (let rep = 0; rep < reps; rep++) {
      // Draw one repetition of the waveform (scaled by speed)
      for (let x = 0; x < scaledWidthPixels; x++) {
        const canvasX = currentX + x;
        if (canvasX >= displayWidth) break;

        // Map x position to original peaks index
        const progress = x / scaledWidthPixels;
        const peakIndex = Math.min(
          Math.floor(progress * peaks.length),
          peaks.length - 1,
        );
        const peak = peaks[peakIndex];

        if (peak) {
          const amplitude = Math.max(Math.abs(peak.min), Math.abs(peak.max));
          const barHeight = amplitude * (displayHeight * 0.85);
          ctx.fillRect(
            canvasX,
            centerY - barHeight / 2,
            1,
            Math.max(1, barHeight),
          );
        }
      }

      currentX += scaledWidthPixels;

      // Add gap after each rep except the last
      if (rep < reps - 1) {
        currentX += gapPixels;
      }
    }
  } catch (e) {
    console.error("Waveform generation failed:", e);
    error.value = `Failed: ${e instanceof Error ? e.message : String(e)}`;

    canvas.width = 300;
    canvas.height = 100;
    ctx.fillStyle = "#394053";
    ctx.fillRect(0, 0, 300, 100);
  } finally {
    isAnalyzing.value = false;

    if (audioContext && audioContext.state !== "closed") {
      audioContext.close();
    }
  }
};

const generateSpectrogram = async () => {
  await nextTick();

  if (!canvasRef.value) {
    console.error("Spectrogram: Canvas ref is null");
    return;
  }

  isAnalyzing.value = true;
  error.value = null;

  const canvas = canvasRef.value;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  let audioContext: AudioContext | null = null;

  try {
    const response = await fetch(props.audioUrl);
    if (!response.ok) {
      throw new Error(`Failed to load audio: ${response.status}`);
    }

    const arrayBuffer = await response.arrayBuffer();

    audioContext = new (window.AudioContext ||
      (window as any).webkitAudioContext)();
    const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);

    audioDuration.value = audioBuffer.duration;
    emit("duration", audioBuffer.duration);

    const channelData = audioBuffer.getChannelData(0);
    const sampleRate = audioBuffer.sampleRate;

    const numFrames =
      Math.floor((channelData.length - FFT_SIZE) / HOP_SIZE) + 1;
    const numBins = FFT_SIZE / 2;

    const maxWidth = 800;
    const maxHeight = 200;
    const displayHeight = Math.min(numBins, maxHeight);

    // Playback settings
    const useSettings = props.showPlaybackSettings;
    const speed = useSettings ? settingsStore.speedModifier : 1;
    const silenceStartSec = useSettings
      ? settingsStore.silenceAtStart / 1000
      : 0;
    const reps = useSettings ? settingsStore.repetitions : 1;
    const gapSec = useSettings ? settingsStore.silenceBetweenReps / 1000 : 0;

    // Calculate durations
    const baseDuration = audioBuffer.duration;
    const scaledDuration = baseDuration / speed;
    const totalEffectiveDuration =
      silenceStartSec + scaledDuration * reps + (reps - 1) * gapSec;

    if (useSettings) {
      emit("effectiveDuration", totalEffectiveDuration);
    }

    // Determine canvas width based on maxDuration or effective duration
    const referenceDuration = props.maxDuration || totalEffectiveDuration;
    const pixelsPerSecond = maxWidth / referenceDuration;
    const displayWidth = maxWidth;

    canvas.width = displayWidth;
    canvas.height = displayHeight;

    // Generate base spectrogram magnitudes
    const windowFunc = hannWindow(FFT_SIZE);
    const magnitudes: number[][] = [];
    let maxMagnitude = 0;

    // Generate at a fixed resolution, we'll resample when drawing
    const baseSpectrogramCols = Math.min(numFrames, maxWidth);
    const frameStep = Math.max(1, Math.floor(numFrames / baseSpectrogramCols));

    for (let frame = 0; frame < numFrames; frame += frameStep) {
      const startSample = frame * HOP_SIZE;
      const real = new Float32Array(FFT_SIZE);
      const imag = new Float32Array(FFT_SIZE);

      for (let i = 0; i < FFT_SIZE; i++) {
        const sampleIdx = startSample + i;
        if (sampleIdx < channelData.length) {
          real[i] = channelData[sampleIdx] * windowFunc[i];
        } else {
          real[i] = 0;
        }
        imag[i] = 0;
      }

      fft(real, imag);

      const frameMags: number[] = [];
      const useBins = Math.min(numBins, displayHeight * 2);

      for (let bin = 0; bin < useBins; bin++) {
        const magnitude = Math.sqrt(
          real[bin] * real[bin] + imag[bin] * imag[bin],
        );
        const db = 20 * Math.log10(magnitude + 1e-10);
        frameMags.push(db);
        if (db > maxMagnitude) maxMagnitude = db;
      }

      magnitudes.push(frameMags);
    }

    const minDb = maxMagnitude - 80;
    const imageData = ctx.createImageData(displayWidth, displayHeight);

    // Fill entire canvas with background first
    for (let i = 0; i < imageData.data.length; i += 4) {
      imageData.data[i] = BG_COLOR[0];
      imageData.data[i + 1] = BG_COLOR[1];
      imageData.data[i + 2] = BG_COLOR[2];
      imageData.data[i + 3] = 255;
    }

    // Helper to draw a column from magnitude data
    const drawColumn = (col: number, magIndex: number) => {
      if (col < 0 || col >= displayWidth) return;
      const frameMags = magnitudes[Math.min(magIndex, magnitudes.length - 1)];
      if (!frameMags) return;

      for (let row = 0; row < displayHeight; row++) {
        const binIdx = Math.floor(
          (displayHeight - 1 - row) * (frameMags.length / displayHeight),
        );
        const db = frameMags[binIdx] || minDb;
        const normalized = Math.max(
          0,
          Math.min(1, (db - minDb) / (maxMagnitude - minDb)),
        );
        const [r, g, b] = getColorForValue(normalized);
        const pixelIndex = (row * displayWidth + col) * 4;
        imageData.data[pixelIndex] = r;
        imageData.data[pixelIndex + 1] = g;
        imageData.data[pixelIndex + 2] = b;
        imageData.data[pixelIndex + 3] = 255;
      }
    };

    // Draw spectrogram with playback settings
    const scaledWidthPixels = Math.floor(scaledDuration * pixelsPerSecond);
    const silenceStartPixels = Math.floor(silenceStartSec * pixelsPerSecond);
    const gapPixels = Math.floor(gapSec * pixelsPerSecond);

    let currentX = silenceStartPixels;

    for (let rep = 0; rep < reps; rep++) {
      // Draw one repetition of the spectrogram (scaled by speed)
      for (let x = 0; x < scaledWidthPixels; x++) {
        // Map x position to original magnitude index
        const progress = x / scaledWidthPixels;
        const magIndex = Math.floor(progress * magnitudes.length);
        drawColumn(currentX + x, magIndex);
      }

      currentX += scaledWidthPixels;

      // Add gap after each rep except the last
      if (rep < reps - 1) {
        currentX += gapPixels;
      }
    }

    ctx.putImageData(imageData, 0, 0);
  } catch (e) {
    console.error("Spectrogram generation failed:", e);
    error.value = `Failed: ${e instanceof Error ? e.message : String(e)}`;

    canvas.width = 300;
    canvas.height = 100;
    ctx.fillStyle = "#394053";
    ctx.fillRect(0, 0, 300, 100);
  } finally {
    isAnalyzing.value = false;

    if (audioContext && audioContext.state !== "closed") {
      audioContext.close();
    }
  }
};

const generateVisualization = () => {
  if (!props.audioUrl) return;

  if (displayMode.value === "waveform") {
    generateWaveform();
  } else if (displayMode.value === "backend") {
    generateBackendSpectrogram();
  } else {
    generateSpectrogram();
  }
};

onMounted(() => {
  if (props.audioUrl) {
    generateVisualization();
  }
});

watch(
  () => props.audioUrl,
  (newUrl) => {
    if (newUrl) {
      generateVisualization();
    }
  },
);

// Re-render if maxDuration changes
watch(
  () => props.maxDuration,
  () => {
    if (props.audioUrl) {
      generateVisualization();
    }
  },
);

// Re-render if display mode changes
watch(displayMode, () => {
  if (props.audioUrl) {
    generateVisualization();
  }
});

// Re-render when playback settings change (if showing them)
watch(
  [
    () => settingsStore.speedModifier,
    () => settingsStore.silenceAtStart,
    () => settingsStore.repetitions,
    () => settingsStore.silenceBetweenReps,
  ],
  () => {
    if (props.audioUrl && props.showPlaybackSettings) {
      generateVisualization();
    }
  },
);
</script>

<template>
  <div class="relative w-full h-full">
    <div
      v-if="isAnalyzing"
      class="absolute inset-0 flex items-center justify-center bg-noche-800 rounded-lg"
    >
      <div
        class="w-5 h-5 border-2 border-sol-500 border-t-transparent rounded-full animate-spin"
      ></div>
    </div>

    <canvas
      v-show="!isAnalyzing"
      ref="canvasRef"
      class="w-full h-full rounded-lg bg-noche-800"
      style="image-rendering: pixelated"
    />

    <div
      v-if="error && !isAnalyzing"
      class="absolute inset-0 flex items-center justify-center bg-noche-800 rounded-lg"
    >
      <span class="text-xs text-noche-500">Visualization unavailable</span>
    </div>
  </div>
</template>
