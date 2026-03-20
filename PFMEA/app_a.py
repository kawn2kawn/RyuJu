import json
import pandas as pd
import streamlit as st
from pathlib import Path

from database import initialize_db, fetch_records, update_record, approve_records
from excel_output import build_excel, make_filename

MASTER_PATH = Path(__file__).parent / "master_data.json"

def load_master() -> dict:
    with open(MASTER_PATH, encoding="utf-8") as f:
        return json.load(f)

def check_password():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if st.session_state.logged_in:
        return True

    st.markdown("## 🔒 龍樹（P-FMEA）ログイン")
    st.info("社員番号とパスワードを入力してください。")

    col1, col2 = st.columns(2)
    with col1:
        input_emp_id = st.text_input("社員番号（数字4桁）", max_chars=4, placeholder="例：1234")
    with col2:
        input_password = st.text_input("パスワード", type="password")

    if st.button("ログイン", type="primary"):
        CORRECT_PASSWORD = "wako0001"
        if not input_emp_id.isdigit() or len(input_emp_id) != 4:
            st.error("❌ 社員番号は「数字4桁」で入力してください。")
            return False
        if input_password == CORRECT_PASSWORD:
            st.session_state.logged_in = True
            st.session_state.emp_id = input_emp_id
            st.success("ログイン成功")
            st.rerun()
            return True
        else:
            st.error("❌ パスワードが違います。")
            return False

    return False

