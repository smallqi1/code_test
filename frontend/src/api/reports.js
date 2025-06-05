import axios from 'axios'

// 获取环境变量中的API基础URL，如果不存在则使用默认值
const API_BASE_URL = import.meta.env.VITE_REPORTS_API_BASE_URL || 'http://localhost:5003'

// 创建axios实例
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
  },
  timeout: 30000 // 30秒超时
})

/**
 * 获取报告历史记录
 * @returns {Promise} 报告历史记录列表
 */
export async function fetchReportHistory() {
  try {
    // 使用已创建的apiClient实例而不是单独的端口
    const response = await apiClient.get('/api/reports/history');
    
    // 确保返回的数据是数组
    if (Array.isArray(response.data)) {
      return response.data;
    } else if (response.data && Array.isArray(response.data.data)) {
      return response.data.data;
    } else {
      console.warn('报告历史API返回了非数组格式的数据:', response.data);
      return [];
    }
  } catch (error) {
    console.error('Error fetching report history:', error);
    // 确保总是返回一个数组，即使发生错误
    return [];
  }
}

/**
 * 生成新报告
 * @param {Object} reportData - 报告生成参数
 * @param {string} reportData.type - 报告类型 (daily, weekly, monthly等)
 * @param {string} reportData.startDate - 开始日期
 * @param {string} reportData.endDate - 结束日期
 * @param {string} reportData.region - 地区代码
 * @param {Object} reportData.content - 报告内容选项
 * @param {string} reportData.format - 报告格式 (pdf, word, excel, html)
 * @param {string} reportData.name - 报告名称
 * @returns {Promise} 生成的报告信息
 */
export async function generateReportRequest(reportData) {
  try {
    // 基本参数验证
    if (!reportData || !reportData.startDate || !reportData.endDate) {
      throw new Error('报告参数不完整，请确保填写必要的字段');
    }
    
    console.log('发送报告生成请求:', reportData)
    const response = await apiClient.post('/api/reports/generate', reportData)
    
    // 检查返回数据是否包含错误
    if (response.data && typeof response.data === 'object' && response.data.error) {
      console.error('服务器返回错误:', response.data.error);
      throw new Error(response.data.error);
    }
    
    // 检查是否为合法的响应
    if (!response.data) {
      console.error('服务器返回空响应');
      throw new Error('报告生成失败：服务器返回空响应');
    }
    
    return response.data
  } catch (error) {
    console.error('Error generating report:', error)
    
    // 处理响应数据中的错误
    if (error.response && error.response.data) {
      if (typeof error.response.data === 'object' && error.response.data.error) {
        // 服务器返回了明确的错误信息
        throw new Error(error.response.data.error);
      } else if (typeof error.response.data === 'string' && error.response.data.includes('error')) {
        // 尝试解析错误信息
        throw new Error(error.response.data);
      }
    }
    
    // 默认错误消息
    throw error
  }
}

/**
 * 获取特定报告详情
 * @param {string} reportId - 报告ID
 * @returns {Promise} 报告详细信息
 */
export async function getReportDetails(reportId) {
  try {
    if (!reportId) {
      throw new Error('报告ID不能为空');
    }
    
    const response = await apiClient.get(`/api/reports/${reportId}`)
    return response.data
  } catch (error) {
    console.error('Error fetching report details:', error)
    
    // 构建更友好的错误信息
    let errorMessage = '获取报告详情失败';
    
    if (error.response) {
      const status = error.response.status;
      
      if (error.response.data && error.response.data.error) {
        errorMessage = error.response.data.error;
      } else {
        switch (status) {
          case 404:
            errorMessage = '报告不存在或已被删除';
            break;
          case 500:
            errorMessage = '服务器获取报告详情时发生错误';
            break;
          default:
            errorMessage = `请求错误: ${status}`;
        }
      }
    } else if (error.request) {
      errorMessage = '无法连接到服务器，请检查网络连接';
    } else if (error.message) {
      errorMessage = error.message;
    }
    
    throw new Error(errorMessage);
  }
}

/**
 * 下载报告文件
 * @param {string} reportId - 报告ID
 * @param {string} format - 报告格式 (pdf, word, excel, html)
 * @param {Object} options - 额外选项，如进度回调
 * @returns {Promise} 下载操作结果
 */
