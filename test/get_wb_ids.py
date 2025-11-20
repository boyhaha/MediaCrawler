from bs4 import BeautifulSoup

file_path = "/repo/data/spider_twitter.html"

with open(file_path, "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")

account_ids = []

# 遍历表格每一行
for row in soup.select("table tr")[1:]:  # 跳过表头
    cols = row.find_all("td")
    if len(cols) < 4:
        continue
    site_type = cols[1].get_text(strip=True)
    if site_type == "微博":
        account_id = cols[3].get_text(strip=True)
        account_ids.append(account_id)

from pprint import pprint
pprint(account_ids)
