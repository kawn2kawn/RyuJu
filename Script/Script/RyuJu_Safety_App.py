import streamlit as st
import pandas as pd
import datetime
import os
import uuid

# ==========================================
# 設定・定数定義
# ==========================================
st.set_page_config(
    page_title="労働安全・ヒヤリハット論理的分析補助ツール 龍樹(Safety)",
    page_icon="⛑️", # 安全第一のヘルメットアイコン
    layout="wide",
    initial_sidebar_state="expanded"
)

DATA_DIR = "data"
LOG_FILE = os.path.join(DATA_DIR, "safety_fact_log.csv")

# ==========================================
# 認証・ログイン関連処理 (追加機能)
# ==========================================
def check_password():
    """
    ログイン認証を行う関数。
    セッションステートを使用してログイン状態を保持する。
    """
    # セッションステートの初期化（未定義ならFalseに設定）
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False

    # ログイン済みなら何もしない（メイン処理へ進む）
    if st.session_state.logged_in:
        return True

    # --- ログイン画面のUI ---
    st.markdown("## 🔒 労働安全・ヒヤリハット分析ツール ログイン")
    st.info("社員番号とパスワードを入力してください。")

    col1, col2 = st.columns(2)
    with col1:
        # 社員番号入力（最大文字数を指定して誤入力を防ぐ）
        input_emp_id = st.text_input("社員番号 (数字4桁)", max_chars=4, placeholder="例: 1234")
    with col2:
        # パスワード入力（type='password'で伏せ字にする）
        input_password = st.text_input("パスワード", type="password")

    if st.button("ログイン", type="primary"):
        # --- 認証ロジック ---
        CORRECT_PASSWORD = "wako0001"

        # バリデーション：数字4桁かチェック
        if not input_emp_id.isdigit() or len(input_emp_id) != 4:
            st.error("❌ 社員番号は「数字4桁」で入力してください。")
            return False
        
        # パスワードチェック
        if input_password == CORRECT_PASSWORD:
            st.session_state.logged_in = True
            st.session_state.emp_id = input_emp_id  # 社員番号を記録（後でログに使える）
            st.success("ログイン成功")
            st.rerun()  # 画面を再読み込みしてメインアプリを表示
            return True
        else:
            st.error("❌ パスワードが違います。")
            return False
    
    return False