export async function downloadReportFile(reportId, format, options = {}) {
  try {
    // 首先检查参数
    if (!reportId) {
      throw new Error('下载失败: 缺少报告ID');
    }
    
    const validFormats = ['pdf', 'word', 'excel', 'html'];
    if (format && !validFormats.includes(format.toLowerCase())) {
      console.warn(`不支持的格式: ${format}, 将使用默认格式`);
    }
    
    // 显示下载状态
    console.log(`开始下载报告 ID: ${reportId}, 格式: ${format || '默认'}`);
    
    // 确保reportId包含文件扩展名
    let filename = reportId;
    
    // 如果reportId不包含文件扩展名，根据format参数添加
    if (!reportId.includes('.')) {
      const formatExtMap = {
        pdf: '.pdf',
        word: '.docx',
        excel: '.xlsx',
        html: '.html'
      };
      const ext = formatExtMap[format?.toLowerCase()] || '.pdf';
      filename = `${reportId}${ext}`;
    }
    
    // 构建下载URL
    const downloadUrl = `${API_BASE_URL}/api/reports/download/${filename}`;
    
    console.log(`下载URL: ${downloadUrl}`);
    
    // 构建请求配置
    const requestConfig = {
      url: downloadUrl,
      method: 'GET',
      responseType: 'blob',
      // 增加超时时间，防止大文件下载超时
      timeout: 120000, // 2分钟
      // 重试配置
      retry: 2,
      retryDelay: 1500,
      // 合并用户提供的配置
      ...options
    };
    
    // 使用axios进行文件下载
    const response = await axios(requestConfig);
    
    // 检查响应状态
    if (response.status !== 200) {
      console.error(`下载失败: 服务器返回状态码 ${response.status}`);
      throw new Error(`下载失败: 服务器返回状态码 ${response.status}`);
    }
    
    // 检查响应数据类型
    if (!response.data) {
      console.error('下载失败: 服务器返回空数据');
      throw new Error('下载失败: 服务器返回空数据');
    }
    
    // 检查响应是否为错误信息（有时服务器会在错误时返回JSON而不是blob）
    if (response.data instanceof Blob && response.data.type.includes('application/json')) {
      // 尝试读取错误消息
      const errorText = await response.data.text();
      try {
        const errorJson = JSON.parse(errorText);
        if (errorJson.available_formats && errorJson.available_formats.length > 0) {
          // 如果有可用格式，给出更有用的提示
          const availableFormats = errorJson.available_formats.join(', ');
          throw new Error(`${errorJson.error || '下载失败'} (可用格式: ${availableFormats})`);
        } else {
          throw new Error(errorJson.error || '下载失败: 服务器返回了错误');
        }
      } catch (e) {
        // 如果无法解析JSON或没有error字段，则抛出原始错误
        if (e.message && e.message !== 'Unexpected token in JSON at position 0') {
          throw e;
        }
        throw new Error('下载失败: 服务器返回了错误');
      }
    }
    
    // 处理Content-Type为text/plain且包含错误信息的情况
    if (response.data instanceof Blob && response.data.type.includes('text/plain')) {
      const textContent = await response.data.text();
      if (textContent.toLowerCase().includes('error') || textContent.toLowerCase().includes('失败')) {
        throw new Error(`下载失败: ${textContent}`);
      }
    }
    
    // 创建Blob对象
    const blob = new Blob([response.data], {
      type: response.headers['content-type'] || 'application/octet-stream'
    });
    
    // 获取文件名
    let downloadFilename = getFilenameFromResponse(response, reportId, format);
    
    // 下载文件
    downloadBlob(blob, downloadFilename);
    
    return { success: true, filename: downloadFilename };
  } catch (error) {
    console.error('报告下载失败:', error);
    
    // 检查错误类型并给出更具体的错误消息
    let errorMessage = '下载失败: 未知错误';
    
    if (error.response) {
      // 服务器响应了错误状态码
      const status = error.response.status;
      console.error('服务器响应错误:', status);
      
      switch (status) {
        case 404:
          errorMessage = '下载失败: 报告不存在或已被删除';
          break;
        case 400:
          errorMessage = '下载失败: 请求参数错误或报告文件未生成';
          break;
        case 401:
          errorMessage = '下载失败: 未授权，请重新登录';
          break;
        case 403:
          errorMessage = '下载失败: 没有权限下载此报告';
          break;
        case 500:
          errorMessage = '下载失败: 服务器内部错误';
          break;
        default:
          errorMessage = `下载失败: 服务器返回错误 (${status})`;
      }
      
      // 尝试从响应中获取更详细的错误信息
      if (error.response.data) {
        try {
          // 如果响应是Blob类型，尝试读取内容
          if (error.response.data instanceof Blob) {
            const reader = new FileReader();
            reader.onload = () => {
              try {
                const errorData = JSON.parse(reader.result);
                if (errorData.error) {
                  console.error('服务器错误详情:', errorData.error);
                }
              } catch (e) {
                // 解析失败，尝试作为纯文本处理
                try {
                  if (reader.result && typeof reader.result === 'string') {
                    const textContent = reader.result;
                    if (textContent.toLowerCase().includes('error') || textContent.toLowerCase().includes('失败')) {
                      errorMessage = `下载失败: ${textContent}`;
                    }
                  }
                } catch (textError) {
                  // 忽略文本处理错误
                }
              }
            };
            reader.readAsText(error.response.data);
          } else if (error.response.data.error) {
            console.error('服务器错误详情:', error.response.data.error);
            errorMessage = `下载失败: ${error.response.data.error}`;
            
            // 如果有可用格式信息，添加到错误消息中
            if (error.response.data.available_formats && error.response.data.available_formats.length > 0) {
              const availableFormats = error.response.data.available_formats.join(', ');
              errorMessage += ` (可用格式: ${availableFormats})`;
            }
          } else if (typeof error.response.data === 'string') {
            // 处理纯文本错误响应
            errorMessage = `下载失败: ${error.response.data}`;
          }
        } catch (e) {
          // 解析错误信息失败，使用默认错误消息
          console.warn('解析错误响应失败:', e);
        }
      }
    } else if (error.request) {
      // 请求发送成功但没有收到响应
      console.error('无响应:', error.request);
      errorMessage = '下载失败: 服务器没有响应，请检查网络连接';
    } else if (error.message) {
      // 请求设置过程中出现问题
      errorMessage = `下载失败: ${error.message}`;
    }
    
    throw new Error(errorMessage);
  }
}

