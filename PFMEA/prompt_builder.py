import json
from pathlib import Path

MASTER_PATH = Path(__file__).parent / "master_data.json"

def load_master() -> dict:
    with open(MASTER_PATH, encoding="utf-8") as f:
        return json.load(f)

def get_additional_risks(process: str, params: dict) -> list[str]:
    """
    工程名とパラメータの選択値から追加リスクのリストを返す
    params: {"パラメータ名": "選択値", ...}
    """
    master = load_master()
    risks_def = master["additional_risks"].get(process, {})
    risks = []

    # 共通リスク
    if "_common" in risks_def:
        for r in risks_def["_common"]:
            if r not in risks:
                risks.append(r)

    # パラメータ別リスク
    for param_name, selected_value in params.items():
        if param_name in risks_def:
            additional = risks_def[param_name].get(selected_value, [])
            for r in additional:
                if r not in risks:
                    risks.append(r)

    return risks

def build_prompt(
    industry: str,
    product: str,
    process: str,
    params: dict
) -> str:
    """
    プロンプト文字列を生成して返す
    params: {"パラメータ名": "選択値", ...}
    """
    additional_risks = get_additional_risks(process, params)

    # パラメータブロック生成
    if params:
        param_lines = "\n".join([f"- {k}：{v}" for k, v in params.items()])
        param_block = f"""
【工程パラメータ】
{param_lines}
"""
    else:
        param_block = ""

    # 追加リスク指示ブロック生成
    if additional_risks:
        risks_str = "、".join([f"「{r}」" for r in additional_risks])
        additional_block = f"""
- 以下の故障モードを必ず含めること：
  {risks_str}
"""
    else:
        additional_block = ""

    prompt = f"""あなたは製造業の品質エンジニアです。
以下の工程についてPFMEA（プロセスFMEA）の洗い出しを行ってください。

【対象製品】
業種：{industry}
製品：{product}

【工程名】
{process}
{param_block}
【出力ルール】
- 必ずJSON配列のみを出力すること
- 前後に説明文・見出し・コードブロック記号（```）を一切含めないこと
- 各要素は以下のキーを持つこと

[
  {{
    "failure_mode": "故障モード",
    "effect": "故障の影響（業種・製品を考慮した具体的な影響）",
    "cause": "故障原因／メカニズム",
    "current_control_prevention": "発生予防",
    "current_control_detection": "故障の検出",
    "recommended_action": "是正処置"
  }}
]

- 通常の{process}リスクを最低5件出力すること
- パラメータによる追加リスクはそれとは別にすべて出力すること
- 合計件数の上限は設けない
- effectの記述は対象製品の用途・業種を考慮した具体的な影響を記述すること{additional_block}"""

    return prompt.strip()
