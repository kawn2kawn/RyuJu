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

def save_to_csv(fact_text, machine_type):
    ensure_data_dir()
    now = datetime.datetime.now()
    case_id = str(uuid.uuid4())[:8]
    
    new_data = {
        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
        "case_id": case_id,
        "machine_type": machine_type,
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

def generate_prompt_template(facts, machine_type):
    """
    【融合版】
    入力はシンプルだが、出力指示（プロンプト）は
    「帰納的推論」と「ツリー構造のなぜなぜ分析」を行う強力なバージョン。
    """
    prompt = f"""
# 不具合原因分析要請

あなたは製造業における熟練の品質保証エンジニアです。
提供された事実に基づき、事実と推測を分け、論理的な「なぜなぜ分析」を行って対策を立案してください。

## 1. 発生事象と事実（現場からのインプット）
**【対象ライン・設備】** {machine_type}
**【事実・現象詳細】**
{facts}

## 2. 分析指示

### Step 1: 事実の4M整理とメカニズム推定
入力された事実記述から、以下の4M（Man, Machine, Material, Method）に関連する要素を**AIが抽出・整理**してください。
その上で、物理的・事象的にどのようなメカニズムで不具合が発生したか、論理的なシナリオ（帰納的推論）を構築してください。

- **Man (人):** 担当者、経験、作業行動など
- **Machine (設備):** 機械、治具、金型、メンテナンス状況など
- **Material (材料):** ワーク、部品、ロット変化など
- **Method (方法):** 作業手順、標準書、条件設定など

### Step 2: なぜなぜ分析（発生要因） - ツリー構造解析
根本原因（真因）に到達するまで「なぜ？」を最低でも3回繰り返してください（最大5回）。
**重要な指示:** 原因は一つとは限りません。要因が複数考えられる場合は、一本道ではなく**「分岐（ツリー構造）」**させて分析してください。

*出力形式イメージ:*
- なぜ1: 〇〇だったから
  - なぜ2-1: ▲▲だったから... -> なぜ3-1 ...
  - なぜ2-2: ◇◇だったから... -> なぜ3-2 ...

### Step 3: なぜなぜ分析（流出要因）
「なぜ工程内で発見・除去できずに後工程（または客先）へ流れたか？」を分析してください。
ここでも要因が複数ある場合は**「分岐（ツリー構造）」**させてください。

### Step 4: 対策提案
特定された真因（分岐した末端の原因すべて）に対し、以下の対策を提示してください。
- **暫定対策**: 直ちに実行すべき処置
- **恒久対策**: 再発を根本から防ぐ仕組み（ルール順守だけに頼らない、物理的対策やポカヨケ・ハード対策を優先）

出力はMarkdown形式で見やすく整形してください。
"""
    return prompt

# ==========================================
# メイン処理 (UI構築)
# ==========================================
def main():
    # サイドバー：入力インターフェース（龍樹のシンプルなUIを維持）
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
        st.info("事実を入力するだけで、AIが4Mに分類し、ツリー構造で深掘り分析を行います。")

    # メイン画面
    st.title("🔍 品質不具合対策論理分析ツール「龍樹 - Quality」")
    st.markdown("サイドバーの事実＋補足情報を元に、強力な分析プロンプトを生成します。")

    col1, col2 = st.columns([1, 2])
    
    with col1:
        machine_type = st.selectbox(
            "対象設備・ライン",
            ["Aライン", "Bライン", "組立工程", "検査工程", "その他"],
            help="品質データの統計を取るために選択してください"
        )
    
    # 自由記述エリア：ここが旧ツールの「4Mチェックリスト」の代わりになります
    extra_facts = st.text_area(
        "補足の事実・気づき（4Mの観点で記述すると精度が上がります）",
        height=200,
        placeholder="例：\n・治具の当たり面に磨耗が見られた（Machine）\n・前日から材料のロットが変更になっていた（Material）\n・標準書には「目視確認」としか書かれていなかった（Method）\n・作業者はその日、急ぎの指示を受けていた（Man）",
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

【補足・4Mに関する気づき】
{extra_facts}
"""
        
        if not input_what or not input_how:
            st.warning("⚠️ サイドバーの「何を」「どうした」は必須入力項目です。")
        else:
            if save_to_csv(combined_facts, machine_type):
                st.success("✅ 品質ログを記録しました。")
            
            # 引数に machine_type を追加してコンテキストを強化
            generated_text = generate_prompt_template(combined_facts, machine_type)
            
            st.markdown("---")
            st.subheader("🤖 AIへの指令書（ツリー構造分析版）")
            st.code(generated_text, language="markdown")
            
            st.markdown("""
            **このプロンプトの特徴:**
            - **ツリー構造:** 原因を一本道にせず、可能性を分岐させて検討させます。
            - **4M自動抽出:** フリーテキストからAIが4M要素を読み取ります。
            - **ポカヨケ重視:** 精神論ではない恒久対策を提案させます。
            """)

if __name__ == "__main__":
    main()
