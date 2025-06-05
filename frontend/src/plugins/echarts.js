// ECharts插件配置
import * as echarts from 'echarts/core'

// 引入柱状图、折线图、饼图、散点图等组件
import { 
  BarChart,
  LineChart,
  PieChart,
  ScatterChart,
  RadarChart,
  GaugeChart,
  MapChart
} from 'echarts/charts'

// 引入提示框、标题、直角坐标系、图例、工具箱、数据区域缩放等组件
import {
  TitleComponent,
  TooltipComponent,
  GridComponent,
  DatasetComponent,
  TransformComponent,
  LegendComponent,
  ToolboxComponent,
  DataZoomComponent,
  VisualMapComponent,
  TimelineComponent,
  GraphicComponent,
  GeoComponent
} from 'echarts/components'

// 引入渲染器
import { CanvasRenderer } from 'echarts/renderers'

// 一次性注册所有组件，确保地图相关组件优先注册
echarts.use([
  // 地图相关组件（优先注册）
  MapChart,
  GeoComponent,
  
  // 图表组件
  BarChart,
  LineChart,
  PieChart,
  ScatterChart,
  RadarChart,
  GaugeChart,
  
  // 功能组件
  TitleComponent,
  TooltipComponent,
  GridComponent,
  DatasetComponent,
  TransformComponent,
  LegendComponent,
  ToolboxComponent,
  DataZoomComponent,
  VisualMapComponent,
  TimelineComponent,
  GraphicComponent,
  
  // 渲染器
  CanvasRenderer
]);

console.log('所有ECharts组件已注册完成');

// 定义关键函数 - 提前定义，解决引用顺序问题
// 提供获取地图状态的方法
const isMapRegistered = (mapName) => {
  try {
    const registeredMap = echarts.getMap(mapName);
    return !!registeredMap;
  } catch (e) {
    console.warn(`检查地图 ${mapName} 注册状态时出错:`, e);
    return false;
  }
};

// 简化坐标精度，减少地图数据量和渲染负担
const simplifyCoordinates = (coords) => {
  if (Array.isArray(coords)) {
    if (typeof coords[0] === 'number') {
      // 这是一个坐标点 [lng, lat]
      coords[0] = parseFloat(coords[0].toFixed(3));
      coords[1] = parseFloat(coords[1].toFixed(3));
    } else {
      // 这是坐标数组，递归处理
      coords.forEach(coord => simplifyCoordinates(coord));
    }
  }
};

