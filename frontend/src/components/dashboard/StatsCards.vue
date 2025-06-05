<template>
  <div class="stats-cards">
    <div 
      v-for="(stat, index) in stats" 
      :key="index" 
      :class="['stats-card', stat.className]"
    >
      <div class="card-content">
        <div class="card-header">
          <div class="card-label">{{ stat.label }}</div>
          <div class="icon-wrapper" :style="{ backgroundColor: stat.iconColor + '15' }">
            <component 
              :is="stat.icon" 
              class="card-icon" 
              :style="{ color: stat.iconColor }" 
            />
          </div>
        </div>
        <div 
          class="card-value" 
          :style="{ color: stat.valueColor }"
        >
          <template v-if="loading">
            <span class="skeleton skeleton-value"></span>
          </template>
          <template v-else>{{ stat.value }}</template>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { defineComponent } from 'vue';
import { 
  Location, 
  CircleCheckFilled, 
  Warning, 
  AlarmClock 
} from '@element-plus/icons-vue';

export default defineComponent({
  name: 'StatsCards',
  components: {
    Location,
    CircleCheckFilled,
    Warning,
    AlarmClock
  },
  props: {
    stats: {
      type: Array,
      required: true
    },
    loading: {
      type: Boolean,
      default: false
    }
  }
});
</script>

<style scoped>
.stats-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 24px;
  margin-bottom: 30px;
  width: 100%;
  margin-top: 20px;
}

.stats-card {
  background-color: white;
  border-radius: 10px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
  height: 120px;
  border-bottom: 3px solid transparent;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.stats-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.08);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}

.icon-wrapper {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.card-icon {
  font-size: 1.25rem !important;
  width: 20px !important;
  height: 20px !important;
}

.card-content {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.card-value {
  font-size: 34px;
  font-weight: 700;
  line-height: 1.1;
}

.card-label {
  font-size: 15px;
  color: #606266;
  font-weight: 500;
}

.city-card {
  background: white;
  border-bottom: 3px solid #1976D2;
}

.good-card {
  background: white;
  border-bottom: 3px solid #4CAF50;
}

.light-card {
  background: white;
  border-bottom: 3px solid #FFA000;
}

.heavy-card {
  background: white;
  border-bottom: 3px solid #E53935;
}

.skeleton {
  display: inline-block;
  background: linear-gradient(90deg, #f2f2f2 25%, #e0e0e0 50%, #f2f2f2 75%);
  background-size: 200% 100%;
  animation: loading 1.5s infinite;
  border-radius: 4px;
}

.skeleton-value {
  width: 60px;
  height: 34px;
}

@keyframes loading {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}

/* 响应式调整 */
@media (max-width: 1200px) {
  .stats-cards {
    grid-template-columns: repeat(4, 1fr);
    gap: 20px;
  }
}

@media (max-width: 992px) {
  .stats-cards {
    grid-template-columns: repeat(2, 1fr);
    gap: 16px;
  }
}

@media (max-width: 768px) {
  .stats-cards {
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
  }
  
  .card-value {
    font-size: 28px;
  }
  
  .icon-wrapper {
    width: 32px;
    height: 32px;
  }
  
  .card-icon {
    font-size: 1.1rem !important;
    width: 16px !important;
    height: 16px !important;
  }
  
  .card-label {
    font-size: 14px;
  }
  
  .stats-card {
    padding: 16px;
    height: 100px;
  }
}

@media (max-width: 480px) {
  .stats-cards {
    grid-template-columns: repeat(1, 1fr);
    gap: 12px;
  }
  
  .stats-card {
    height: 90px;
  }
}
</style> 