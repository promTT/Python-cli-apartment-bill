import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
BASIC_INFO_PATH = BASE_DIR / "basic_info.json"
PREVIOUS_METER_PATH = BASE_DIR / "previous_meter.json"
CURRENT_METER_PATH = BASE_DIR / "current_meter.json"
FINAL_BILLS_PATH = BASE_DIR / "final_apartment_bills.json"


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_json(path: Path, data):
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)


def flatten_meters(meter_list):
    flat = {}
    for item in meter_list:
        for unit, value in item.items():
            flat[unit] = value
    return flat


def find_meter_index(meter_list, unit_number):
    for index, item in enumerate(meter_list):
        if unit_number in item:
            return index
    return None


def update_meter_value(meter_list, unit_number, new_value):
    index = find_meter_index(meter_list, unit_number)
    if index is None:
        meter_list.append({unit_number: new_value})
        return "added"
    meter_list[index][unit_number] = new_value
    return "updated"


def prompt_yes_no(question):
    while True:
        answer = input(question).strip().upper()
        if answer in {"Y", "N"}:
            return answer
        print("กรุณาพิมพ์ Y หรือ N เท่านั้น")


def prompt_meter_value(prompt_text):
    while True:
        raw = input(prompt_text).strip()
        try:
            value = int(raw)
        except ValueError:
            print("กรุณาใส่เป็นตัวเลขจำนวนเต็ม")
            continue
        if value < 0 or value > 9999:
            print("กรุณาใส่ค่ามิเตอร์ระหว่าง 0 ถึง 9999")
            continue
        return value


def classify_issue(delta):
    if delta < 0:
        return "ติดลบ"
    if delta > 500:
        return "เกิน 500 หน่วย"
    return None


def build_issues(info, prev_meter, curr_meter):
    rooms_config = info.get("rooms_config", {})
    prev_water = flatten_meters(prev_meter.get("water", []))
    prev_electric = flatten_meters(prev_meter.get("electric", []))
    curr_water = flatten_meters(curr_meter.get("water", []))
    curr_electric = flatten_meters(curr_meter.get("electric", []))

    issues = []
    for unit_number in rooms_config.keys():
        for meter_type, previous_map, current_map in (
            ("water", prev_water, curr_water),
            ("electric", prev_electric, curr_electric),
        ):
            previous_value = previous_map.get(unit_number, 0)
            current_value = current_map.get(unit_number, 0)
            delta = current_value - previous_value
            issue_type = classify_issue(delta)
            if issue_type is None:
                continue
            issues.append({
                "unit_number": unit_number,
                "meter_type": meter_type,
                "previous_value": previous_value,
                "current_value": current_value,
                "delta": delta,
                "issue_type": issue_type,
            })

    return issues


def describe_meter_type(meter_type):
    return "น้ำ" if meter_type == "water" else "ไฟ"


def review_issue(issue, prev_meter, curr_meter):
    unit_number = issue["unit_number"]
    meter_type = issue["meter_type"]
    previous_value = issue["previous_value"]
    current_value = issue["current_value"]
    delta = issue["delta"]
    issue_type = issue["issue_type"]

    print("\n" + "=" * 72)
    print(f"ห้อง {unit_number} | {describe_meter_type(meter_type)} {issue_type}")
    print(f"เดือนเก่า: {previous_value}")
    print(f"เดือนใหม่: {current_value}")
    print(f"ผลต่าง   : {delta}")

    old_updated = None
    new_updated = None

    old_answer = prompt_yes_no("เดือนเก่าถูกหรือไม่? (Y/N): ")
    if old_answer == "N":
        old_updated = prompt_meter_value("ใส่เลขเดือนเก่าใหม่: ")

    new_answer = prompt_yes_no("เดือนใหม่ถูกหรือไม่? (Y/N): ")
    if new_answer == "N":
        new_updated = prompt_meter_value("ใส่เลขเดือนใหม่ใหม่: ")

    return {
        "unit_number": unit_number,
        "meter_type": meter_type,
        "issue_type": issue_type,
        "previous_value": previous_value,
        "current_value": current_value,
        "old_answer": old_answer,
        "new_answer": new_answer,
        "old_updated": old_updated,
        "new_updated": new_updated,
    }


def apply_review_result(result, prev_meter, curr_meter):
    unit_number = result["unit_number"]
    meter_type = result["meter_type"]

    if result["old_answer"] == "N" and result["old_updated"] is not None:
        update_meter_value(prev_meter[meter_type], unit_number, result["old_updated"])

    if result["new_answer"] == "N" and result["new_updated"] is not None:
        update_meter_value(curr_meter[meter_type], unit_number, result["new_updated"])


def format_summary_line(result):
    meter_label = describe_meter_type(result["meter_type"])
    return (
        f"ห้อง {result['unit_number']} มี{meter_label}{result['issue_type']} | "
        f"เดือนเก่า {result['previous_value']} ({result['old_answer']}) | "
        f"เดือนใหม่ {result['current_value']} ({result['new_answer']})"
    )


def regenerate_final_bill():
    try:
        from processes import get_calculated_bill_data
    except Exception:
        return False

    bill_data = get_calculated_bill_data()
    if not bill_data:
        return False

    save_json(FINAL_BILLS_PATH, bill_data)
    return True


def main():
    info = load_json(BASIC_INFO_PATH)
    prev_meter = load_json(PREVIOUS_METER_PATH)
    curr_meter = load_json(CURRENT_METER_PATH)

    issues = build_issues(info, prev_meter, curr_meter)
    if not issues:
        print("ไม่พบห้องที่มีไฟหรือน้ำติดลบ หรือเกิน 500 หน่วย")
        return

    print("พบรายการที่ต้องตรวจสอบทั้งหมด")
    for issue in issues:
        print(
            f"- ห้อง {issue['unit_number']} | {describe_meter_type(issue['meter_type'])} | "
            f"เดือนเก่า {issue['previous_value']} -> เดือนใหม่ {issue['current_value']} | {issue['issue_type']}"
        )

    print("\nเริ่มตรวจทีละห้อง")
    results = []
    for issue in issues:
        result = review_issue(issue, prev_meter, curr_meter)
        apply_review_result(result, prev_meter, curr_meter)
        results.append(result)

    save_json(PREVIOUS_METER_PATH, prev_meter)
    save_json(CURRENT_METER_PATH, curr_meter)
    regenerate_final_bill()

    print("\n" + "=" * 72)
    print("สรุปผล DRC")
    for result in results:
        print(format_summary_line(result))
    print("=" * 72)
    print("บันทึกข้อมูลลง previous_meter.json และ current_meter.json เรียบร้อย")


if __name__ == "__main__":
    main()