// 主题配置
const lightTheme = {
  color: [
    '#1890ff', '#52c41a', '#faad14', '#f5222d', '#722ed1',
    '#13c2c2', '#eb2f96', '#fadb14', '#a0d911', '#fa8c16'
  ],
  backgroundColor: '#ffffff',
  textStyle: {},
  title: {
    textStyle: {
      color: '#333333'
    },
    subtextStyle: {
      color: '#666666'
    }
  },
  line: {
    itemStyle: {
      borderWidth: 1
    },
    lineStyle: {
      width: 2
    },
    symbolSize: 4,
    symbol: 'emptyCircle',
    smooth: false
  },
  radar: {
    itemStyle: {
      borderWidth: 1
    },
    lineStyle: {
      width: 2
    },
    symbolSize: 4,
    symbol: 'emptyCircle',
    smooth: false
  },
  bar: {
    itemStyle: {
      barBorderWidth: 0,
      barBorderColor: '#cccccc'
    }
  },
  pie: {
    itemStyle: {
      borderWidth: 0,
      borderColor: '#cccccc'
    }
  },
  scatter: {
    itemStyle: {
      borderWidth: 0,
      borderColor: '#cccccc'
    }
  },
  boxplot: {
    itemStyle: {
      borderWidth: 0,
      borderColor: '#cccccc'
    }
  },
  parallel: {
    itemStyle: {
      borderWidth: 0,
      borderColor: '#cccccc'
    }
  },
  sankey: {
    itemStyle: {
      borderWidth: 0,
      borderColor: '#cccccc'
    }
  },
  funnel: {
    itemStyle: {
      borderWidth: 0,
      borderColor: '#cccccc'
    }
  },
  gauge: {
    itemStyle: {
      borderWidth: 0,
      borderColor: '#cccccc'
    }
  },
  candlestick: {
    itemStyle: {
      color: '#f5222d',
      color0: '#52c41a',
      borderColor: '#f5222d',
      borderColor0: '#52c41a',
      borderWidth: 1
    }
  },
  graph: {
    itemStyle: {
      borderWidth: 0,
      borderColor: '#cccccc'
    },
    lineStyle: {
      width: 1,
      color: '#aaaaaa'
    },
    symbolSize: 4,
    symbol: 'emptyCircle',
    smooth: false,
    color: [
      '#1890ff', '#52c41a', '#faad14', '#f5222d', '#722ed1',
      '#13c2c2', '#eb2f96', '#fadb14', '#a0d911', '#fa8c16'
    ],
    label: {
      color: '#333333'
    }
  },
  map: {
    itemStyle: {
      areaColor: '#f3f3f3',
      borderColor: '#444',
      borderWidth: 0.5
    },
    label: {
      color: '#000',
      show: true
    },
    emphasis: {
      itemStyle: {
        areaColor: '#1890ff',
        borderColor: '#444',
        borderWidth: 1
      },
      label: {
        color: '#ffffff'
      }
    }
  },
  geo: {
    itemStyle: {
      areaColor: '#eee',
      borderColor: '#444',
      borderWidth: 0.5
    },
    label: {
      color: '#000'
    },
    emphasis: {
      itemStyle: {
        areaColor: 'rgba(24,144,255,0.5)',
        borderColor: '#444',
        borderWidth: 1
      },
      label: {
        color: '#ffffff'
      }
    }
  },
  categoryAxis: {
    axisLine: {
      show: true,
      lineStyle: {
        color: '#d9d9d9'
      }
    },
    axisTick: {
      show: false,
      lineStyle: {
        color: '#d9d9d9'
      }
    },
    axisLabel: {
      show: true,
      color: '#666666'
    },
    splitLine: {
      show: false,
      lineStyle: {
        color: [
          '#e8e8e8'
        ]
      }
    },
    splitArea: {
      show: false,
      areaStyle: {
        color: [
          'rgba(250,250,250,0.05)',
          'rgba(200,200,200,0.02)'
        ]
      }
    }
  },
  valueAxis: {
    axisLine: {
      show: false,
      lineStyle: {
        color: '#d9d9d9'
      }
    },
    axisTick: {
      show: false,
      lineStyle: {
        color: '#d9d9d9'
      }
    },
    axisLabel: {
      show: true,
      color: '#666666'
    },
    splitLine: {
      show: true,
      lineStyle: {
        color: [
          '#e8e8e8'
        ]
      }
    },
    splitArea: {
      show: false,
      areaStyle: {
        color: [
          'rgba(250,250,250,0.05)',
          'rgba(200,200,200,0.02)'
        ]
      }
    }
  },
  logAxis: {
    axisLine: {
      show: false,
      lineStyle: {
        color: '#d9d9d9'
      }
    },
    axisTick: {
      show: false,
      lineStyle: {
        color: '#d9d9d9'
      }
    },
    axisLabel: {
      show: true,
      color: '#666666'
    },
    splitLine: {
      show: true,
      lineStyle: {
        color: [
          '#e8e8e8'
        ]
      }
    },
    splitArea: {
      show: false,
      areaStyle: {
        color: [
          'rgba(250,250,250,0.05)',
          'rgba(200,200,200,0.02)'
        ]
      }
    }
  },
  timeAxis: {
    axisLine: {
      show: true,
      lineStyle: {
        color: '#d9d9d9'
      }
    },
    axisTick: {
      show: true,
      lineStyle: {
        color: '#d9d9d9'
      }
    },
    axisLabel: {
      show: true,
      color: '#666666'
    },
    splitLine: {
      show: false,
      lineStyle: {
        color: [
          '#e8e8e8'
        ]
      }
    },
    splitArea: {
      show: false,
      areaStyle: {
        color: [
          'rgba(250,250,250,0.05)',
          'rgba(200,200,200,0.02)'
        ]
      }
    }
  },
  toolbox: {
    iconStyle: {
      borderColor: '#999'
    },
    emphasis: {
      iconStyle: {
        borderColor: '#666'
      }
    }
  },
  legend: {
    textStyle: {
      color: '#666666'
    }
  },
  tooltip: {
    axisPointer: {
      lineStyle: {
        color: '#cccccc',
        width: 1
      },
      crossStyle: {
        color: '#cccccc',
        width: 1
      }
    }
  },
  timeline: {
    lineStyle: {
      color: '#1890ff',
      width: 2
    },
    itemStyle: {
      color: '#1890ff',
      borderWidth: 1
    },
    controlStyle: {
      color: '#1890ff',
      borderColor: '#1890ff',
      borderWidth: 0.5
    },
    checkpointStyle: {
      color: '#1890ff',
      borderColor: '#1890ff',
      borderWidth: 1
    },
    label: {
      color: '#666666'
    },
    emphasis: {
      itemStyle: {
        color: '#1890ff'
      },
      controlStyle: {
        color: '#1890ff',
        borderColor: '#1890ff',
        borderWidth: 0.5
      },
      label: {
        color: '#666666'
      }
    }
  },
  visualMap: {
    color: [
      '#1890ff',
      '#a3d8ff',
      '#e9f4ff'
    ]
  },
  dataZoom: {
    backgroundColor: 'rgba(255,255,255,0)',
    dataBackgroundColor: 'rgba(222,222,222,0.2)',
    fillerColor: 'rgba(24,144,255,0.2)',
    handleColor: '#1890ff',
    handleSize: '100%',
    textStyle: {
      color: '#999999'
    }
  },
  markPoint: {
    label: {
      color: '#333333'
    },
    emphasis: {
      label: {
        color: '#333333'
      }
    }
  }
}

