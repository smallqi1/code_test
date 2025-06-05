<template>
  <span>{{ displayValue }}</span>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue';

// 组件属性
const props = defineProps({
  startVal: {
    type: Number,
    default: 0
  },
  endVal: {
    type: Number,
    default: 100
  },
  duration: {
    type: Number,
    default: 2000
  },
  autoplay: {
    type: Boolean,
    default: true
  },
  decimals: {
    type: Number,
    default: 0
  },
  decimal: {
    type: String,
    default: '.'
  },
  separator: {
    type: String,
    default: ','
  },
  prefix: {
    type: String,
    default: ''
  },
  suffix: {
    type: String,
    default: ''
  },
  useEasing: {
    type: Boolean,
    default: true
  },
  easingFn: {
    type: Function,
    default: (t, b, c, d) => {
      return c * (-Math.pow(2, -10 * t / d) + 1) * 1024 / 1023 + b;
    }
  }
});

// 响应式数据
const localStartVal = ref(props.startVal);
const displayValue = ref(formatValue(props.startVal));
const localDuration = ref(props.duration);
const startTime = ref(null);
const remaining = ref(0);
const rAF = ref(null);

// 方法
function formatValue(value) {
  const val = value.toFixed(props.decimals);
  const parts = val.toString().split('.');
  
  // 添加千位分隔符
  parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, props.separator);
  
  // 构建最终结果
  let formatted = props.prefix + parts.join(props.decimal) + props.suffix;
  return formatted;
}

function countUp() {
  if (!startTime.value) startTime.value = Date.now();
  
  const timestamp = Date.now();
  const progress = timestamp - startTime.value;
  remaining.value = Math.max(0, localDuration.value - progress);
  
  // 计算当前值
  let val;
  if (props.useEasing) {
    val = props.startVal + props.easingFn(
      progress,
      0,
      props.endVal - props.startVal,
      localDuration.value
    );
  } else {
    val = props.startVal + (props.endVal - props.startVal) * (progress / localDuration.value);
  }
  
  val = (props.endVal > props.startVal) 
    ? Math.min(props.endVal, val) 
    : Math.max(props.endVal, val);
  
  // 更新显示值
  displayValue.value = formatValue(val);
  
  // 继续动画或停止
  if (progress < localDuration.value) {
    rAF.value = requestAnimationFrame(countUp);
  } else {
    displayValue.value = formatValue(props.endVal);
  }
}

function start() {
  localStartVal.value = props.startVal;
  startTime.value = null;
  localDuration.value = props.duration;
  rAF.value = requestAnimationFrame(countUp);
}

function reset() {
  if (rAF.value) {
    cancelAnimationFrame(rAF.value);
    rAF.value = null;
  }
  startTime.value = null;
  displayValue.value = formatValue(props.startVal);
}

// 监听属性变化
watch(() => props.endVal, (newVal) => {
  if (props.autoplay) {
    start();
  }
});

// 生命周期钩子
onMounted(() => {
  if (props.autoplay) {
    start();
  }
});

onUnmounted(() => {
  if (rAF.value) {
    cancelAnimationFrame(rAF.value);
  }
});

// 暴露方法给父组件
defineExpose({
  start,
  reset
});
</script>

<style scoped>
span {
  display: inline-block;
  transition: transform 0.3s;
}
span:hover {
  transform: scale(1.1);
}
</style> 