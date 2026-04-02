#!/usr/bin/env python3
"""Restructure the proposal document: reorder sections without changing content."""
import sys
sys.stdout.reconfigure(encoding='utf-8')
from docx import Document
from docx.oxml.ns import qn

doc = Document('農糧署研究計畫書_v8_0330.docx')
body = doc.element.body

# Save all elements (body[0]~body[149])
all_elements = list(body)
sect_pr = all_elements[-1]       # sectPr (page/section settings)
content = all_elements[:-1]      # body[0]~body[148]

# Remove all from body
for elem in all_elements:
    body.remove(elem)

# Helper
def elems(start, end):
    return content[start:end]

# ========== Build new element order ==========
new_order = []

# --- 第一章　研究背景、動機、目的與問題 ---
new_order += elems(0, 5)        # Ch1 heading[0] + 1.1[1-4]
new_order += elems(5, 9)        # 1.2 計畫亮點[5-8]
new_order += elems(73, 82)      # orig 3.1 → 1.3 待解決的問題[73-81]
new_order += elems(82, 86)      # orig 3.2 → 1.4 研究目的[82-85]
new_order += elems(86, 101)     # orig 3.3 → 1.5 研究問題[86-100]
new_order += elems(101, 106)    # orig 3.4 → 1.6 研究範圍與限制[101-105]

# --- 第二章　相關文獻回顧 ---
new_order += elems(43, 44)      # Ch2 heading[43]
new_order += elems(60, 64)      # orig 2.2 → 2.1 氣象因子[60-63]
new_order += elems(44, 60)      # orig 2.1 → 2.2 預測方法論[44-59]
new_order += elems(64, 67)      # 2.3 農業決策支援系統[64-66]
new_order += elems(67, 72)      # 2.4 研究缺口[67-71]
new_order += elems(18, 43)      # orig 1.4 → 2.5 學術定位[18-42]

# --- 第三章　機器學習與決策支援架構 ---
new_order += elems(72, 73)      # Ch3 heading[72]
new_order += elems(9, 18)       # orig 1.3 → 3.1 開放資料來源[9-17]

# --- 第四章　工作內容重點 (不動) ---
new_order += elems(106, 123)    # Ch4 heading + all subsections[106-122]

# --- 參考文獻 (不動) ---
new_order += elems(123, 149)    # References[123-148]

# Verify count
assert len(new_order) == len(content), \
    f"Element count mismatch: {len(new_order)} vs {len(content)}"

# Reattach in new order
for elem in new_order:
    body.append(elem)
body.append(sect_pr)

# ========== Update heading numbers only ==========
def set_heading_text(elem, new_text):
    """Replace all text in a paragraph element."""
    runs = elem.findall(qn('w:r'))
    if not runs:
        return
    t_elems = runs[0].findall(qn('w:t'))
    if t_elems:
        t_elems[0].text = new_text
        t_elems[0].set(qn('xml:space'), 'preserve')
    for run in runs[1:]:
        for t in run.findall(qn('w:t')):
            t.text = ''

# Map: original body index → new heading text
heading_updates = {
    # Chapter titles
    0:   '第一章　研究背景、動機、目的與問題',
    43:  '第二章　相關文獻回顧',
    72:  '第三章　機器學習與決策支援架構',
    # Ch1 section renumbering (orig Ch3 → Ch1)
    73:  '1.3　待解決的問題與服務對象',
    74:  '1.3.1　核心問題',
    82:  '1.4　研究目的',
    86:  '1.5　研究問題',
    101: '1.6　研究範圍與限制',
    # Ch2 section renumbering
    60:  '2.1　氣象因子與農產品價格關聯研究',
    44:  '2.2　農產品價格預測方法論基礎',
    46:  '2.2.1　梯度提升樹方法（XGBoost）',
    49:  '2.2.2　可分解式預測模型（Prophet）',
    52:  '2.2.3　人工神經網路（ANN）',
    55:  '2.2.4　三種預測方法綜合比較',
    18:  '2.5　學術定位',
    # Ch3 section renumbering (orig 1.3 → 3.1)
    9:   '3.1　開放資料來源',
}

for body_idx, new_text in heading_updates.items():
    set_heading_text(content[body_idx], new_text)

# Save
output = '農糧署研究計畫書_v9_0331.docx'
doc.save(output)
print(f'Done! Saved as {output}')

# Verify new structure
print('\n=== New Structure ===')
from docx import Document as D2
doc2 = D2(output)
for para in doc2.paragraphs:
    if para.style.name.startswith('Heading'):
        indent = '  ' * (int(para.style.name.replace('Heading', '').strip()) - 1)
        print(f'{indent}{para.text}')
