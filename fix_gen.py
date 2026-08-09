import json
from pathlib import Path
NEW = ("Напишите казахское слово «%s» в родительном падеже принадлежности "
       "(чей? чьё?). Ответьте одним словом на казахском языке, без пояснений.")
out = []
for line in Path("data/kk_grammar_ru.jsonl").read_text(encoding="utf-8").splitlines():
    if not line.strip():
        continue
    it = json.loads(line)
    if it["category"] != "gen":
        continue
    it["question"] = NEW % it["stem"]
    out.append(json.dumps(it, ensure_ascii=False))
Path("data/gen_ru_v2.jsonl").write_text("\n".join(out) + "\n", encoding="utf-8")
print("wrote %d genitive items" % len(out))