const darkTheme = {
  color: [
    '#36a2e5', '#60c785', '#f6c94a', '#ec6372', '#9a64e5',
    '#3fbfbf', '#e45496', '#f6db54', '#c4e551', '#f59f41'
  ],
  backgroundColor: '#2d2d2d',
  textStyle: {},
  title: {
    textStyle: {
      color: '#f0f0f0'
    },
    subtextStyle: {
      color: '#b0b0b0'
    }
  },
  line: {
    itemStyle: {
      borderWidth: 1
    },
    lineStyle: {
      width: 2
    },
    symbolSize: 4,
    symbol: 'emptyCircle',
    smooth: false
  },
  radar: {
    itemStyle: {
      borderWidth: 1
    },
    lineStyle: {
      width: 2
    },
    symbolSize: 4,
    symbol: 'emptyCircle',
    smooth: false
  },
  bar: {
    itemStyle: {
      barBorderWidth: 0,
      barBorderColor: '#444444'
    }
  },
  pie: {
    itemStyle: {
      borderWidth: 0,
      borderColor: '#444444'
    }
  },
  scatter: {
    itemStyle: {
      borderWidth: 0,
      borderColor: '#444444'
    }
  },
  boxplot: {
    itemStyle: {
      borderWidth: 0,
      borderColor: '#444444'
    }
  },
  parallel: {
    itemStyle: {
      borderWidth: 0,
      borderColor: '#444444'
    }
  },
  sankey: {
    itemStyle: {
      borderWidth: 0,
      borderColor: '#444444'
    }
  },
  funnel: {
    itemStyle: {
      borderWidth: 0,
      borderColor: '#444444'
    }
  },
  gauge: {
    itemStyle: {
      borderWidth: 0,
      borderColor: '#444444'
    }
  },
  candlestick: {
    itemStyle: {
      color: '#ec6372',
      color0: '#60c785',
      borderColor: '#ec6372',
      borderColor0: '#60c785',
      borderWidth: 1
    }
  },
  graph: {
    itemStyle: {
      borderWidth: 0,
      borderColor: '#444444'
    },
    lineStyle: {
      width: 1,
      color: '#aaaaaa'
    },
    symbolSize: 4,
    symbol: 'emptyCircle',
    smooth: false,
    color: [
      '#36a2e5', '#60c785', '#f6c94a', '#ec6372', '#9a64e5',
      '#3fbfbf', '#e45496', '#f6db54', '#c4e551', '#f59f41'
    ],
    label: {
      color: '#eeeeee'
    }
  },
  map: {
    itemStyle: {
      areaColor: '#333333',
      borderColor: '#222222',
      borderWidth: 0.5
    },
    label: {
      color: '#e0e0e0',
      show: true
    },
    emphasis: {
      itemStyle: {
        areaColor: '#36a2e5',
        borderColor: '#222222',
        borderWidth: 1
      },
      label: {
        color: '#ffffff'
      }
    }
  },
  geo: {
    itemStyle: {
      areaColor: '#444444',
      borderColor: '#222222',
      borderWidth: 0.5
    },
    label: {
      color: '#e0e0e0'
    },
    emphasis: {
      itemStyle: {
        areaColor: 'rgba(54,162,229,0.5)',
        borderColor: '#222222',
        borderWidth: 1
      },
      label: {
        color: '#ffffff'
      }
    }
  },
  categoryAxis: {
    axisLine: {
      show: true,
      lineStyle: {
        color: '#666666'
      }
    },
    axisTick: {
      show: false,
      lineStyle: {
        color: '#666666'
      }
    },
    axisLabel: {
      show: true,
      color: '#b0b0b0'
    },
    splitLine: {
      show: false,
      lineStyle: {
        color: [
          '#555555'
        ]
      }
    },
    splitArea: {
      show: false,
      areaStyle: {
        color: [
          'rgba(50,50,50,0.05)',
          'rgba(40,40,40,0.02)'
        ]
      }
    }
  },
  valueAxis: {
    axisLine: {
      show: false,
      lineStyle: {
        color: '#666666'
      }
    },
    axisTick: {
      show: false,
      lineStyle: {
        color: '#666666'
      }
    },
    axisLabel: {
      show: true,
      color: '#b0b0b0'
    },
    splitLine: {
      show: true,
      lineStyle: {
        color: [
          '#555555'
        ]
      }
    },
    splitArea: {
      show: false,
      areaStyle: {
        color: [
          'rgba(50,50,50,0.05)',
          'rgba(40,40,40,0.02)'
        ]
      }
    }
  },
  logAxis: {
    axisLine: {
      show: false,
      lineStyle: {
        color: '#666666'
      }
    },
    axisTick: {
      show: false,
      lineStyle: {
        color: '#666666'
      }
    },
    axisLabel: {
      show: true,
      color: '#b0b0b0'
    },
    splitLine: {
      show: true,
      lineStyle: {
        color: [
          '#555555'
        ]
      }
    },
    splitArea: {
      show: false,
      areaStyle: {
        color: [
          'rgba(50,50,50,0.05)',
          'rgba(40,40,40,0.02)'
        ]
      }
    }
  },
  timeAxis: {
    axisLine: {
      show: true,
      lineStyle: {
        color: '#666666'
      }
    },
    axisTick: {
      show: true,
      lineStyle: {
        color: '#666666'
      }
    },
    axisLabel: {
      show: true,
      color: '#b0b0b0'
    },
    splitLine: {
      show: false,
      lineStyle: {
        color: [
          '#555555'
        ]
      }
    },
    splitArea: {
      show: false,
      areaStyle: {
        color: [
          'rgba(50,50,50,0.05)',
          'rgba(40,40,40,0.02)'
        ]
      }
    }
  },
  toolbox: {
    iconStyle: {
      borderColor: '#999999'
    },
    emphasis: {
      iconStyle: {
        borderColor: '#b0b0b0'
      }
    }
  },
  legend: {
    textStyle: {
      color: '#b0b0b0'
    }
  },
  tooltip: {
    axisPointer: {
      lineStyle: {
        color: '#666666',
        width: 1
      },
      crossStyle: {
        color: '#666666',
        width: 1
      }
    }
  },
  timeline: {
    lineStyle: {
      color: '#36a2e5',
      width: 2
    },
    itemStyle: {
      color: '#36a2e5',
      borderWidth: 1
    },
    controlStyle: {
      color: '#36a2e5',
      borderColor: '#36a2e5',
      borderWidth: 0.5
    },
    checkpointStyle: {
      color: '#36a2e5',
      borderColor: '#36a2e5',
      borderWidth: 1
    },
    label: {
      color: '#b0b0b0'
    },
    emphasis: {
      itemStyle: {
        color: '#36a2e5'
      },
      controlStyle: {
        color: '#36a2e5',
        borderColor: '#36a2e5',
        borderWidth: 0.5
      },
      label: {
        color: '#b0b0b0'
      }
    }
  },
  visualMap: {
    color: [
      '#36a2e5',
      '#86c5ea',
      '#c4e3fb'
    ]
  },
  dataZoom: {
    backgroundColor: 'rgba(40,40,40,0)',
    dataBackgroundColor: 'rgba(80,80,80,0.2)',
    fillerColor: 'rgba(54,162,229,0.2)',
    handleColor: '#36a2e5',
    handleSize: '100%',
    textStyle: {
      color: '#b0b0b0'
    }
  },
  markPoint: {
    label: {
      color: '#eeeeee'
    },
    emphasis: {
      label: {
        color: '#eeeeee'
      }
    }
  }
}

