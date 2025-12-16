<script setup lang="ts">
import { ref, watch, onMounted, nextTick } from "vue";

const props = defineProps<{
  audioUrl: string;
  label?: string;
}>();

// Canvas refs
const canvasRef = ref<HTMLCanvasElement | null>(null);

// State
const isAnalyzing = ref(false);
const error = ref<string | null>(null);

// Configuration
const FFT_SIZE = 1024;
const HOP_SIZE = 256; // Overlap for smoother spectrogram

// Simple FFT implementation (Cooley-Tukey radix-2)
function fft(real: Float32Array, imag: Float32Array): void {
  const n = real.length;
  if (n <= 1) return;

  // Bit-reverse permutation
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

  // Cooley-Tukey FFT
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

// Hann window function for smoother FFT
function hannWindow(size: number): Float32Array {
  const window = new Float32Array(size);
  for (let i = 0; i < size; i++) {
    window[i] = 0.5 * (1 - Math.cos((2 * Math.PI * i) / (size - 1)));
  }
  return window;
}

// Color map for spectrogram (magma-like colormap)
const getColorForValue = (value: number): [number, number, number] => {
  // value is 0-1, apply gamma for better visualization
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

// Generate spectrogram from audio URL
const generateSpectrogram = async () => {
  // Wait for next tick to ensure canvas is rendered
  await nextTick();

  if (!canvasRef.value) {
    console.error("Spectrogram: Canvas ref is null after nextTick");
    return;
  }

  isAnalyzing.value = true;
  error.value = null;

  const canvas = canvasRef.value;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  let audioContext: AudioContext | null = null;

  try {
    console.log("Spectrogram: Fetching audio from:", props.audioUrl);
    // Fetch audio file
    const response = await fetch(props.audioUrl);
    if (!response.ok) {
      console.error(
        "Spectrogram: Failed to fetch audio, status:",
        response.status,
      );
      throw new Error(`Failed to load audio: ${response.status}`);
    }

    console.log(
      "Spectrogram: Got response, content-type:",
      response.headers.get("content-type"),
    );
    const arrayBuffer = await response.arrayBuffer();
    console.log("Spectrogram: ArrayBuffer size:", arrayBuffer.byteLength);

    // Create audio context and decode
    audioContext = new (window.AudioContext ||
      (window as any).webkitAudioContext)();
    console.log("Spectrogram: Created AudioContext, decoding...");
    const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
    console.log("Spectrogram: Decoded audio buffer:", {
      duration: audioBuffer.duration,
      sampleRate: audioBuffer.sampleRate,
      numberOfChannels: audioBuffer.numberOfChannels,
      length: audioBuffer.length,
    });

    // Get mono audio data
    const channelData = audioBuffer.getChannelData(0);
    const sampleRate = audioBuffer.sampleRate;

    // Calculate spectrogram dimensions
    const numFrames =
      Math.floor((channelData.length - FFT_SIZE) / HOP_SIZE) + 1;
    const numBins = FFT_SIZE / 2; // Only positive frequencies

    // Limit canvas size for performance
    const maxWidth = 800;
    const maxHeight = 200;
    const displayWidth = Math.min(numFrames, maxWidth);
    const displayHeight = Math.min(numBins, maxHeight);

    canvas.width = displayWidth;
    canvas.height = displayHeight;

    // Precompute window function
    const windowFunc = hannWindow(FFT_SIZE);

    // Store all magnitude data
    const magnitudes: number[][] = [];
    let maxMagnitude = 0;

    // Process each frame
    const frameStep = Math.max(1, Math.floor(numFrames / displayWidth));

    for (let frame = 0; frame < numFrames; frame += frameStep) {
      const startSample = frame * HOP_SIZE;

      // Prepare FFT input (apply window)
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

      // Compute FFT
      fft(real, imag);

      // Compute magnitude spectrum (only lower half for display - speech frequencies)
      const frameMags: number[] = [];
      const useBins = Math.min(numBins, displayHeight * 2); // Focus on lower frequencies

      for (let bin = 0; bin < useBins; bin++) {
        const magnitude = Math.sqrt(
          real[bin] * real[bin] + imag[bin] * imag[bin],
        );
        // Convert to dB scale
        const db = 20 * Math.log10(magnitude + 1e-10);
        frameMags.push(db);
        if (db > maxMagnitude) maxMagnitude = db;
      }

      magnitudes.push(frameMags);
    }

    // Normalize and draw
    const minDb = maxMagnitude - 80; // 80 dB dynamic range
    const imageData = ctx.createImageData(displayWidth, displayHeight);

    for (let col = 0; col < magnitudes.length && col < displayWidth; col++) {
      const frameMags = magnitudes[col];

      for (let row = 0; row < displayHeight; row++) {
        // Map row to frequency bin (invert so low freq at bottom)
        const binIdx = Math.floor(
          (displayHeight - 1 - row) * (frameMags.length / displayHeight),
        );
        const db = frameMags[binIdx] || minDb;

        // Normalize to 0-1
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
    }

    ctx.putImageData(imageData, 0, 0);
  } catch (e) {
    console.error("Spectrogram generation failed:", e);
    console.error("Error details:", {
      name: e instanceof Error ? e.name : "Unknown",
      message: e instanceof Error ? e.message : String(e),
      stack: e instanceof Error ? e.stack : undefined,
    });
    error.value = `Failed to generate spectrogram: ${e instanceof Error ? e.message : String(e)}`;

    // Draw placeholder
    canvas.width = 300;
    canvas.height = 100;
    ctx.fillStyle = "#394053";
    ctx.fillRect(0, 0, 300, 100);
    ctx.fillStyle = "#657392";
    ctx.font = "14px sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText("Spectrogram unavailable", 150, 50);
  } finally {
    isAnalyzing.value = false;

    if (audioContext && audioContext.state !== "closed") {
      audioContext.close();
    }
  }
};

// Generate on mount
onMounted(() => {
  console.log("Spectrogram: Component mounted, audioUrl:", props.audioUrl);
  if (props.audioUrl) {
    generateSpectrogram();
  }
});

// Watch for URL changes after mount
watch(
  () => props.audioUrl,
  (newUrl) => {
    console.log("Spectrogram: URL changed to:", newUrl);
    if (newUrl) {
      generateSpectrogram();
    }
  },
);
</script>

<template>
  <div class="space-y-2">
    <div v-if="label" class="text-sm text-noche-400">{{ label }}</div>

    <!-- Loading State -->
    <div
      v-if="isAnalyzing"
      class="flex items-center justify-center h-24 bg-noche-800 rounded-lg"
    >
      <div class="flex items-center gap-2 text-noche-400">
        <div
          class="w-4 h-4 border-2 border-sol-500 border-t-transparent rounded-full animate-spin"
        ></div>
        <span class="text-sm">Analyzing...</span>
      </div>
    </div>

    <!-- Spectrogram Canvas -->
    <canvas
      v-show="!isAnalyzing"
      ref="canvasRef"
      class="w-full h-32 rounded-lg bg-noche-800 object-cover"
      style="image-rendering: pixelated"
    />

    <!-- Error State -->
    <div v-if="error" class="text-xs text-tierra-400 text-center">
      {{ error }}
    </div>

    <!-- Frequency Labels -->
    <div
      v-if="!isAnalyzing && !error"
      class="flex justify-between text-xs text-noche-500 px-1"
    >
      <span>0 Hz</span>
      <span>Time →</span>
      <span>~4 kHz</span>
    </div>
  </div>
</template>
