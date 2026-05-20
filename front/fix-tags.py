from pathlib import Path

close_bad = "</m" + "otion>"
close_good = "</" + "di" + "v>"
open_bad = "<m" + "otion"
open_good = "<" + "di" + "v"

root = Path(__file__).parent
files = [
    root / "src/pages/NewsPage.tsx",
    root / "src/components/news/NewsFilmCard.tsx",
]

for p in files:
    if not p.exists():
        continue
    t = p.read_text()
    t = t.replace(close_bad, close_good)
    t = t.replace(open_bad, open_good)
    p.write_text(t)
    print("fixed", p.name)