// 注册主题
echarts.registerTheme('light', lightTheme)
echarts.registerTheme('dark', darkTheme)

// 获取主题
const getChartTheme = (isDark = false) => {
  return isDark ? 'dark' : 'light'
}

// 优化地图加载函数，增加重试机制和错误处理
const loadGuangdongMap = async (retryCount = 2) => {
  // 检查是否已注册
  if (isMapRegistered('guangdong')) {
    console.log('广东省地图数据已注册，无需重新加载');
    return true;
  }
  
  try {
    console.log('广东省地图数据加载中...');
    
    // 定义所有可能的地图路径
    const mapPaths = [
      '/maps/guangdong.json',
      '/guangdong.json',
      '/static/maps/guangdong.json',
      '/assets/maps/guangdong.json'
    ];
    
    // 优先从缓存中读取
    const cachedMapData = localStorage.getItem('guangdong_map_data');
    if (cachedMapData) {
      try {
        const mapData = JSON.parse(cachedMapData);
        if (mapData && mapData.features && mapData.features.length > 0) {
          console.log('从缓存加载广东省地图数据');
          echarts.registerMap('guangdong', mapData);
          return true;
        }
      } catch (cacheError) {
        console.warn('缓存的地图数据无效，将从服务器加载', cacheError);
        localStorage.removeItem('guangdong_map_data');
      }
    }
    
    // 依次尝试所有路径
    let lastError = null;
    for (const path of mapPaths) {
      try {
        const response = await fetch(path);
        if (response.ok) {
          return await processMapResponse(response);
        }
      } catch (e) {
        lastError = e;
        console.warn(`从${path}加载地图失败:`, e);
      }
    }
    
    // 所有路径都失败时，重试或使用备用简化地图
    if (retryCount > 0) {
      console.log(`地图加载失败，${retryCount}秒后重试...`);
      // 使用setTimeout而不是直接递归，避免调用栈溢出
      return new Promise(resolve => {
        setTimeout(async () => {
          const result = await loadGuangdongMap(retryCount - 1);
          resolve(result);
        }, 1000);
      });
    }
    
    // 所有重试都失败，使用备用简化地图
    console.warn('所有地图加载尝试均失败，使用备用简化地图');
    return preloadGuangdongMap();
  } catch (error) {
    console.error('广东省地图数据加载失败:', error);
    return preloadGuangdongMap();
  }
};

