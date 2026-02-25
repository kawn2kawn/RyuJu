import streamlit as st
import pandas as pd
import datetime
import os
import uuid

# ==========================================
# 設定・定数定義
# ==========================================
st.set_page_config(
    page_title="品質不具合論理分析ツール 龍樹(Quality)",
    layout="wide",
    initial_sidebar_state="expanded"
)

DATA_DIR = "data"
LOG_FILE = os.path.join(DATA_DIR, "quality_fact_log.csv")

# ==========================================
# 関数定義
# ==========================================

def ensure_data_dir():
    if not os.path.exists(DATA_DIR):
        try:
            os.makedirs(DATA_DIR)
        except Exception as e:
            st.error(f"【システムエラー】フォルダ作成に失敗しました: {e}")

def save_to_csv(fact_text):
    """
    入力された事実をCSVに保存する。
    """
    ensure_data_dir()
    now = datetime.datetime.now()
    case_id = str(uuid.uuid4())[:8]
    
    new_data = {
        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
        "case_id": case_id,
        "raw_facts": fact_text
    }
    
    df = pd.DataFrame([new_data])
    
    try:
        if not os.path.exists(LOG_FILE):
            df.to_csv(LOG_FILE, index=False, encoding="utf-8-sig")
        else:
            df.to_csv(LOG_FILE, mode='a', header=False, index=False, encoding="utf-8-sig")
        return True
    except Exception as e:
        st.error(f"【ログ保存エラー】CSVへの書き込みに失敗しました: {e}")
        return False

def generate_prompt_template(facts):
    """
    【修正版】
    - 発生/流出を明確に分離
    - なぜなぜ分析の末端IDと対策を紐づける指示を追加
    """
    prompt = f"""
# 不具合原因分析要請

あなたは製造業における熟練の品質保証エンジニアです。
提供された事実に基づき、事実と推測を分け、論理的な「なぜなぜ分析」を行って対策を立案してください。

## 1. 発生事象と事実（現場からのインプット）
**【事実・現象詳細】**
{facts}

## 2. 分析指示

### Step 1: 事実の4M整理とメカニズム推定
入力された事実記述から、以下の4M（Man, Machine, Material, Method）に関連する要素を**AIが抽出・整理**してください。
その上で、物理的・事象的にどのようなメカニズムで不具合が発生したか、論理的なシナリオ（帰納的推論）を構築してください。

### Step 2: なぜなぜ分析（発生要因）
不具合が「発生したメカニズム」について深掘りします。
根本原因（真因）に到達するまで「なぜ？」を最低でも3回繰り返してください（最大5回）。

**【重要指示：ID付与】**
- 分析はツリー構造で行ってください。
- **全ての末端の要因（根本原因）には、必ず一意のID（例: 発-1, 発-2...）を付与してください。**
- 後のStep 4で、このIDを使って対策と紐づけます。

*出力イメージ:*
- なぜ1: 〇〇だったから
  - なぜ2-1: ▲▲だったから
     - なぜ3-1: ◇◇だったから **(ID: 発-1)**

### Step 3: なぜなぜ分析（流出要因）
「なぜ工程内で発見・除去できずに後工程（または客先）へ流れたか？」を分析してください。

**【重要指示：ID付与】**
- **全ての末端の要因（根本原因）には、必ず一意のID（例: 流-1, 流-2...）を付与してください。**

*出力イメージ:*
- なぜ1: 検査で見逃したから
  - なぜ2-1: 基準が曖昧だったから
     - なぜ3-1: 限度見本が古かったから **(ID: 流-1)**

### Step 4: 対策提案（紐づけ必須）
特定された真因に対し、**「発生対策」と「流出対策」を明確に分けて**提案してください。
**【最重要】各対策が、Step 2/3のどのID（根本原因）に対する処置なのかを必ず明記してください。**

#### 出力フォーマット:
**【A. 発生対策】**
1. **対策内容**: (ここに具体的な対策を記述)
   - **対象ID**: (例: 発-1)
   - **区分**: 恒久対策 / 暫定対策

**【B. 流出対策】**
1. **対策内容**: (ここに具体的な対策を記述)
   - **対象ID**: (例: 流-1)
   - **区分**: 恒久対策 / 暫定対策

出力はMarkdown形式で見やすく整形してください。
"""
    return prompt

