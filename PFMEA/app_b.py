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

# 表示列定義：(DBカラム名, 表示名)
DISPLAY_COLUMNS = [
    ("id",                          "No."),
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
    ("status",                      "ステータス"),
    ("remarks",                     "備考"),
]

DB_TO_DISPLAY = {db: disp for db, disp in DISPLAY_COLUMNS}
DISPLAY_TO_DB = {disp: db for db, disp in DISPLAY_COLUMNS}

# 編集可能な列（表示名）
EDITABLE_COLUMNS = [
    "故障モード",
    "故障の影響",
    "厳しさ（S）",
    "故障原因／メカニズム",
    "発生頻度（O）",
    "発生予防",
    "故障の検出",
    "検出度（D）",
    "備考",
]

def records_to_df(records: list[dict]) -> pd.DataFrame:
    """
    DBレコードリストを表示用DataFrameに変換する
    """
    if not records:
        return pd.DataFrame()
    rows = []
    for r in records:
        row = {disp: r.get(db, "") for db, disp in DISPLAY_COLUMNS}
        rows.append(row)
    df = pd.DataFrame(rows)
    return df

def main():
    st.set_page_config(page_title="龍樹（P-FMEA）確認・出力", layout="wide")
    initialize_db()

    st.title("龍樹（P-FMEA）確認・出力アプリ")
    master = load_master()

    # ----------------------------------------
    # 区画1：検索・絞り込み
    # ----------------------------------------
    st.header("① 検索・絞り込み")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        f_industry = st.selectbox(
            "業種", ["（全て）"] + master["industries"]
        )
    with col2:
        f_product = st.text_input("製品名（部分一致）")
    with col3:
        all_processes = (
            master["processes"]["段取"] + master["processes"]["成形"]
        )
        f_process = st.selectbox(
            "工程名", ["（全て）"] + all_processes
        )
    with col4:
        f_status = st.selectbox(
            "ステータス", ["全て", "洗い出し中", "承認済み"]
        )

    f_keyword = st.text_input("故障モード　キーワード検索")

    if st.button("検索する", type="primary"):
        records = fetch_records(
            industry = None if f_industry == "（全て）" else f_industry,
            product  = f_product.strip() or None,
            process  = None if f_process == "（全て）" else f_process,
            status   = f_status,
            keyword  = f_keyword.strip() or None
        )
        st.session_state["search_results"] = records
        st.session_state.pop("edited_df", None)

    # ----------------------------------------
    # 区画2：PFMEA全体閲覧・編集
    # ----------------------------------------
    if "search_results" in st.session_state:
        records = st.session_state["search_results"]
        st.divider()
        st.header("② PFMEA閲覧・編集")

        if not records:
            st.warning("該当するレコードがありません。")
            return

        st.caption(f"{len(records)}件 該当")

        df = records_to_df(records)

        # 編集可能DataFrameとして表示
        edited_df = st.data_editor(
            df,
            use_container_width=True,
            num_rows="fixed",
            disabled=[
                col for col in df.columns
                if col not in EDITABLE_COLUMNS
            ],
            column_config={
                "厳しさ（S）":   st.column_config.NumberColumn(min_value=1, max_value=10, step=1),
                "発生頻度（O）": st.column_config.NumberColumn(min_value=1, max_value=10, step=1),
                "検出度（D）":   st.column_config.NumberColumn(min_value=1, max_value=10, step=1),
            },
            key="data_editor"
        )
        st.session_state["edited_df"] = edited_df

        # ----------------------------------------
        # 区画3：承認・保存・出力
        # ----------------------------------------
        st.divider()
        st.header("③ 承認・出力")

        col_save, col_approve, col_excel = st.columns(3)

        # 編集内容を保存
        with col_save:
            if st.button("編集内容を保存する", type="primary"):
                edited  = st.session_state["edited_df"]
                original_records = st.session_state["search_results"]
                save_count = 0
                for i, row in edited.iterrows():
                    original = original_records[i]
                    updated = {}
                    for disp_name in EDITABLE_COLUMNS:
                        db_key   = DISPLAY_TO_DB[disp_name]
                        new_val  = row[disp_name]
                        orig_val = original.get(db_key, "")
                        if str(new_val) != str(orig_val):
                            updated[db_key] = new_val
                    # 評点が変わっていればRPNを再計算
                    s = int(row["厳しさ（S）"])
                    o = int(row["発生頻度（O）"])
                    d = int(row["検出度（D）"])
                    new_rpn = s * o * d
                    if new_rpn != original.get("rpn"):
                        updated["rpn"] = new_rpn
                    if updated:
                        update_record(original["id"], updated)
                        save_count += 1
                if save_count > 0:
                    st.success(f"{save_count}件の編集内容を保存しました。")
                    st.session_state.pop("search_results", None)
                    st.session_state.pop("edited_df", None)
                    st.rerun()
                else:
                    st.info("変更はありませんでした。")

        # 承認済みに変更
        with col_approve:
            if st.button("承認済みにする"):
                target_ids = [r["id"] for r in st.session_state["search_results"]]
                approve_records(target_ids)
                st.success(f"{len(target_ids)}件を承認済みにしました。")
                st.session_state.pop("search_results", None)
                st.session_state.pop("edited_df", None)
                st.rerun()

        # Excel出力
        with col_excel:
            approved = [
                r for r in st.session_state["search_results"]
                if r["status"] == "承認済み"
            ]
            if approved:
                industry_val = approved[0].get("industry", "")
                product_val  = approved[0].get("product", "")
                excel_bytes  = build_excel(approved, industry_val, product_val)
                filename     = make_filename(industry_val, product_val)
                st.download_button(
                    label    = f"Excelで出力する（{len(approved)}件）",
                    data     = excel_bytes,
                    file_name= filename,
                    mime     = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.caption("承認済みのレコードがありません。")

if __name__ == "__main__":
    main()