// 提取处理响应的函数，优化并添加缓存逻辑
const processMapResponse = async (response) => {
  try {
    // 解析JSON数据
    const mapData = await response.json();
    
    // 验证地图数据
    if (!mapData || !mapData.features || mapData.features.length === 0) {
      throw new Error('地图数据格式无效');
    }
    
    // 优化地图数据
    if (mapData.features) {
      // 简化地图数据中的坐标精度，减少渲染负担
      mapData.features.forEach(feature => {
        if (feature.geometry && feature.geometry.coordinates) {
          simplifyCoordinates(feature.geometry.coordinates);
        }
      });
    }
    
    // 保存到本地缓存，但使用try-catch避免存储问题影响主流程
    try {
      localStorage.setItem('guangdong_map_data', JSON.stringify(mapData));
    } catch (cacheError) {
      console.warn('无法缓存地图数据:', cacheError);
    }
    
    // 注册地图数据
    echarts.registerMap('guangdong', mapData);
    console.log('广东省地图数据加载并注册成功');
    
    return true;
  } catch (error) {
    console.error('处理地图数据失败:', error);
    throw error;
  }
};

// 修改预加载广东省简化地图函数 - 作为备用
const preloadGuangdongMap = () => {
  try {
    // 广东省主要城市的边界轮廓 - 使用更精细的多边形定义
    const betterGdMap = {
      "type": "FeatureCollection",
      "features": [
        {
          "id": "440100",
          "type": "Feature",
          "properties": { "name": "广州市", "cp": [113.280637, 23.125178] },
          "geometry": { 
            "type": "Polygon", 
            "coordinates": [[[113.1, 23.0], [113.4, 23.0], [113.5, 23.3], [113.3, 23.5], [113.0, 23.3], [113.1, 23.0]]]
          }
        },
        {
          "id": "440300",
          "type": "Feature",
          "properties": { "name": "深圳市", "cp": [114.085947, 22.547] },
          "geometry": { 
            "type": "Polygon", 
            "coordinates": [[[113.8, 22.4], [114.3, 22.5], [114.4, 22.7], [114.0, 22.8], [113.8, 22.6], [113.8, 22.4]]]
          }
        },
        {
          "id": "440400",
          "type": "Feature", 
          "properties": { "name": "珠海市", "cp": [113.553986, 22.224979] },
          "geometry": { 
            "type": "Polygon", 
            "coordinates": [[[113.3, 22.0], [113.6, 22.1], [113.7, 22.4], [113.5, 22.5], [113.3, 22.3], [113.3, 22.0]]]
          }
        },
        {
          "id": "440500",
          "type": "Feature", 
          "properties": { "name": "汕头市", "cp": [116.708463, 23.37102] },
          "geometry": { 
            "type": "Polygon", 
            "coordinates": [[[116.5, 23.2], [116.9, 23.3], [117.0, 23.5], [116.8, 23.6], [116.5, 23.5], [116.5, 23.2]]]
          }
        },
        {
          "id": "440600",
          "type": "Feature", 
          "properties": { "name": "佛山市", "cp": [113.134026, 23.035095] },
          "geometry": { 
            "type": "Polygon", 
            "coordinates": [[[112.8, 22.8], [113.2, 22.9], [113.3, 23.1], [113.1, 23.2], [112.8, 23.1], [112.8, 22.8]]]
          }
        },
        {
          "id": "440700",
          "type": "Feature", 
          "properties": { "name": "江门市", "cp": [113.094942, 22.590431] },
          "geometry": { 
            "type": "Polygon", 
            "coordinates": [[[112.6, 22.3], [113.1, 22.4], [113.2, 22.7], [112.9, 22.9], [112.5, 22.7], [112.6, 22.3]]]
          }
        },
        {
          "id": "440800",
          "type": "Feature", 
          "properties": { "name": "湛江市", "cp": [110.364977, 21.274898] },
          "geometry": { 
            "type": "Polygon", 
            "coordinates": [[[110.0, 20.9], [110.6, 21.0], [110.7, 21.4], [110.4, 21.6], [110.0, 21.4], [110.0, 20.9]]]
          }
        },
        {
          "id": "440900",
          "type": "Feature", 
          "properties": { "name": "茂名市", "cp": [110.919229, 21.659751] },
          "geometry": { 
            "type": "Polygon", 
            "coordinates": [[[110.5, 21.4], [111.2, 21.5], [111.3, 21.9], [111.0, 22.0], [110.6, 21.8], [110.5, 21.4]]]
          }
        },
        {
          "id": "441200",
          "type": "Feature", 
          "properties": { "name": "肇庆市", "cp": [112.472529, 23.051546] },
          "geometry": { 
            "type": "Polygon", 
            "coordinates": [[[112.0, 22.8], [112.6, 22.9], [112.8, 23.2], [112.5, 23.4], [112.0, 23.3], [112.0, 22.8]]]
          }
        },
        {
          "id": "441300",
          "type": "Feature", 
          "properties": { "name": "惠州市", "cp": [114.412599, 23.079404] },
          "geometry": { 
            "type": "Polygon", 
            "coordinates": [[[114.1, 22.8], [114.7, 22.9], [114.8, 23.3], [114.4, 23.4], [114.0, 23.2], [114.1, 22.8]]]
          }
        },
        {
          "id": "441900",
          "type": "Feature", 
          "properties": { "name": "东莞市", "cp": [113.746262, 23.046237] },
          "geometry": { 
            "type": "Polygon", 
            "coordinates": [[[113.6, 22.9], [114.0, 23.0], [114.0, 23.2], [113.8, 23.2], [113.6, 23.1], [113.6, 22.9]]]
          }
        },
        {
          "id": "442000",
          "type": "Feature", 
          "properties": { "name": "中山市", "cp": [113.382391, 22.521113] },
          "geometry": { 
            "type": "Polygon", 
            "coordinates": [[[113.2, 22.4], [113.5, 22.5], [113.5, 22.7], [113.3, 22.7], [113.2, 22.6], [113.2, 22.4]]]
          }
        },
        {
          "id": "445100",
          "type": "Feature", 
          "properties": { "name": "潮州市", "cp": [116.632301, 23.661701] },
          "geometry": { 
            "type": "Polygon", 
            "coordinates": [[[116.4, 23.5], [116.8, 23.6], [116.9, 23.8], [116.7, 23.9], [116.4, 23.7], [116.4, 23.5]]]
          }
        },
        {
          "id": "445200",
          "type": "Feature", 
          "properties": { "name": "揭阳市", "cp": [116.372834, 23.549993] },
          "geometry": { 
            "type": "Polygon", 
            "coordinates": [[[116.1, 23.3], [116.6, 23.4], [116.7, 23.7], [116.4, 23.8], [116.0, 23.6], [116.1, 23.3]]]
          }
        },
        {
          "id": "445300",
          "type": "Feature", 
          "properties": { "name": "云浮市", "cp": [112.044439, 22.929801] },
          "geometry": { 
            "type": "Polygon", 
            "coordinates": [[[111.7, 22.7], [112.3, 22.8], [112.4, 23.1], [112.1, 23.2], [111.7, 23.0], [111.7, 22.7]]]
          }
        },
        {
          "id": "441400",
          "type": "Feature", 
          "properties": { "name": "梅州市", "cp": [116.117582, 24.299112] },
          "geometry": { 
            "type": "Polygon", 
            "coordinates": [[[115.8, 24.0], [116.4, 24.1], [116.5, 24.5], [116.2, 24.6], [115.8, 24.4], [115.8, 24.0]]]
          }
        },
        {
          "id": "441500",
          "type": "Feature", 
          "properties": { "name": "汕尾市", "cp": [115.375279, 22.786211] },
          "geometry": { 
            "type": "Polygon", 
            "coordinates": [[[115.1, 22.5], [115.6, 22.6], [115.7, 22.9], [115.4, 23.0], [115.1, 22.8], [115.1, 22.5]]]
          }
        },
        {
          "id": "441600",
          "type": "Feature", 
          "properties": { "name": "河源市", "cp": [114.697802, 23.746266] },
          "geometry": { 
            "type": "Polygon", 
            "coordinates": [[[114.4, 23.5], [115.0, 23.6], [115.1, 24.0], [114.8, 24.1], [114.3, 23.9], [114.4, 23.5]]]
          }
        },
        {
          "id": "441700",
          "type": "Feature", 
          "properties": { "name": "阳江市", "cp": [111.975107, 21.859222] },
          "geometry": { 
            "type": "Polygon", 
            "coordinates": [[[111.6, 21.6], [112.2, 21.7], [112.3, 22.0], [112.0, 22.1], [111.6, 21.9], [111.6, 21.6]]]
          }
        },
        {
          "id": "441800",
          "type": "Feature", 
          "properties": { "name": "清远市", "cp": [113.051227, 23.685022] },
          "geometry": { 
            "type": "Polygon", 
            "coordinates": [[[112.7, 23.4], [113.3, 23.5], [113.4, 23.9], [113.1, 24.0], [112.7, 23.8], [112.7, 23.4]]]
          }
        },
        {
          "id": "440200",
          "type": "Feature", 
          "properties": { "name": "韶关市", "cp": [113.591544, 24.801322] },
          "geometry": { 
            "type": "Polygon", 
            "coordinates": [[[113.2, 24.5], [113.9, 24.6], [114.0, 25.0], [113.7, 25.1], [113.2, 24.9], [113.2, 24.5]]]
          }
        }
      ]
    };
    
    // 注册更丰富、更准确的广东地图 - 直接覆盖原有注册，无需先清除
    echarts.registerMap('guangdong', betterGdMap);
    console.log('已注册简化的广东省地图数据作为备用');
    
    return true;
  } catch (error) {
    console.warn('注册广东省简化地图失败:', error);
    return false;
  }
};

