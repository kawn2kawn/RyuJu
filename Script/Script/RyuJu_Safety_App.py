import streamlit as st
import pandas as pd
import datetime
import os
import uuid

# ==========================================
# 設定・定数定義
# ==========================================
st.set_page_config(
    page_title="労働安全論理分析ツール 龍樹(Safety)",
    layout="wide",
    initial_sidebar_state="expanded"
)

DATA_DIR = "data"
LOG_FILE = os.path.join(DATA_DIR, "safety_fact_log.csv")

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
    【安全分析版】
    - 人的要因（行動面・管理面）、物的要因（不備面・管理面）に特化
    - なぜなぜ分析の末端IDと対策を紐づける
    """
    prompt = f"""
# 労働安全・災害原因分析要請

あなたは労働安全衛生の熟練コンサルタントです。
提供された事実に基づき、不安全行動と不安全状態を特定し、論理的な「なぜなぜ分析」を行って対策を立案してください。

## 1. 発生事象と事実（現場からのインプット）
**【事実・現象詳細】**
{facts}

## 2. 分析指示

### Step 1: 不安全要因の分類（人的・物的）
入力された事実記述から、以下の4要素に関連する要素を**AIが抽出・整理**してください。
その上で、どのような経緯で労働災害（またはヒヤリハット）に至ったかのメカニズムを構築してください。

- **人的要因 A（作業行動面）:** 無理な姿勢、近道反応、保護具不使用、確認不足など
- **人的要因 B（作業管理面）:** 教育不足、指示ミス、不適切な人員配置、無理な工期など
- **物的要因 C（設備不備面）:** 防護カバー欠如、老朽化、スイッチ故障、通路の突起など
- **物的要因 D（設備管理面）:** 点検漏れ、修理放置、不適切なレイアウト、環境（暗さ・騒音）など

### Step 2: なぜなぜ分析（人的要因の深掘り）
「なぜその行動をとったか？」「なぜ管理が不十分だったか？」を深掘りします。
根本原因（真因）に到達するまで「なぜ？」を最低3回繰り返してください。

**【重要指示：ID付与】**
- 分析はツリー構造で行ってください。
- **全ての末端の要因（根本原因）には、必ず一意のID（例: 人-1, 人-2...）を付与してください。**

### Step 3: なぜなぜ分析（物的要因の深掘り）
「なぜ設備に不備があったか？」「なぜ管理で見抜けなかったか？」を分析してください。

**【重要指示：ID付与】**
- **全ての末端の要因（根本原因）には、必ず一意のID（例: 物-1, 物-2...）を付与してください。**

### Step 4: 対策提案（紐づけ必須）
特定された真因に対し、以下の4つのカテゴリーで対策を提案してください。
**【最重要】各対策が、どのID（根本原因）に対する処置なのかを必ず明記してください。**

#### 出力フォーマット:
**【①人的要因：作業行動面への対策】** (対象ID: 人-X)
**【②人的要因：作業管理面への対策】** (対象ID: 人-X)
**【③物的要因：設備不備面への対策】** (対象ID: 物-X)
**【④物的要因：設備管理面への対策】** (対象ID: 物-X)

※各対策は「暫定対策（即処置）」と「恒久対策（仕組みの改善）」に分けて記述してください。

出力はMarkdown形式で見やすく整形してください。
"""
    return prompt

# ==========================================
# メイン処理 (UI構築)
# ==========================================
def main():
    # --- CSS注入（フォントサイズ調整） ---
    st.markdown("""
    <style>
        html { font-size: 110%; }
        .stTextInput input, .stTextArea textarea, .stDateInput input { font-size: 18px !important; }
        .stTextInput label, .stTextArea label, .stDateInput label { font-size: 20px !important; font-weight: bold; }
        .stButton button { font-size: 20px !important; }
    </style>
    """, unsafe_allow_html=True)

    # サイドバー：入力インターフェース
    with st.sidebar:
        st.title("🔍 労働安全情報入力")
        
        st.subheader("【発生状況】")
        input_what = st.text_input("何を（災害の種類）", placeholder="例：フォークリフトとの接触、転倒、挟まれ")
        input_how = st.text_input("どうした（事象）", placeholder="例：旋回中のフォークに足が接触した")
        
        st.write("---")
        
        st.subheader("【調査事実】")
        input_date = st.date_input("いつ（日付）", datetime.date.today())
        input_when_detail = st.text_input("いつ（詳細時刻）", placeholder="例：午前10時、残業時間帯")
        input_where = st.text_input("どこで", placeholder="例：出荷バース、第2倉庫")
        input_who = st.text_input("誰が", placeholder="例：作業者（Aさん）、入社3ヶ月")
        
        st.write("---")
        st.header("💡 安全分析のヒント")
        st.info("不安全な「行動」だけでなく、それを許した「環境や管理」の事実を詳しく書いてください。")

    # メイン画面
    col_title, col_logo = st.columns([5, 1])
    with col_title:
        st.title("🔍 労働安全論理分析支援ツール「龍樹 - Safety」")

    with col_logo:
        if os.path.exists("header_logo.png"):
            st.image("header_logo.png", use_container_width=True)
    
    st.markdown("#### サイドバーの基本情報に加え、以下の欄に詳細な事実や気づきを入力してください。\n**客先や個人が特定されるような固有名詞は絶対に入力しないでください**")

    # 安全版プレースホルダー
    placeholder_text = """例：
・コンベアの詰まりを直そうとして、機械を止めずに手を入れた。
・コンベアの安全カバーが外されていたが、作業効率のためにそのままにしていた。
・作業者は「いつもやっている方法で、大丈夫だと思った」と話している。
・当日、ラインの速度が通常より1.2倍速く設定されており、作業者は焦っていた。
・安全センサーは故障していたが、修理依頼が出されたまま1ヶ月放置されていた。
・新人で、その工程の作業手順教育は受けていたが、異常時の対応教育は受けていなかった。"""

    st.markdown("### 詳細な事実・調査結果（三現主義で多くの事実を収集し記述してください/人的・物的要因を意識すると精度が上がります）")
    
    extra_facts = st.text_area(
        label="詳細な事実・調査結果",
        label_visibility="collapsed",
        height=450,
        placeholder=placeholder_text,
    )

    if st.button("安全分析プロンプトを生成する", type="primary"):
        combined_facts = f"""
【事象の概要】
・種類: {input_what}
・事象: {input_how}

【調査による事実】
・発生日: {input_date}
・詳細時間: {input_when_detail}
・場所: {input_where}
・担当者情報: {input_who}

【詳細な事実・調査結果・要因に関する気づき】
{extra_facts}
"""
        
        if not input_what or not input_how:
            st.warning("⚠️ サイドバーの項目は必須入力項目です。")
        else:
            if save_to_csv(combined_facts):
                st.success("✅ 安全ログを記録しました。")
            
            generated_text = generate_prompt_template(combined_facts)
            
            st.markdown("---")
            st.subheader("🤖 AIへの指令書（安全分析・ツリー構造版）")
            st.info("右上のコピーボタンを押して、ChatGPTやGemini等に貼り付けてください。")
            
            st.code(generated_text, language="markdown")
            
            st.markdown("""
            **安全版プロンプトの特徴:**
            1. **人的・物的要因の分離:** 行動、管理、設備不備、設備管理の4軸で真因を追究させます。
            2. **不安全状態の抽出:** 個人の過失に留めず、背後にある設備や管理の欠陥をAIに探らせます。
            3. **ツリー構造 & ID紐付け:** 複雑な要因を整理し、対策と原因を確実に1対1で対応させます。
            """)

if __name__ == "__main__":
    main()
