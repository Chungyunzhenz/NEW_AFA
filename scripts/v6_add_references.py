"""v5→v6: 補充 5 篇新文獻至參考文獻 + 在文獻回顧中引用"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
from docx import Document
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

RED = 'FF0000'
BLUE = '0000FF'  # 用藍色標記新找的文獻，與紅色(修改)區分
INPUT = '農糧署研究計畫書_v5_0330.docx'
OUTPUT = '農糧署研究計畫書_v6_0330.docx'

def mke(text, bold=False, color=RED):
    run = OxmlElement('w:r')
    rPr = OxmlElement('w:rPr')
    c = OxmlElement('w:color'); c.set(qn('w:val'), color); rPr.append(c)
    if bold:
        rPr.append(OxmlElement('w:b'))
    run.append(rPr)
    t = OxmlElement('w:t'); t.text = text; t.set(qn('xml:space'), 'preserve')
    run.append(t)
    return run

def sp(para, text, bold=False, color=RED):
    p_elem = para._element
    for ch in list(p_elem):
        if (ch.tag.split('}')[-1] if '}' in ch.tag else ch.tag) == 'r':
            p_elem.remove(ch)
    if text:
        p_elem.append(mke(text, bold, color))

def cp(para):
    sp(para, '')

def ip(ref, text, bold=False, color=RED):
    p = OxmlElement('w:p')
    if text:
        p.append(mke(text, bold, color))
    ref.addnext(p)
    return p

doc = Document(INPUT)
P = doc.paragraphs

# ============================================================
# 1. 在第二章文獻回顧中加入新文獻引用
# ============================================================
print("1. 更新第二章文獻回顧引用...")

# 找到 2.1 引言段落（介紹三種方法的那段）
# 目前 P[49] = "本節就本研究所採用之三種核心預測方法..."
# 在其前面加入一段綜述引用
for i, p in enumerate(P):
    if '本節就本研究所採用之三種核心預測方法' in p.text:
        sp(P[i],
           '農產品價格預測為農業經濟學與機器學習之重要交叉研究領域。'
           'Sun et al.（2023）之系統性文獻回顧指出，近年研究趨勢已從傳統統計方法轉向智慧預測方法，'
           '且多模型組合為未來發展方向。本節就本研究所採用之三種核心預測方法——'
           'XGBoost、Prophet 與 ANN——歸納其理論依據、技術特性與農業預測情境下之適用性。')
        print(f"   更新 P[{i}] 加入 Sun et al. (2023) 引用")
        break

# 找到 XGBoost 段落，加入 Zhao et al. (2025) 引用
for i, p in enumerate(P):
    if 'Chen 與 Guestrin（2016）提出之 XGBoost' in p.text:
        sp(P[i],
           'Chen 與 Guestrin（2016）提出之 XGBoost（eXtreme Gradient Boosting），'
           '透過正則化目標函數與高效之分裂演算法，建立數百棵決策樹逐步修正殘差，'
           '在各類預測競賽中取得優異成績。Zhao et al.（2025）以稻米、小麥與玉米之歷史價格資料驗證，'
           'TCN-XGBoost 混合模型可達 MAPE 5.3% 之預測精度，顯示 XGBoost 在農產品價格預測之有效性。'
           '其核心優勢在於特徵工程之靈活性——'
           '研究者可將滯後值、滾動統計量、日曆特徵、氣象變數等多種資訊納入模型，'
           '學習複雜的非線性交互效應，並透過特徵重要性排名提供高度可解釋之預測結果。')
        print(f"   更新 P[{i}] 加入 Zhao et al. (2025) 引用")
        break

# 找到 Prophet 段落，加入 Prathilothamai et al. (2025) 引用
for i, p in enumerate(P):
    if 'Taylor 與 Letham（2018）發表之 Prophet' in p.text:
        sp(P[i],
           'Taylor 與 Letham（2018）發表之 Prophet 模型，採用可加或可乘式分解架構，'
           '將時間序列拆解為趨勢、季節性、假日效應與外生回歸項等成分。'
           'Prophet 之設計哲學為「讓分析師更容易產出合理的預測」，'
           '其自動化之變化點偵測與彈性之季節性建模，特別適合處理具明顯年度週期性之農產品資料。'
           'Prathilothamai et al.（2025）以印度番茄市場為案例，驗證 Prophet 結合時間序列模型'
           '在蔬菜價格預測之適用性，顯示 Prophet 對季節性農產品價格之建模具有實務價值。')
        print(f"   更新 P[{i}] 加入 Prathilothamai et al. (2025) 引用")
        break

# 找到 ANN 段落，加入 Li et al. (2021) 和 Paul et al. (2022) 引用
for i, p in enumerate(P):
    if 'Rumelhart、Hinton 與 Williams（1986）' in p.text:
        sp(P[i],
           '人工神經網路（Artificial Neural Network）之理論基礎源於 Rumelhart、Hinton 與 Williams（1986）'
           '提出之反向傳播演算法，透過多層感知器（MLP）架構，'
           '可學習輸入特徵與目標變數之間的複雜非線性映射關係。'
           'Li et al.（2021）以中國蔬菜批發市場資料驗證，神經網路組合模型在蔬菜價格預測上'
           '優於單一模型；Paul et al.（2022）以印度茄子批發市場之逐日價格資料實證，'
           'GRNN 等神經網路方法在多數市場中之預測表現優於傳統 ARIMA 方法。'
           '本研究採用 Scikit-learn 套件（Pedregosa et al., 2011）提供之 MLPRegressor，'
           '其參數量適中，在約 170 個月度資料點之規模下較不易過擬合。')
        print(f"   更新 P[{i}] 加入 Li et al. (2021) & Paul et al. (2022) 引用")
        break

# ============================================================
# 2. 在參考文獻區加入 5 篇新文獻
# ============================================================
print("\n2. 新增 5 篇參考文獻...")

# 找到最後一篇參考文獻（Pedregosa）
last_ref_idx = None
for i in range(len(P)-1, 190, -1):
    if P[i].text.strip() and len(P[i].text) > 30:
        last_ref_idx = i
        break

if last_ref_idx:
    ref = P[last_ref_idx]._element

    # 加空行 + 備註標題
    p_note = ip(ref,
        '【以下為新補充之文獻，用以佐證三種預測模型在農產品／蔬菜價格預測之適用性】',
        bold=True, color=BLUE)

    # 1. Sun et al. (2023) - 綜述
    p1 = ip(p_note,
        'Sun, F., Meng, X., Zhang, Y., Wang, Y., Jiang, H., & Liu, P. (2023). '
        'Agricultural product price forecasting methods: A review. '
        'Agriculture, 13(9), 1671. '
        'https://doi.org/10.3390/agriculture13091671',
        color=BLUE)

    # 2. Paul et al. (2022) - ANN/ML 蔬菜價格
    p2 = ip(p1,
        'Paul, R. K., Yeasin, M., Kumar, P., Kumar, P., Balasubramanian, M., Roy, H. S., '
        'Paul, A. K., & Gupta, A. (2022). '
        'Machine learning techniques for forecasting agricultural prices: '
        'A case of brinjal in Odisha, India. '
        'PLOS ONE, 17(7), e0270553. '
        'https://doi.org/10.1371/journal.pone.0270553',
        color=BLUE)

    # 3. Zhao et al. (2025) - XGBoost 價格預測
    p3 = ip(p2,
        'Zhao, T., Chen, G., Suraphee, S., Phoophiwfa, T., & Busababodhin, P. (2025). '
        'A hybrid TCN-XGBoost model for agricultural product market price forecasting. '
        'PLOS ONE, 20(5), e0322496. '
        'https://doi.org/10.1371/journal.pone.0322496',
        color=BLUE)

    # 4. Li et al. (2021) - 神經網路蔬菜價格
    p4 = ip(p3,
        'Li, B., Ding, J., Yin, Z., Li, K., Zhao, X., & Zhang, L. (2021). '
        'Optimized neural network combined model based on the induced ordered weighted '
        'averaging operator for vegetable price forecasting. '
        'Expert Systems with Applications, 168, 114232. '
        'https://doi.org/10.1016/j.eswa.2020.114232',
        color=BLUE)

    # 5. Prathilothamai et al. (2025) - Prophet 蔬菜價格
    p5 = ip(p4,
        'Prathilothamai, M., Vinay, K., Vishnu Vardhan, K., Rama Vamsidhar Reddy, G., '
        '& Nithin, U. (2025). '
        'Enhancing agricultural price forecasting with time series models: '
        'A case study on tomato markets. '
        'In Lecture Notes in Networks and Systems (Vol. 1237). Springer. '
        'https://doi.org/10.1007/978-981-96-1185-0_16',
        color=BLUE)

    print("   5 篇新文獻已加入（藍色字體標記）")
else:
    print("   ERROR: 找不到參考文獻區")

# ============================================================
# Save
# ============================================================
print(f"\nSaving to {OUTPUT}...")
doc.save(OUTPUT)
print("Done!")
