import requests
import re
from bs4 import BeautifulSoup

url = "https://dig.taipei/Tpdig/PWorkData.aspx"
session = requests.Session()

# Step 1: 先取得首頁
r = session.get(url)
r.encoding = "utf-8"
soup = BeautifulSoup(r.text, "html.parser")

# Step 2: 擷取整個 <form> 中所有欄位（不只 hidden）
form_data = {}
for inp in soup.select("form input"):
    name = inp.get("name")
    value = inp.get("value", "")
    if name:
        form_data[name] = value

# Step 3: 模擬按下「第3頁」
form_data["__EVENTTARGET"] = "GridView1"
form_data["__EVENTARGUMENT"] = "Page$3"

# Step 4: 送出 POST（用相同 session）
resp = session.post(url, data=form_data)
resp.encoding = "utf-8"

# Step 5: 檢查結果
soup2 = BeautifulSoup(resp.text, "html.parser")
rows = soup2.select("tr")[1:]
for i, tr in enumerate(rows):
    tds = tr.select("td")
    if len(tds) >= 4:
        # 提取第4個 td 中的文字
        cell_text = tds[3].text.strip()
        
        # 提取 <a> 標籤中的 URL（從 onclick 屬性）
        link_url = None
        if tds[3].a:
            onclick = tds[3].a.get('onclick', '')
            if onclick:
                # 從 onclick="window.open('URL');" 中提取 URL
                match = re.search(r"window\.open\('([^']+)'\)", onclick)
                if match:
                    link_url = match.group(1)
        
        print(f"Row {i+1}: {tds[0].text.strip()}, {tds[1].text.strip()}, {tds[2].text.strip()}, {cell_text}")
        if link_url:
            print(f"  Link URL: {link_url}")

print("DONE, length:", len(rows))
