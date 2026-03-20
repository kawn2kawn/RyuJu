import json
import pandas as pd
import streamlit as st
from pathlib import Path

from database import initialize_db, fetch_records, update_record
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

# 表示列定義：(DBカラム名, 表示名)
DISPLAY_COLUMNS = [
    ("id",                          "No."),
    ("created_at",                  "登録日時"),
    ("industry",                    "業種"),
    ("product",                     "製品名"),
    ("process",                     "工程の役割"),
    ("failure_mode",                "故障モード"),
    ("effect",                      "故障の影響"),
    ("severity",                    "厳しさ（S）"),
    ("cause",                       "故障原因／メカニズム"),
    ("occurrence",                  "発生頻度（O）"),
    ("current_control_prevention",  "発生予防"),
    ("current_control_detection",   "故障の検出"),
    ("detection",                   "検出度（D）"),
    ("rpn",                         "RPN"),
    ("remarks",                     "備考"),
]

DB_TO_DISPLAY = {db: disp for db, disp in DISPLAY_COLUMNS}
DISPLAY_TO_DB = {disp: db for db, disp in DISPLAY_COLUMNS}

def records_to_df(records: list[dict]) -> pd.DataFrame:
    if not records:
        return pd.DataFrame()
    rows = []
    for r in records:
        row = {disp: r.get(db, "") for db, disp in DISPLAY_COLUMNS}
        rows.append(row)
    return pd.DataFrame(rows)

