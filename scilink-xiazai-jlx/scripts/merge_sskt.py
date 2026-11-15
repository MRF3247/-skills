import pymupdf
from pathlib import Path

D = Path("/Users/Jin/Desktop")
cv = pymupdf.open("/tmp/sskt_cover.pdf")
toc = pymupdf.open("/tmp/sskt_toc.pdf")
body = pymupdf.open("/tmp/sskt_body.pdf")

out = pymupdf.open()
book = []
book.append([1, "封面", 1])
out.insert_pdf(cv, from_page=0, to_page=0)

book.append([1, "目录", out.page_count + 1])
out.insert_pdf(toc)

book.append([1, "第一篇 起步", out.page_count + 1])
out.insert_pdf(body)

book.append([1, "封底", out.page_count + 1])
out.insert_pdf(cv, from_page=1, to_page=1)

out.set_toc(book)
dest = D / "《放养硕博自救指南——从起步到发表》.pdf"
out.save(dest, garbage=4, deflate=True)
print(f"{out.page_count} 页 | {round(dest.stat().st_size/1024)}KB -> {dest}")
for lvl, t, p in book:
    print(f"   p{p:>2} {t}")
