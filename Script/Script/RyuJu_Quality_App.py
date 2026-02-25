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

# 現場でのデータ管理用フォルダとファイル名
DATA_DIR = "data"
LOG_FILE = os.path.join(DATA_DIR, "quality_fact_log.csv")

# ==========================================
# 関数定義
# ==========================================

def ensure_data_dir():
    """
    データ保存用のフォルダが存在するか確認し、なければ作成する。
    現場のPC環境で権限エラー等が発生した場合に備え、例外処理を入れる。
    """
    if not os.path.exists(DATA_DIR):
        try:
            os.makedirs(DATA_DIR)
        except Exception as e:
            st.error(f"【システムエラー】フォルダ作成に失敗しました: {e}")

def save_to_csv(fact_text):
    """
    入力された事実をCSVに保存する。
    将来の統計分析（AI活用）を見据え、タイムスタンプと一意のIDを付与する。
    """
    ensure_data_dir()
    now = datetime.datetime.now()
    case_id = str(uuid.uuid4())[:8]  # 追跡用の簡易ID
    
    new_data = {
        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
        "case_id": case_id,
        "raw_facts": fact_text
    }
    
    df = pd.DataFrame([new_data])
    
    try:
        if not os.path.exists(LOG_FILE):
            # 新規作成時はヘッダーあり。Excelでの文字化け防止のためutf-8-sigを採用。
            df.to_csv(LOG_FILE, index=False, encoding="utf-8-sig")
        else:
            # 2回目以降は追記（append）モード。
            df.to_csv(LOG_FILE, mode='a', header=False, index=False, encoding="utf-8-sig")
        return True
    except Exception as e:
        st.error(f"【ログ保存エラー】CSVへの書き込みに失敗しました。ファイルが開かれていないか確認してください: {e}")
        return False

def generate_prompt_template(facts):
    """
    現場の事実に基づき、AI（ChatGPT/Gemini等）へ渡すための最強の分析指示書を作成する。
    発生と流出を分離し、IDによる紐づけを強制する。
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

    # メイン画面のレイアウト
    col_title, col_logo = st.columns([5, 1])

    with col_title:
        st.title("🔍 品質不具合対策論理分析支援ツール「龍樹 - Quality」")

    with col_logo:
        # ロゴ画像があれば表示。ファイル名の間違いや欠落で止まらないようチェック。
        if os.path.exists("header_logo.png"):
            st.image("header_logo.png", use_container_width=True)
    
    st.markdown("#### サイドバーの基本情報に加え、以下の欄に詳細な事実や気づきを入力してください。\n**客先や個人が特定されるような固有名詞は絶対に入力しないでください**")

    # プレースホルダー用の例文（三現主義に基づいた具体例）
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

    st.markdown("### 詳細な事実・調査結果（三現主義で多くの事実を収集し記述してください/4Mの観点で記述すると精度が上がります）")
    
    extra_facts = st.text_area(
        label="詳細な事実・調査結果",
        label_visibility="collapsed",
        height=450,
        placeholder=placeholder_text,
        help="箇条書きでOKです。AIがここから4M要素を自動抽出します。"
    )

    if st.button("論理分析プロンプトを生成する", type="primary"):
        # 入力データを構造化してまとめる
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
            # CSVに保存を実行
            if save_to_csv(combined_facts):
                st.success("✅ 品質ログを記録しました。")
            
            # AIへの指令書を作成
            generated_text = generate_prompt_template(combined_facts)
            
            st.markdown("---")
            st.subheader("🤖 AIへの指令書（ツリー構造分析版）")
            
            # 修正ポイント：コピーボタン付きのst.codeを廃止し、確実に全選択できるエリアを作成
            st.info("下のテキストエリア内を全選択（Ctrl+A）してコピーしてください。")
            
            # テキストエリアによる出力（コピーボタンなし・確実な全選択用）
            st.text_area(
                label="プロンプト出力エリア",
                value=generated_text,
                height=500,
                label_visibility="collapsed"
            )
            
            st.markdown("""
            **このプロンプトの5つの特徴:**
            1. **4M自動抽出:** 乱雑なメモから要素をAIが自動整理。
            2. **メカニズム推定:** 物理的な不具合シナリオを構築。
            3. **ツリー構造 & ID付与:** 原因の分岐を明確化し、IDで管理。
            4. **深掘りの適正化:** 「なぜ」を繰り返させ、真因を追及。
            5. **対策の紐づけ & 区分:** IDを用いた確実な対策立案と、暫定/恒久の峻別。
            """)

if __name__ == "__main__":
    main()