def main():
    st.set_page_config(page_title="龍樹（P-FMEA）確認・出力", page_icon="🌳", layout="wide")
    initialize_db()

    st.title("🌳 龍樹（P-FMEA）確認・出力アプリ")

    # ログアウトボタン
    col_title, col_logout = st.columns([8, 1])
    with col_logout:
        if st.button("ログアウト"):
            st.session_state.logged_in = False
            st.rerun()

    master = load_master()

    # ----------------------------------------
    # 区画1：検索・絞り込み
    # ----------------------------------------
    st.header("① 検索・絞り込み")

    col1, col2, col3 = st.columns(3)
    with col1:
        f_industry = st.selectbox(
            "業種", ["（全て）"] + master["industries"]
        )
    with col2:
        f_product = st.selectbox(
            "製品名", ["（全て）"] + master["products"]
        )
    with col3:
        all_processes = (
            master["processes"]["段取"] + master["processes"]["成形"]
        )
        f_process = st.selectbox(
            "工程名", ["（全て）"] + all_processes
        )

    f_keyword = st.text_input("故障モード　キーワード検索")

    if st.button("検索する", type="primary"):
        records = fetch_records(
            industry = None if f_industry == "（全て）" else f_industry,
            product  = None if f_product == "（全て）" else f_product,
            process  = None if f_process == "（全て）" else f_process,
            status   = None,
            keyword  = f_keyword.strip() or None
        )
        st.session_state["search_results"] = records
        st.session_state.pop("selected_ids", None)
        st.session_state.pop("edit_scores", None)

    # ----------------------------------------
    # 区画2：一覧表示・チェックボックス選択
    # ----------------------------------------
    if "search_results" in st.session_state:
        records = st.session_state["search_results"]
        st.divider()
        st.header("② レコード選択")

        if not records:
            st.warning("該当するレコードがありません。")
            return

        st.caption(f"{len(records)}件 該当　　チェックを入れたレコードに対して編集・出力が行えます。")

        # チェックボックス付き一覧
        selected_ids = []
        df = records_to_df(records)

        # ヘッダー行
        header_cols = st.columns([0.5, 1, 2, 2, 2, 3, 3, 1, 1, 1, 1])
        headers = ["選択", "No.", "登録日時", "業種", "製品名", "工程の役割", "故障モード", "S", "O", "D", "RPN"]
        for col, h in zip(header_cols, headers):
            col.markdown(f"**{h}**")
        st.divider()

        for i, record in enumerate(records):
            row_cols = st.columns([0.5, 1, 2, 2, 2, 3, 3, 1, 1, 1, 1])
            checked = row_cols[0].checkbox("", key=f"chk_{record['id']}", label_visibility="collapsed")
            row_cols[1].write(record.get("id", ""))
            row_cols[2].write(str(record.get("created_at", ""))[:10])
            row_cols[3].write(record.get("industry", ""))
            row_cols[4].write(record.get("product", ""))
            row_cols[5].write(record.get("process", ""))
            row_cols[6].write(record.get("failure_mode", ""))
            row_cols[7].write(record.get("severity", ""))
            row_cols[8].write(record.get("occurrence", ""))
            row_cols[9].write(record.get("detection", ""))
            row_cols[10].write(record.get("rpn", ""))

            if checked:
                selected_ids.append(record["id"])

        st.session_state["selected_ids"] = selected_ids

        # ----------------------------------------
        # 区画3：選択レコードの編集
        # ----------------------------------------
        if selected_ids:
            st.divider()
            st.header("③ 選択レコードの編集")
            st.caption(f"{len(selected_ids)}件を選択中")

            selected_records = [r for r in records if r["id"] in selected_ids]
            edit_scores = {}

            for record in selected_records:
                with st.expander(
                    f"No.{record['id']}　{record['process']}　{record['failure_mode']}",
                    expanded=True
                ):
                    st.markdown(f"**故障の影響：** {record.get('effect', '')}")
                    st.markdown(f"**故障原因：** {record.get('cause', '')}")

                    c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
                    with c1:
                        s = st.number_input(
                            "厳しさ（S）", min_value=1, max_value=10,
                            value=int(record.get("severity", 1)),
                            key=f"es_{record['id']}"
                        )
                    with c2:
                        o = st.number_input(
                            "発生頻度（O）", min_value=1, max_value=10,
                            value=int(record.get("occurrence", 1)),
                            key=f"eo_{record['id']}"
                        )
                    with c3:
                        d = st.number_input(
                            "検出度（D）", min_value=1, max_value=10,
                            value=int(record.get("detection", 1)),
                            key=f"ed_{record['id']}"
                        )
                    with c4:
                        st.metric("RPN", s * o * d)

                    remarks = st.text_input(
                        "備考", value=record.get("remarks", "") or "",
                        key=f"er_{record['id']}"
                    )

                    edit_scores[record["id"]] = {
                        "severity": s, "occurrence": o, "detection": d,
                        "rpn": s * o * d, "remarks": remarks
                    }

            st.session_state["edit_scores"] = edit_scores

            # ----------------------------------------
            # 区画4：保存・出力
            # ----------------------------------------
            st.divider()
            st.header("④ 保存・出力")

            col_save, col_excel = st.columns(2)

            with col_save:
                if st.button("編集内容を保存する", type="primary"):
                    save_count = 0
                    for rid, scores in st.session_state["edit_scores"].items():
                        original = next(r for r in records if r["id"] == rid)
                        updated = {}
                        for key in ["severity", "occurrence", "detection", "rpn", "remarks"]:
                            if str(scores[key]) != str(original.get(key, "")):
                                updated[key] = scores[key]
                        if updated:
                            update_record(rid, updated)
                            save_count += 1
                    if save_count > 0:
                        st.success(f"{save_count}件の編集内容を保存しました。")
                        st.session_state.pop("search_results", None)
                        st.session_state.pop("selected_ids", None)
                        st.session_state.pop("edit_scores", None)
                        st.rerun()
                    else:
                        st.info("変更はありませんでした。")

            with col_excel:
                if st.button("選択したレコードをExcelで出力する"):
                    output_records = []
                    for record in selected_records:
                        r = record.copy()
                        if record["id"] in st.session_state.get("edit_scores", {}):
                            r.update(st.session_state["edit_scores"][record["id"]])
                        output_records.append(r)

                    industry_val = output_records[0].get("industry", "")
                    product_val  = output_records[0].get("product", "")
                    excel_bytes  = build_excel(output_records, industry_val, product_val)
                    filename     = make_filename(industry_val, product_val)

                    st.download_button(
                        label    = f"📥 ダウンロード（{len(output_records)}件）",
                        data     = excel_bytes,
                        file_name= filename,
                        mime     = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

if __name__ == "__main__":
    if check_password():
        main()
