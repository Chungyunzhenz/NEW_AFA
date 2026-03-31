"""在蔬菜資料盤點表格後，新增其他資料來源盤點表格"""
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

def insert_para_after(ref_elem, text, bold=False):
    new_p = OxmlElement('w:p')
    if text:
        new_p.append(make_run_element(text, bold=bold))
    ref_elem.addnext(new_p)
    return new_p

def insert_table_after(ref_elem, headers, rows):
    tbl = OxmlElement('w:tbl')
    tblPr = OxmlElement('w:tblPr')
    tblStyle = OxmlElement('w:tblStyle')
    tblStyle.set(qn('w:val'), 'TableGrid')
    tblPr.append(tblStyle)
    tblW = OxmlElement('w:tblW')
    tblW.set(qn('w:w'), '0')
    tblW.set(qn('w:type'), 'auto')
    tblPr.append(tblW)
    tblBorders = OxmlElement('w:tblBorders')
    for border_name in ['top', 'left', 'bottom', 'right', 'insideH', 'insideV']:
        border = OxmlElement(f'w:{border_name}')
        border.set(qn('w:val'), 'single')
        border.set(qn('w:sz'), '4')
        border.set(qn('w:space'), '0')
        border.set(qn('w:color'), '000000')
        tblBorders.append(border)
    tblPr.append(tblBorders)
    tbl.append(tblPr)
    tblGrid = OxmlElement('w:tblGrid')
    for _ in headers:
        tblGrid.append(OxmlElement('w:gridCol'))
    tbl.append(tblGrid)

    def make_cell(text, is_header=False):
        tc = OxmlElement('w:tc')
        p = OxmlElement('w:p')
        p.append(make_run_element(str(text), bold=is_header))
        tc.append(p)
        return tc

    tr = OxmlElement('w:tr')
    for h in headers:
        tr.append(make_cell(h, is_header=True))
    tbl.append(tr)
    for row_data in rows:
        tr = OxmlElement('w:tr')
        for cell_text in row_data:
            tr.append(make_cell(cell_text))
        tbl.append(tr)
    ref_elem.addnext(tbl)
    return tbl


INPUT = '農糧署研究計畫書_v4_0330_v2.docx'
OUTPUT = '農糧署研究計畫書_v4_0330_v3.docx'

doc = Document(INPUT)
paras = doc.paragraphs

# Find paragraph [36] - the shared data paragraph
target_idx = None
for i, p in enumerate(paras):
    if '共享之輔助資料' in p.text:
        target_idx = i
        break

if target_idx is None:
    print("ERROR: 找不到目標段落")
    sys.exit(1)

print(f"找到目標段落 [{target_idx}]: {paras[target_idx].text[:60]}...")

# Replace the text paragraph with a title + table
set_para_red(paras[target_idx],
    "此外，五種蔬菜共享以下輔助資料來源：")

# Insert table after the paragraph
tbl = insert_table_after(paras[target_idx]._element,
    headers=["資料類別", "資料筆數", "時間範圍", "主要欄位", "資料完整性"],
    rows=[
        ["氣象觀測資料\n（中央氣象署 CWA）",
         "119,080",
         "2005–2026",
         "觀測日期、縣市、平均溫度、最高溫、最低溫、降雨量(mm)、濕度(%)",
         "完整，涵蓋 22 縣市"],
        ["颱風歷史事件\n（中央氣象署颱風資料庫）",
         "145",
         "2000–2025",
         "颱風名稱、年份、警報起迄日、強度等級（輕度/中度/強烈）、侵臺路徑、最大風速、最低氣壓",
         "完整，無斷層"],
        ["農情產量統計\n（農業部農糧署）",
         "5,951",
         "2008–2024",
         "年份、縣市、種植面積(公頃)、收穫面積(公頃)、產量(公噸)、每公頃產量",
         "完整，年度資料"],
        ["批發市場主檔",
         "20",
         "—",
         "市場代碼、市場名稱、所在縣市",
         "靜態主檔"],
        ["縣市主檔",
         "22",
         "—",
         "縣市代碼、縣市名稱",
         "靜態主檔"],
    ]
)

# Add caption after table
p_cap = insert_para_after(tbl, "資料來源：本研究整理（2026）")

# Add summary sentence
p_sum = insert_para_after(p_cap,
    "五種蔬菜涵蓋葉菜（甘藍、萵苣、小白菜）、花菜（花椰菜）及辛香料（青蔥）三種食用類型，"
    "搭配上述氣象、颱風與產量資料，可全面驗證模型之跨品類適用性。"
)

print("已新增輔助資料盤點表格")

doc.save(OUTPUT)
print(f"儲存完成：{OUTPUT}")
