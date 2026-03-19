import json

REQUIRED_KEYS = [
    "failure_mode",
    "effect",
    "cause",
    "current_control_prevention",
    "current_control_detection",
    "recommended_action"
]

DISPLAY_NAMES = {
    "failure_mode":                 "故障モード",
    "effect":                       "故障の影響",
    "cause":                        "故障原因／メカニズム",
    "current_control_prevention":   "発生予防",
    "current_control_detection":    "故障の検出",
    "recommended_action":           "是正処置"
}

def parse_llm_output(raw_text: str) -> tuple[list[dict] | None, str | None]:
    """
    LLMの出力テキストをパースして検証する
    戻り値: (レコードリスト, エラーメッセージ)
    成功時: (list, None)
    失敗時: (None, エラーメッセージ)
    """
    # トリム
    text = raw_text.strip()

    if not text:
        return None, "出力が空です。プロンプトを再確認してください。"

    # JSONパース
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None, "出力形式が正しくありません。ChatGPTの出力をそのまま貼り付けてください。"

    # 配列チェック
    if not isinstance(data, list):
        return None, "出力形式が正しくありません。ChatGPTの出力をそのまま貼り付けてください。"

    # 空配列チェック
    if len(data) == 0:
        return None, "出力が空です。プロンプトを再確認してください。"

    # 必須キー検証
    errors = []
    for i, record in enumerate(data):
        for key in REQUIRED_KEYS:
            if key not in record:
                errors.append(f"{i + 1}件目：「{DISPLAY_NAMES[key]}」が欠損しています。")

    if errors:
        error_msg = "以下の項目が欠損しています。ChatGPTの出力を再確認してください。\n"
        error_msg += "\n".join(errors)
        return None, error_msg

    # 必要なキーのみ抽出して返す
    cleaned = []
    for record in data:
        cleaned.append({key: str(record[key]).strip() for key in REQUIRED_KEYS})

    return cleaned, None


def to_display_records(records: list[dict]) -> list[dict]:
    """
    内部キーを日本語表示名に変換したレコードリストを返す
    Streamlitのst.dataframe表示用
    """
    result = []
    for r in records:
        result.append({DISPLAY_NAMES[k]: r[k] for k in REQUIRED_KEYS if k in r})
    return result
