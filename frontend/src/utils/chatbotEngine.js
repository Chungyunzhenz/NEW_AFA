const SIGNAL_LABEL = {
  GREEN: '綠燈（正常）',
  YELLOW: '黃燈（注意）',
  RED: '紅燈（警戒）',
  UNKNOWN: '資料不足',
};

/**
 * Rule-based chatbot engine.
 * generateResponse(userInput, context) → string reply
 */
export function generateResponse(userInput, context = {}) {
  const input = (userInput || '').trim().toLowerCase();
  if (!input) return '請輸入您想詢問的問題。';

  // Greeting
  if (/^(你好|哈囉|嗨|hi|hello|hey)/.test(input)) {
    return '您好！我是農產助手，可以回答價格、趨勢、燈號預警、預測等相關問題。請問有什麼需要幫忙的？';
  }

  // Traffic light / alert
  if (/燈號|警示|紅燈|黃燈|綠燈|預警|alert/.test(input)) {
    const tl = context.trafficLight;
    if (!tl || !tl.data_available) {
      return '目前尚無燈號資料，請先選擇作物並確認資料已載入。';
    }
    const overall = context.overallSignal || 'UNKNOWN';
    const lines = [
      `目前整體燈號：${SIGNAL_LABEL[overall] || overall}`,
    ];
    if (tl.supply_index != null) lines.push(`・供給指數：${tl.supply_index}`);
    if (tl.price_drop_pct != null) lines.push(`・價格跌幅：${tl.price_drop_pct}%`);
    if (tl.area_growth_pct != null) lines.push(`・面積成長率：${tl.area_growth_pct}%`);
    return lines.join('\n');
  }

  // Price query
  if (/價格|多少錢|均價|行情|price/.test(input)) {
    const td = context.tradingData;
    if (!td || td.length === 0) {
      return '目前尚無交易資料，請先選擇作物。';
    }
    const latest = td[td.length - 1];
    const price = latest?.value ?? latest?.avgPrice ?? latest?.avg_price ?? latest?.price_avg;
    if (price != null) {
      const cropLabel = context.cropLabel || '所選作物';
      return `${cropLabel}最新平均價格為 NT$ ${Number(price).toLocaleString('zh-TW', { maximumFractionDigits: 1 })}（資料日期：${latest?.date || latest?.period || '未知'}）。`;
    }
    return '找到交易資料，但價格欄位為空。';
  }

  // Trend query
  if (/趨勢|走勢|漲跌|漲|跌|trend/.test(input)) {
    const td = context.tradingData;
    if (!td || td.length < 2) {
      return '資料不足以分析趨勢，請確認已選擇作物並有足夠歷史資料。';
    }
    const getPrice = (d) => d?.value ?? d?.avgPrice ?? d?.avg_price ?? d?.price_avg ?? 0;
    const recent = td.slice(-7);
    const first = getPrice(recent[0]);
    const last = getPrice(recent[recent.length - 1]);
    if (first > 0) {
      const changePct = ((last - first) / first * 100).toFixed(1);
      const dir = changePct > 0 ? '上漲' : changePct < 0 ? '下跌' : '持平';
      return `近期趨勢：價格${dir} ${Math.abs(changePct)}%（從 ${first.toLocaleString()} 到 ${last.toLocaleString()}）。`;
    }
    return '近期資料不足以計算趨勢。';
  }

  // Prediction query
  if (/預測|未來|預估|forecast|predict/.test(input)) {
    const pred = context.predictions;
    if (!pred || pred.length === 0) {
      return '目前沒有預測資料。請先選擇作物查看預測結果。';
    }
    const next = pred[0];
    const val = next?.value ?? next?.predicted ?? next?.forecast_value;
    const date = next?.date ?? next?.forecastDate ?? next?.forecast_date;
    if (val != null) {
      return `下一筆預測：${date || '未來'} 預估價格 NT$ ${Number(val).toLocaleString('zh-TW', { maximumFractionDigits: 1 })}。共 ${pred.length} 筆預測資料可查閱。`;
    }
    return '有預測資料但數值為空，建議查看預測結果區塊。';
  }

  // How to use
  if (/怎麼用|功能|說明|help|使用/.test(input)) {
    return [
      '本系統提供以下功能：',
      '1. 儀表板總覽：KPI 指標、趨勢圖、地圖分佈',
      '2. 交易分析：價量走勢、季節性分析、市場比較',
      '3. 預測結果：AI 模型預測價格與產量',
      '4. 資料管理：同步、匯入、模型訓練',
      '5. 燈號預警：供給指數、價格跌幅、面積成長率',
      '',
      '您可以問我：「目前價格」、「走勢如何」、「燈號狀態」、「預測結果」等問題。',
    ].join('\n');
  }

  // Fallback
  return [
    '抱歉，我不太理解您的問題。您可以試著問我：',
    '・「目前價格多少？」',
    '・「最近走勢如何？」',
    '・「燈號狀態？」',
    '・「有什麼預測？」',
    '・「怎麼使用這個系統？」',
  ].join('\n');
}

/**
 * Return a list of quick-question suggestions.
 */
export function getQuickQuestions() {
  return [
    '目前價格多少？',
    '最近走勢如何？',
    '燈號狀態',
    '有什麼預測？',
    '功能說明',
  ];
}
