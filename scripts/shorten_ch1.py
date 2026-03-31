"""精簡第一章 1.1–1.3"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
from docx import Document
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

RED = 'FF0000'

def make_run_element(text, bold=False, color=RED):
    run = OxmlElement('w:r')
    rPr = OxmlElement('w:rPr')
    c = OxmlElement('w:color')
    c.set(qn('w:val'), color)
    rPr.append(c)
    if bold:
        b = OxmlElement('w:b')
        rPr.append(b)
    run.append(rPr)
    t = OxmlElement('w:t')
    t.text = text
    t.set(qn('xml:space'), 'preserve')
    run.append(t)
    return run

def set_para_red(para, new_text, bold=False):
    p_elem = para._element
    for child in list(p_elem):
        tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
        if tag == 'r':
            p_elem.remove(child)
    if new_text:
        p_elem.append(make_run_element(new_text, bold=bold))

def clear_para(para):
    p_elem = para._element
    for child in list(p_elem):
        tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
        if tag == 'r':
            p_elem.remove(child)

INPUT = '農糧署研究計畫書_v4_0330.docx'
OUTPUT = '農糧署研究計畫書_v4_0330_v2.docx'

doc = Document(INPUT)
paras = doc.paragraphs

# ============================================================
# 1.1 精簡（段落 2–5）
# ============================================================

# [2] 保留核心數據，刪除冗長描述
set_para_red(paras[2],
    '甘藍（高麗菜）為臺灣產量最大之蔬菜，2023 年產量仍佔全部蔬菜品項之 17%，'
    '素有「菜王」之稱（焦鈞，2024）。然而，甘藍亦為「菜金菜土」問題最嚴重之品項——'
    '價格走揚時農民搶種，採收後供過於求致價格崩跌；'
    '颱風過後消費者搶購，價格又短期翻倍。'
    '此一循環年復一年，農民、消費者、政府與產銷通路四方均深受其害。'
)
print('[2] 精簡完成')

# [3] 合併四方影響＋政策侷限為一段
set_para_red(paras[3],
    '現行政策工具（如供苗預警、滾動倉儲、災害救助）多屬事後應對性質，缺乏「事前預知」能力。'
    '本計畫之核心目標，即透過 AI 預測系統補強此一關鍵缺口，'
    '使農糧署得以在產銷異常發生之前啟動政策工具、使農民於種植決策前掌握價格趨勢。'
)
print('[3] 精簡完成')

# [4] 清除（已合併至 [3]）
clear_para(paras[4])
print('[4] 已清除')

# [5] 清除（預期效益——使用者要求不寫預期結果）
clear_para(paras[5])
print('[5] 已清除（預期效益移除）')

# ============================================================
# 1.2 精簡（段落 8–11）
# ============================================================

# [8] 精簡結構性問題
set_para_red(paras[8],
    '甘藍之產銷失衡屬結構性問題。臺灣以小農經營為主，個別農民難以掌握全國種植總量與供需動態。'
    '甘藍種植技術門檻低、生長期僅約 70 天，冬季產量可較夏季增產 40%–60%，'
    '當種植面積擴大又逢良好天候，供給集中湧入市場，價格隨之急速下滑（報導者，2021）。'
)
print('[8] 精簡完成')

# [9] 只留核心發現
set_para_red(paras[9],
    'Su et al.（2025）之實證分析發現，颱風期間甘藍價格飆升之主因為消費者恐慌搶購之需求面衝擊，'
    '且政策介入之「時機」較「手段」更具決定性，顯示事前預測之重要性。'
)
print('[9] 精簡完成')

# [10] 精簡供苗預警機制
set_para_red(paras[10],
    '現行農糧署「大宗蔬菜供苗預警」機制由育苗場每旬回報出貨量，'
    '惟面臨回報數據低報、農民管道多元、預警公信力不足等困難（今周刊，2018；農傳媒，2021）。'
    '癥結在於「預測精準度」與「提前量」不足——'
    '唯有在農民做出種植決策之前提供可靠之價格趨勢預測，政策方具備實質引導空間。'
)
print('[10] 精簡完成')

# [11] 精簡其他蔬菜
set_para_red(paras[11],
    '上述困境在本計畫另外四種研究蔬菜中同樣存在：'
    '萵苣與小白菜生長週期更短，對氣候變化反應更即時；'
    '花椰菜淡季長達四個月，供需落差最顯著；'
    '青蔥颱風後價格暴漲幅度最劇（歷史紀錄曾達 5–10 倍）。'
    '五種蔬菜共享「資訊不對稱導致產銷失衡」之核心困境。'
)
print('[11] 精簡完成')

# ============================================================
# 1.3 精簡（段落 14–16, 22）
# ============================================================

# [14] 精簡概述
set_para_red(paras[14],
    '本計畫之預測模型建立於多源政府開放資料之整合基礎上，'
    '合計資料規模逾 1,310 萬筆，涵蓋 22 種作物、20 個批發市場及 22 個縣市。'
)
print('[14] 精簡完成')

# [15] 合併資料描述與整合困境
set_para_red(paras[15],
    '資料來源包括：農糧署批發市場交易行情（約 1,298 萬筆）、中央氣象署氣象觀測（約 11.9 萬筆）、'
    '農情產量統計（約 5,951 筆）及颱風資料庫（145 筆），詳見表 1-2。'
    '整合過程面臨更新頻率不一、格式標準不同、跨機關缺乏統一串接機制等困境，'
    '本計畫透過結構化資料庫與自動化 API 擷取管道加以解決。'
)
print('[15] 精簡完成')

# [16] 清除（已合併至 [15]）
clear_para(paras[16])
print('[16] 已清除')

# [22] 精簡表格分析結論
set_para_red(paras[22],
    '由表 1-1 可見，現有平臺普遍聚焦於歷史資料查詢或即時行情揭露，'
    '尚無任何平臺具備以機器學習進行蔬菜價格前瞻預測之能力，此即本計畫之核心定位。'
)
print('[22] 精簡完成')

doc.save(OUTPUT)
print(f'\n儲存完成：{OUTPUT}')