// 安全地设置图表选项
const safeSetOption = (chartInstance, options) => {
  if (!chartInstance || !options) {
    console.warn('图表实例或选项为空，无法设置选项');
    return false;
  }
  
  try {
    // 创建深拷贝
    const safeOptions = JSON.parse(JSON.stringify(options));
    
    // 确保所有Series都有正确的类型定义
    if (safeOptions.series && Array.isArray(safeOptions.series)) {
      safeOptions.series.forEach(series => {
        // 确保series有一个类型
        series.type = series.type || 'line';
        
        // 如果是地图类型，进行特殊处理
        if (series.type === 'map') {
          series.map = series.map || 'guangdong';
          series.mapType = 'map';
          
          // 处理地图数据
          if (series.data && Array.isArray(series.data)) {
            series.data = series.data.map(item => {
              if (typeof item !== 'object') {
                return { name: '未知', value: 0, type: 'map' };
              }
              return {
                ...item,
                name: item.name || '未知',
                value: typeof item.value === 'number' ? item.value : 0,
                type: 'map'
              };
            });
          }
        }
      });
    }
    
    // 设置选项
    chartInstance.setOption(safeOptions);
    return true;
  } catch (e) {
    console.error('安全设置图表选项失败:', e);
    return false;
  }
};

// 立即加载广东地图数据
const mapPreloaded = loadGuangdongMap();