# ==========================================
# 関数定義 (既存機能)
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
    
    # ログイン中の社員番号を取得（未ログイン時はUnknown）
    recorder_id = st.session_state.get('emp_id', 'Unknown')
    
    new_data = {
        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
        "case_id": case_id,
        "recorder_id": recorder_id, # 記録者IDを追加
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
    【安全・ヒヤリハット分析版（強化型）】
    論理的連鎖（Chain of Logic）に加え、逆検証（Reverse Verification）を強制するプロンプト
    """
    prompt = f"""
# 労働安全・ヒヤリハット原因分析要請（論理連鎖・逆検証特化）

あなたは製造業における「労働安全衛生の熟練コンサルタント」であり、論理的思考（ロジカルシンキング）のプロフェッショナルです。
提供された事実に基づき、曖昧さを排除した「なぜなぜ分析」を行い、必ず「論理の逆検証」を経てから再発防止策を立案してください。

## 1. 発生事象と事実
{facts}

## 2. 分析プロセス指示

### Step 1: リスクと要因の整理
まず、この事象が「一歩間違えればどのような重大災害（重篤度）に繋がっていたか」を推定してください。
その上で、事象に関与する以下の4要因を事実から抽出してください。
- **人的要因:** 作業者の行動、判断、心身の状態
- **管理的要因:** ルール、教育、指示、配置、工期
- **設備的要因:** 機械の構造、故障、安全装置の有無
- **環境的要因:** 作業場所、明るさ、足場、騒音

### Step 2: 論理連鎖による「なぜなぜ分析」（Why-Why Analysis）
以下のルールを厳守し、根本原因に到達するまで分析を行ってください。

**【厳守ルール：連鎖の法則】**
1. **「なぜ？」の対象を固定する**: 前の段階の「答え（Ans）」が、次の段階の「問い（Why）」の主語にならなければなりません。
2. **客観的事実と推論を分ける**: 「〜の気がする」ではなく「〜という状態だった」と記述してください。

**【出力フォーマット】**
分析は以下の形式で記述し、末端の根本原因には必ず**ID（例: R-1, R-2...）**を付与してください。

#### 分析チェーンA（主たる要因）
- **[事象]**: (ここに出発点となる事象を書く)
  - **Why1**: なぜ [事象] が起きたのか？
    - **Ans1**: [回答]
      - **Why2**: なぜ [Ans1] なのか？ (←ここがつながっていること！)
        - **Ans2**: [回答]
          - **Why3**: なぜ [Ans2] なのか？
            - **Ans3 (根本原因)**: [回答] **(ID: R-1)**

---

### Step 3: 論理の「逆検証」（Reverse Verification）
**【重要】Step 2で作成したロジックが正しいか、逆方向からテストしてください。**

1. 特定した「根本原因（Ans）」から「事象」に向かって、**「だから（Therefore）」**という接続詞で文章をつないで読んでください。
2. 「A（原因）である。**だから**、B（結果）になった」という理屈に無理や飛躍がないか確認してください。
3. もし論理が飛躍している（「風が吹けば桶屋が儲かる」状態）場合は、Step 2に戻って中間要因を補完・修正してください。

**【出力形式】**
- **逆検証の結果**: 論理成立 / 修正済み（修正内容を簡潔に記述）
- **確認フロー**: [根本原因] → (だから) → [中間要因] → (だから) → [発生事象]

---

### Step 4: 対策提案（ID紐づけ必須）
特定された根本原因（ID付き）に対して、以下の対策を提案してください。
「気をつける」「注意する」といった精神論は禁止とし、**物理的・仕組み的対策**（ポカヨケ、ハード対策）を優先してください。

**【出力形式】**
- **対策案1**: [具体的な対策内容]
  - **対象ID**: R-1
  - **区分**: 設備対策 / 管理対策 / 暫定処置

- **対策案2**: [具体的な対策内容]
  - **対象ID**: R-2
  - **区分**: 設備対策 / 管理対策 / 暫定処置

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
        # 十字をグリーンにする
        st.markdown('<h1><span style="color: #008000;">✙</span> 安全・ヒヤリ入力</h1>', unsafe_allow_html=True)
        
        # ログイン情報の表示
        current_user = st.session_state.get('emp_id', 'Unknown')
        st.caption(f"ログイン中: 社員番号 {current_user}")
        if st.button("ログアウト", type="secondary"):
            st.session_state.logged_in = False
            st.rerun()

        st.write("---")
        
        input_who = st.text_input("誰が", placeholder="例：作業者（Aさん）、入社3ヶ月")
        input_how = st.text_input("どうした（ヒヤリ／事象）", placeholder="例：台車と接触しそうになった、指を挟みかけた")
        input_date = st.date_input("いつ（日付）", datetime.date.today())
        input_when_detail = st.text_input("いつ（詳細時刻）", placeholder="例：午前10時、残業時間帯")
        input_where = st.text_input("どこで", placeholder="例：出荷バース、第2倉庫")
        
        st.write("---")
        st.header("💡 安全分析のヒント")
        st.info("不安全な「行動」だけでなく、それを許した「環境や管理」の事実を書いてください。ヒヤリハットは宝の山です。")

    # メイン画面
    col_title, col_logo = st.columns([5, 1])
    with col_title:
        # メインタイトルの十字もグリーンにし、サイズを調整
        st.markdown('## <span style="color: #008000;">✙</span> 労災・ヒヤリハット論理分析支援ツール「🐉 龍樹 RyuJu -Safety-」', unsafe_allow_html=True)

    with col_logo:
        if os.path.exists("header_logo.png"):
            st.image("header_logo.png", use_container_width=True)
    
    # 【UI修正】フォントサイズ統一と赤文字注意喚起
    st.markdown("#### サイドバーの基本情報に加え、以下の欄に詳細な事実や気づきを入力してください。")
    st.markdown("#### :red[客先や個人が特定されるような固有名詞は絶対に入力しないでください]")

    # 安全版プレースホルダー（ヒヤリハット事例を強化）
    placeholder_text = """例（ヒヤリハット／災害）：
・【ヒヤリ】コンベアの詰まりを直そうとして、機械を止めずに手をいれてしまい、コンベアとコンベアカバーの間に指を挟まれそうになった
・いつもやっている方法なので、大丈夫だと思った
・コンベアのスピードはゆっくりなので問題ないとおもった
・コンベア上で搬送物の「詰まり」が発生し、正常な搬送が滞っていた
・詰まりが発生した箇所は、作業者が手の届く範囲であった
・コンベアの動力（電源）は切られていなかった
・「機械を止める」という手順を踏まずに作業に着手した
・稼働中の設備内（コンベアとカバーの隙間付近）に手を侵入させた
・稼働中のコンベアに対して、手が侵入できる物理的な隙間や開口部があった"""

    st.markdown("#### 詳細な事実・調査結果（三現主義で多くの事実を収集／人的・物的要因を意識すると精度が上がります）")
    
    extra_facts = st.text_area(
        label="詳細な事実・調査結果",
        label_visibility="collapsed",
        height=450,
        placeholder=placeholder_text,
    )

    if st.button("安全・ヒヤリ分析プロンプトを生成する", type="primary"):
        combined_facts = f"""
【事象の概要】
・事象: {input_how}

【調査による事実】
・発生日: {input_date}
・詳細時間: {input_when_detail}
・場所: {input_where}
・担当者情報: {input_who}

【詳細な事実・調査結果・要因に関する気づき】
{extra_facts}
"""
        
        if not input_how:
            st.warning("⚠️ サイドバーの「どうした」は必須入力項目です。")
        else:
            if save_to_csv(combined_facts):
                st.success("✅ 安全・ヒヤリログを記録しました。")
            
            generated_text = generate_prompt_template(combined_facts)
            
            st.markdown("---")
            st.subheader("🤖 AIへの指令書（安全・ヒヤリ分析版）")
            
            # 修正箇所：コピーボタン（st.code）を廃止し、text_areaと指示文に変更
            st.info("💡 **下のテキストエリア内を全選択（Ctrl+A）してコピー**し、ChatGPTやGemini等に貼り付けてください。")
            
            # 読み取り専用のテキストエリアとして表示（heightは内容に合わせて調整）
            st.text_area(
                label="プロンプト出力エリア",
                value=generated_text,
                height=600,
                label_visibility="collapsed"
            )
            
            st.markdown("""
            **安全・ヒヤリ分析プロンプトの特徴:**
            1. **連鎖ルールの強制:** 「前の答えが次の質問になる」形式を指定し、論理の飛躍を防ぎます。
            2. **逆検証（NEW）:** 「原因→だから→結果」と逆から読んで成立するか確認し、論理の強さを担保します。
            3. **精神論の排除:** 「気をつける」等の対策を禁止し、物理対策を提案させます。
            """)

if __name__ == "__main__":
    # パスワード認証チェック
    if check_password():
        main()
