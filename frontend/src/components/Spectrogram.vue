<script setup lang="ts">
import { ref, watch, onMounted, nextTick } from "vue";

const props = defineProps<{
  audioUrl: string;
  maxDuration?: number; // If provided, scale spectrogram to this duration
}>();

const emit = defineEmits<{
  (e: "duration", duration: number): void;
}>();

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

    // Calculate width based on maxDuration if provided
    const durationRatio = props.maxDuration
      ? audioBuffer.duration / props.maxDuration
      : 1;
    const baseWidth = Math.min(numFrames, maxWidth);
    const displayWidth = baseWidth; // Full canvas width
    const spectrogramWidth = Math.floor(baseWidth * durationRatio); // Actual spectrogram portion
    const displayHeight = Math.min(numBins, maxHeight);

    canvas.width = displayWidth;
    canvas.height = displayHeight;

    const windowFunc = hannWindow(FFT_SIZE);
    const magnitudes: number[][] = [];
    let maxMagnitude = 0;

    const frameStep = Math.max(1, Math.floor(numFrames / spectrogramWidth));

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

    // Draw spectrogram data (only up to spectrogramWidth)
    const actualCols = Math.min(magnitudes.length, spectrogramWidth);
    for (let col = 0; col < actualCols; col++) {
      const frameMags = magnitudes[col];

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

onMounted(() => {
  if (props.audioUrl) {
    generateSpectrogram();
  }
});

watch(
  () => props.audioUrl,
  (newUrl) => {
    if (newUrl) {
      generateSpectrogram();
    }
  },
);

// Re-render if maxDuration changes
watch(
  () => props.maxDuration,
  () => {
    if (props.audioUrl) {
      generateSpectrogram();
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
      <span class="text-xs text-noche-500">Spectrogram unavailable</span>
    </div>
  </div>
</template>