/**
 * 从响应头获取文件名
 * @private
 */
function getFilenameFromResponse(response, reportId, format) {
  let filename = `report-${reportId}`;
  const contentDisposition = response.headers['content-disposition'];
  
  if (contentDisposition) {
    try {
      // 尝试多种格式的filename提取
      const filenameRegex = /filename[^;=\n]*=(['"])*(.*)\1*/;
      const filenameMatches = contentDisposition.match(filenameRegex);
      if (filenameMatches && filenameMatches.length >= 3) {
        filename = filenameMatches[2];
      } else {
        // 尝试直接分割
        const parts = contentDisposition.split('filename=');
        if (parts.length >= 2) {
          filename = parts[1].replace(/["']/g, '').trim();
        }
      }
      
      // 处理URL编码的文件名
      if (filename.includes('%')) {
        try {
          filename = decodeURIComponent(filename);
        } catch (e) {
          console.warn('文件名解码失败:', e);
        }
      }
    } catch (e) {
      console.warn('从Content-Disposition解析文件名失败:', e);
    }
  }
  
  // 根据格式添加适当的扩展名
  if (!filename.includes('.')) {
    const formatExtMap = {
      pdf: '.pdf',
      word: '.docx',
      excel: '.xlsx',
      html: '.html'
    };
    filename += formatExtMap[format?.toLowerCase()] || '.pdf';
  }
  
  return filename;
}

/**
 * 下载Blob对象为文件
 * @private
 */
function downloadBlob(blob, filename) {
  // 创建临时下载链接
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', filename);
  document.body.appendChild(link);
  link.click();
  
  // 清理
  setTimeout(() => {
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
    console.log(`报告下载完成: ${filename}`);
  }, 100);
}

/**
 * 删除报告
 * @param {string} reportId - 报告ID
 * @returns {Promise} 操作结果
 */
export async function deleteReport(reportId) {
  try {
    if (!reportId) {
      throw new Error('删除失败: 缺少报告ID');
    }
    
    console.log(`开始删除报告 ID: ${reportId}`);
    
    const response = await apiClient.delete(`/api/reports/${reportId}`);
    return response.data;
  } catch (error) {
    console.error('删除报告失败:', error);
    
    // 构建更友好的错误信息
    let errorMessage = '删除报告失败';
    
    if (error.response) {
      const status = error.response.status;
      
      if (error.response.data && error.response.data.error) {
        errorMessage = error.response.data.error;
      } else {
        switch (status) {
          case 404:
            errorMessage = '报告不存在或已被删除';
            break;
          case 500:
            errorMessage = '服务器删除报告时发生错误';
            break;
          default:
            errorMessage = `请求错误: ${status}`;
        }
      }
    } else if (error.request) {
      errorMessage = '无法连接到服务器，请检查网络连接';
    } else if (error.message) {
      errorMessage = error.message;
    }
    
    throw new Error(errorMessage);
  }
} 