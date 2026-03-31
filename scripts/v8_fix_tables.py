"""修復 4.1 工作項目 + 4.3 KPI 表格"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
from docx import Document
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

RED = 'FF0000'

def mke(text, bold=False, color=RED):
    run = OxmlElement('w:r')
    rPr = OxmlElement('w:rPr')
    c = OxmlElement('w:color'); c.set(qn('w:val'), color); rPr.append(c)
    if bold: rPr.append(OxmlElement('w:b'))
    run.append(rPr)
    t = OxmlElement('w:t'); t.text = text; t.set(qn('xml:space'), 'preserve')
    run.append(t)
    return run

def it(ref, headers, rows):
    tbl = OxmlElement('w:tbl')
    tblPr = OxmlElement('w:tblPr')
    ts = OxmlElement('w:tblStyle'); ts.set(qn('w:val'), 'TableGrid'); tblPr.append(ts)
    tw = OxmlElement('w:tblW'); tw.set(qn('w:w'), '0'); tw.set(qn('w:type'), 'auto'); tblPr.append(tw)
    borders = OxmlElement('w:tblBorders')
    for bn in ['top','left','bottom','right','insideH','insideV']:
        b = OxmlElement(f'w:{bn}')
        b.set(qn('w:val'),'single'); b.set(qn('w:sz'),'4'); b.set(qn('w:space'),'0'); b.set(qn('w:color'),'000000')
        borders.append(b)
    tblPr.append(borders); tbl.append(tblPr)
    g = OxmlElement('w:tblGrid')
    for _ in headers: g.append(OxmlElement('w:gridCol'))
    tbl.append(g)
    def mc(t, hd=False):
        tc = OxmlElement('w:tc'); p = OxmlElement('w:p'); p.append(mke(str(t), hd)); tc.append(p); return tc
    tr = OxmlElement('w:tr')
    for h in headers: tr.append(mc(h, True))
    tbl.append(tr)
    for rd in rows:
        tr = OxmlElement('w:tr')
        for ct in rd: tr.append(mc(ct))
        tbl.append(tr)
    ref.addnext(tbl)
    return tbl

doc = Document('農糧署研究計畫書_v8_0330.docx')
P = doc.paragraphs

# 4.1 工作項目表格
for i, p in enumerate(P):
    if '主要工作項目如下' in p.text:
        it(p._element,
            ['工作項目', '內容說明', '交付物'],
            [['W1：多源資料整合',
              '整合農糧署交易行情、氣象觀測、農情產量、颱風歷史等四大資料源，建立自動化 ETL 管道',
              'SQLite 資料庫、資料品質報告'],
             ['W2：特徵工程設計',
              '設計 20+ 維特徵矩陣，含歷史價格、滾動統計、日曆、氣象、颱風等五大類',
              '特徵工程模組、特徵說明文件'],
             ['W3：三模型訓練與評估',
              '分別實作 Prophet、XGBoost、ANN 三種模型，評估五種蔬菜之預測表現並比較分析',
              '模型程式碼、績效比較報告'],
             ['W4：決策支援平臺開發',
              '開發 Web 應用系統，含互動式儀表板、地圖視覺化、颱風模擬、預警燈號',
              '前後端程式碼、API 文件'],
             ['W5：系統測試與結案報告',
              '系統功能測試、結案報告撰寫',
              '測試報告、結案報告']])
        print(f'4.1 工作項目表格已插入')
        break

# 4.3 KPI 表格
for i, p in enumerate(P):
    if '關鍵績效指標如下' in p.text:
        it(p._element,
            ['KPI', '目標', '量測方式'],
            [['預測精度', '三種模型均達合理預測水準', '以 MAPE、R² 等指標評估五種蔬菜之預測表現'],
             ['模型比較', '完成三模型之系統性比較分析', '各模型在不同作物之表現差異報告'],
             ['資料整合', '完成多源資料之串接與入庫', '結構化資料庫建置完成並可正常查詢'],
             ['系統開發', '完成決策支援平臺之開發與展示', '前後端系統可正常運行並展示預測結果']])
        print(f'4.3 KPI 表格已插入')
        break

doc.save('農糧署研究計畫書_v8_final.docx')
print('儲存完成：農糧署研究計畫書_v8_final.docx')