# ==========================================
# メイン処理 (UI構築)
# ==========================================
def main():
    # サイドバー：入力インターフェース
    with st.sidebar:
        st.title("🔍 品質不具合情報入力")
        
        st.subheader("【客先情報でわかる事実】")
        input_what = st.text_input("何を", placeholder="例：A00-00000 〇〇〇〇、1A11")
        input_how = st.text_input("どうした", placeholder="例：〇〇〇〇が欠品していた")
        
        st.write("---")
        
        st.subheader("【客先情報から調査で分かる事実】")
        input_date = st.date_input("いつ（日付）", datetime.date.today())
        input_when_detail = st.text_input("いつ（詳細時刻・時間帯）", placeholder="例：夜勤帯、15時ごろ")
        input_where = st.text_input("どこで", placeholder="例：第1加工工程、検査ライン")
        input_who = st.text_input("誰が", placeholder="例：イニシャル（T.K）、新人作業者")
        
        st.write("---")
        st.header("💡 入力ヒント")
        st.info("事実を出来るだけ多く入力するだけで、AIが4Mに分類し、ツリー構造で深掘り分析を行います。")

    # メイン画面
    # ---------------------------------------------------------
    # 画像（ロゴ）を右上に配置するためのレイアウト変更
    # ---------------------------------------------------------
    col_title, col_logo = st.columns([5, 1]) # 左:タイトル(広め) / 右:ロゴ(狭め)

    with col_title:
        st.title("🔍 品質不具合対策論理分析支援ツール「龍樹 - Quality」")

    with col_logo:
        # 画像ファイルが存在する場合のみ表示（エラー回避）
        if os.path.exists("header_logo.png"):
            # use_container_width=True でカラムの幅に合わせて表示
            st.image("header_logo.png", use_container_width=True)
    
    # ↓↓↓ 【修正部分】ここを #### で見出し化し、大きく表示するように変更 ↓↓↓
    st.markdown("#### サイドバーの基本情報に加え、以下の欄に詳細な事実や気づきを入力してください。\n**客先や個人が特定されるような固有名詞は絶対に入力しないでください**")

    # プレースホルダー用の例文
    placeholder_text = """例：
・3R03Aロットの10個全てで異品を梱包していた。
・顧客へ5個の異品が流出した。(4/1_3個、4/11_2個)
・E16-13490-01（10個）とE16-18490-01（16個）の2品番が1日違いで計画されていた。
　3/3 ：E16-13490-01 　　 3/4 ：E16-18490-01
・指示日は違うが、2種類の部品がラインサイドに払出されていた。
・指図書のバーコードを読み取り、タブレットに製品画像を表示している。
　日産向けではタブレットによる製品表示はしていない（今回の異品）
・品質留意点として【類似品があるため混同なきこと】とあるが、具体的な表記ではなかった。
・作業者聞き取りから、日常的に部品の過不足が起きているので員数管理はしていた。
・10個の生産計画に対し異品の16個を使用したが、部品の過不足が日頃から散発しており
　部品が余ったが、異常と思わなかった。
・チェックシートに使用部品の使用数に対して不足があった時には、数量を記録するようになっているが記録されていなかった。"""

    # 自由記述エリア
    # ラベル文字を大きくするためにst.markdownでヘッダーとして表示し、
    # text_area自体のラベルは非表示(collapsed)にする手法をとります
    st.markdown("### 詳細な事実・調査結果（三現主義で多くの事実を収集し記述してください/4Mの観点で記述すると精度が上がります）")
    
    extra_facts = st.text_area(
        label="詳細な事実・調査結果", # 内部的なラベル（表示はされない）
        label_visibility="collapsed", # ラベルのスペースを隠す
        height=450,
        placeholder=placeholder_text,
        help="箇条書きでOKです。AIがここから4M要素を自動抽出します。"
    )

    if st.button("論理分析プロンプトを生成する", type="primary"):
        combined_facts = f"""
【客先情報での事実】
・対象: {input_what}
・事象: {input_how}

【調査による事実】
・発生日: {input_date}
・詳細時間: {input_when_detail}
・場所: {input_where}
・担当: {input_who}

【詳細な事実・調査結果・4Mに関する気づき】
{extra_facts}
"""
        
        if not input_what or not input_how:
            st.warning("⚠️ サイドバーの「何を」「どうした」は必須入力項目です。")
        else:
            if save_to_csv(combined_facts):
                st.success("✅ 品質ログを記録しました。")
            
            generated_text = generate_prompt_template(combined_facts)
            
            st.markdown("---")
            st.subheader("🤖 AIへの指令書（ツリー構造分析版）")
            st.info("右上のコピーボタンを押して、ChatGPTやGemini等に貼り付けてください。")
            
            # ワンクリックでコピー可能なコードブロック
            st.code(generated_text, language="markdown")
            
            st.markdown("""
            **このプロンプトの5つの特徴:**
            1. **4M自動抽出:** 乱雑なメモから、人・設備・材料・方法の要素をAIが自動で整理します。
            2. **メカニズム推定:** いきなり分析せず、まずは「何が起きたか」のシナリオを物理的に組み立てます。
            3. **ツリー構造 & ID付与:** 原因を一本道にせず分岐させ、末端にID（発-1等）を振って管理します。
            4. **深掘りの適正化:** 「なぜ」を最低3回繰り返させ、浅い分析で終わらせません。
            5. **対策の紐づけ & 区分:** どの原因(ID)への対策かを明記し、「暫定」と「恒久」を厳密に分けます。
            """)

if __name__ == "__main__":
    main()