def main():
    st.set_page_config(page_title="龍樹（P-FMEA）確認・出力", page_icon="🌳", layout="wide")
    initialize_db()

    st.title("龍樹（P-FMEA）洗い出しアプリ")
    master = load_master()

    # ----------------------------------------
    # 区画1：対象情報入力
    # ----------------------------------------
    st.header("① 対象情報入力")

    col1, col2 = st.columns(2)
    with col1:
        industry = st.selectbox("業種", master["industries"])

        product_selection = st.selectbox("製品名", master["products"])

        if product_selection == "その他":
            product = st.text_input(
                "製品名を入力してください",
                placeholder="例：吸気ダクト"
            )
            st.caption("⚠️ 客先品番は入力しないでください。")
        else:
            product = product_selection
            st.caption("⚠️ 客先品番は入力しないでください。")

    with col2:
        category = st.selectbox("工程分類", master["process_categories"])
        process  = st.selectbox("工程名", master["processes"][category])

    # 工程パラメータの動的表示
    param_defs = master["parameters"].get(process, [])
    params = {}

    if param_defs:
        st.subheader("工程パラメータ")
        for p in param_defs:
            if p["type"] == "radio":
                params[p["name"]] = st.radio(
                    p["name"],
                    p["options"],
                    horizontal=True
                )
            elif p["type"] == "selectbox":
                params[p["name"]] = st.selectbox(p["name"], p["options"])

    # ----------------------------------------
    # 区画2：プロンプト生成・コピー
    # ----------------------------------------
    st.divider()
    st.header("② プロンプト生成")

    if st.button("プロンプトを生成する", type="primary"):
        if not product.strip():
            st.error("製品名を入力してください。")
        else:
            prompt = build_prompt(industry, product.strip(), process, params)
            st.session_state["generated_prompt"] = prompt

    if "generated_prompt" in st.session_state:
        st.text_area(
            "生成されたプロンプト",
            value=st.session_state["generated_prompt"],
            height=300,
            key="prompt_display"
        )
        st.info("⬆️ 上のテキストエリア内をクリックして全選択（Ctrl+A）→ コピー（Ctrl+C）し、ChatGPTに貼り付けて実行してください。")

    # ----------------------------------------
    # 区画3：LLM出力の取り込み
    # ----------------------------------------
    st.divider()
    st.header("③ LLM出力の取り込み")

    llm_output = st.text_area(
        "ChatGPTの出力（JSON）をここに貼り付けてください",
        height=200,
        key="llm_output"
    )

    if st.button("解析・取り込み", type="primary"):
        if not llm_output.strip():
            st.error("ChatGPTの出力を貼り付けてください。")
        else:
            records, error = parse_llm_output(llm_output)
            if error:
                st.error(error)
                st.session_state.pop("parsed_records", None)
            else:
                st.session_state["parsed_records"] = records
                st.session_state["parse_meta"] = {
                    "industry": industry,
                    "product": product.strip(),
                    "process": process,
                    "params": params
                }
                st.success(f"{len(records)}件の故障モードを取り込みました。")

    if "parsed_records" in st.session_state:
        st.dataframe(
            to_display_records(st.session_state["parsed_records"]),
            use_container_width=True
        )

    # ----------------------------------------
    # 区画4：評点入力・登録
    # ----------------------------------------
    if "parsed_records" in st.session_state:
        st.divider()
        st.header("④ 評点入力・登録")
        st.caption("各故障モードに対して厳しさ（S）・発生頻度（O）・検出度（D）を入力してください。")

        records   = st.session_state["parsed_records"]
        meta      = st.session_state["parse_meta"]
        scores    = []
        all_valid = True

        for i, rec in enumerate(records):
            with st.expander(f"{i + 1}. {rec['failure_mode']}", expanded=True):
                c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
                with c1:
                    st.markdown(f"**故障の影響：** {rec['effect']}")
                with c2:
                    s = st.number_input(
                        "厳しさ（S）", min_value=1, max_value=10,
                        key=f"s_{i}"
                    )
                with c3:
                    o = st.number_input(
                        "発生頻度（O）", min_value=1, max_value=10,
                        key=f"o_{i}"
                    )
                with c4:
                    d = st.number_input(
                        "検出度（D）", min_value=1, max_value=10,
                        key=f"d_{i}"
                    )
                rpn = s * o * d
                st.metric("RPN", rpn)

                # 評価基準参照
                criteria = master["evaluation_criteria"]
                with st.expander("📋 評価基準を参照する"):
                    tab1, tab2, tab3 = st.tabs(["厳しさ（S）", "発生頻度（O）", "検出度（D）"])
                    with tab1:
                        for c in criteria["厳しさ"]:
                            selected = "　◀ 現在の選択" if c["rank"] == s else ""
                            st.markdown(f"**{c['rank']}　{c['summary']}**{selected}")
                            st.caption(c["detail"])
                    with tab2:
                        for c in criteria["発生頻度"]:
                            selected = "　◀ 現在の選択" if c["rank"] == o else ""
                            st.markdown(f"**{c['rank']}　{c['summary']}**{selected}")
                            st.caption(c["detail"])
                    with tab3:
                        for c in criteria["検出度"]:
                            selected = "　◀ 現在の選択" if c["rank"] == d else ""
                            st.markdown(f"**{c['rank']}　{c['summary']}**{selected}")
                            st.caption(c["detail"])

                remarks = st.text_input("備考（任意）", key=f"rem_{i}")

                scores.append({
                    **rec,
                    "industry":  meta["industry"],
                    "product":   meta["product"],
                    "process":   meta["process"],
                    "gate_type": meta["params"].get("ゲート方式"),
                    "has_insert": (
                        1 if meta["params"].get("インサート部品") == "あり"
                        else 0 if meta["params"].get("インサート部品") == "なし"
                        else None
                    ),
                    "severity":   s,
                    "occurrence": o,
                    "detection":  d,
                    "rpn":        rpn,
                    "remarks":    remarks
                })

        st.divider()
        if st.button("データベースに登録する", type="primary"):
            count = insert_records(scores)
            st.success(f"{count}件をデータベースに登録しました。（ステータス：洗い出し中）")
            st.session_state.pop("parsed_records", None)
            st.session_state.pop("parse_meta", None)
            st.session_state.pop("generated_prompt", None)
            st.rerun()

if __name__ == "__main__":
    if check_password():
        main()