// 诊断地图问题的函数
const diagnoseMapIssues = (mapName = 'guangdong') => {
  console.log('开始诊断地图问题...');
  
  // 检查地图是否已注册
  const mapRegistered = isMapRegistered(mapName);
  console.log(`地图 ${mapName} 注册状态:`, mapRegistered ? '已注册' : '未注册');
  
  // 如果未注册，尝试重新加载
  if (!mapRegistered) {
    console.log('地图未注册，正在尝试重新加载...');
    return loadGuangdongMap().then(result => {
      console.log('重新加载结果:', result ? '成功' : '失败');
      return result;
    });
  }
  
  return Promise.resolve(true);
};

// 确保地图已注册
const ensureMapRegistered = (mapName, mapData) => {
  try {
    // 先检查地图是否已注册
    if (isMapRegistered(mapName)) {
      return true;
    }
    
    // 如果mapName是'guangdong'但没有提供mapData，尝试使用缓存或备用地图
    if (mapName === 'guangdong' && !mapData) {
      try {
        // 先尝试从localStorage读取缓存的地图数据
        const cachedMapData = localStorage.getItem('guangdong_map_data');
        if (cachedMapData) {
          try {
            const parsedData = JSON.parse(cachedMapData);
            if (parsedData && parsedData.features && parsedData.features.length > 0) {
              echarts.registerMap('guangdong', parsedData);
              return true;
            }
          } catch (e) {
            console.warn('解析缓存的地图数据出错:', e);
          }
        }
        
        // 如果缓存不可用，使用备用简化地图
        return preloadGuangdongMap();
      } catch (e) {
        console.error('确保广东地图注册失败:', e);
        return preloadGuangdongMap();
      }
    }
    
    // 如果提供了地图数据，注册它
    if (mapData) {
      try {
        // 确保地图数据格式正确
        if (!mapData.type || !mapData.features || !Array.isArray(mapData.features)) {
          console.error(`地图 ${mapName} 数据格式错误，尝试使用备用地图`);
          return mapName === 'guangdong' ? preloadGuangdongMap() : false;
        }
        
        // 注册地图
        echarts.registerMap(mapName, mapData);
        console.log(`地图 ${mapName} 已成功注册`);
        return true;
      } catch (error) {
        console.error(`注册地图 ${mapName} 失败:`, error);
        return mapName === 'guangdong' ? preloadGuangdongMap() : false;
      }
    }
    
    return false;
  } catch (e) {
    console.error(`确保地图 ${mapName} 注册时出错:`, e);
    // 对于广东地图，总是确保有备用方案
    return mapName === 'guangdong' ? preloadGuangdongMap() : false;
  }
};

// 导出所需的内容
export {
  echarts,
  getChartTheme,
  loadGuangdongMap,
  preloadGuangdongMap,
  isMapRegistered,
  safeSetOption,
  ensureMapRegistered,
  diagnoseMapIssues,
  mapPreloaded
} 