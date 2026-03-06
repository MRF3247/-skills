# 豆瓣新书速递 - 每日自动更新任务

## 前置环境检查（首次执行必做）

**在开始任何工作之前，请按顺序完成以下检查，任何一项不通过都必须先解决：**

### 检查1：Python + openpyxl

在终端执行 `python -c "import openpyxl; print('ok')"` 。如果报错，先执行 `pip install openpyxl`。

### 检查2：飞书MCP

尝试调用 `mcp_lark-mcp_im_v1_chat_list` 工具。如果工具不存在或调用失败，说明飞书MCP未安装，请按以下步骤引导用户：

> 你的阶跃AI还没有安装飞书MCP工具，需要先安装才能发送飞书通知。
> 请在阶跃AI的MCP设置中添加飞书MCP，配置JSON如下：
> ```json
> {
>   "lark-mcp": {
>     "command": "npx",
>     "args": ["-y", "@larksuiteoapi/lark-mcp", "mcp", "-a", "你的飞书APP_ID", "-s", "你的飞书APP_SECRET"]
>   }
> }
> ```
> 飞书APP_ID和APP_SECRET需要在飞书开放平台（https://open.feishu.cn）创建应用后获取。
> 添加后请重启阶跃AI，然后重新执行本任务。

如果飞书MCP可用，继续。

### 检查3：历史数据文件

检查 `C:\Users\lijin\Documents\douban_books_data.json` 是否存在：
- **存在** → 正常增量更新流程（第1步开始）
- **不存在** → 首次全量抓取流程（跳到附录A）

### 检查4：飞书多维表格

检查飞书多维表格是否可访问。调用 `mcp_lark-mcp_bitable_v1_appTable_list`，app_token = `SoIsbtDeJaMZxIsVFvecV5iPnBj`。如果失败，说明多维表格被删除或权限丢失，需要重新创建（参考附录B）。

---

## 每日增量更新流程

### 第1步：抓取豆瓣新书速递全部9页

写一个Python脚本，抓取 https://book.douban.com/latest?subcat=%E5%85%A8%E9%83%A8 全部9页。

URL规则：
- 第1页：上述URL
- 第2-9页：同URL + `&p={页码}`

请求头必须带：
```python
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://book.douban.com/',
}
```

从每个 `<li class="media clearfix">` 块中提取：
- 书名 + 详情页链接：`<h2>` 下的 `<a>` 标签
- 作者 + 出版社：`<p class="subject-abstract color-gray">` 文本，用 `/` 分割，第1项=作者、第3项=出版社
- 封面图片URL：`<img class="subject-cover">` 的 src

**请求间隔≥1.5秒**，避免被封。

### 第2步：对比历史数据，找出新书

读取 `C:\Users\lijin\Documents\douban_books_data.json`，以**豆瓣详情页链接（link字段）**为唯一标识，筛选出新增书籍。

- 无新书 → 跳到第8步，发送"今日无更新"通知，结束。
- 有新书 → 继续。

### 第3步：获取新书完整简介 + 外语书原名

对每本新书，访问其豆瓣详情页，**同时提取两项信息**：

**（1）完整内容简介**

在 `<div class="intro">` 中。页面可能有多个 `div.intro`，**优先取第2个**（展开后的完整版）：
```python
intros = re.findall(r'<div class="intro">\s*(.*?)\s*</div>', html, re.DOTALL)
text = strip_html(intros[1]) if len(intros) >= 2 else strip_html(intros[0]) if intros else ''
```

**（2）外语书的原作名和作者外文名**

判断外语书：作者字段包含 `[`、`(`、`（`、`［` 等国籍标记（如 `[美]`、`(英)`），但**排除**中国古代标记（`(元)`、`(清)`、`(宋)`、`(明)`、`(唐)` 等）。

提取原作名：在 `<div id="info">` 中查找：
```python
re.search(r'原作名:\s*</span>\s*(.*?)(?:<br|</)', info_html)
```

提取作者外文名：从作者字段的括号中提取：
```python
re.search(r'[（(]\s*([A-Za-z][\w\s.\-\',]+?)\s*[）)]', author_str)
```

**请求间隔≥1秒。**

### 第4步：下载新书封面图片

下载到 `C:\Users\lijin\Documents\book_covers_all\`，文件名按总序号递增。

**关键坑：img9.doubanio.com 反爬**，会返回HTML而非图片。解决方法：
```python
def download_image(url, filepath):
    fname = url.split('/')[-1]  # 如 s35355919.jpg
    for domain in ['img1.doubanio.com', 'img2.doubanio.com', 'img3.doubanio.com']:
        for size in ['l', 's']:
            try_url = f"https://{domain}/view/subject/{size}/public/{fname}"
            # 下载后验证文件头前2字节 == b'\xff\xd8'（JPEG）
            # 如果是 b'<scr' 开头 → 反爬HTML，换域名重试
```

### 第5步：对新书进行分类

根据书名+简介+作者+出版社的关键词综合判断，归入以下分类之一：

| 分类 | 典型关键词 |
|---|---|
| 文学·小说 | 小说、诗、散文、科幻、推理、漫画、绘本、文艺出版社 |
| 历史·传记 | 历史、传记、战争、革命、回忆录、年谱 |
| 哲学·思想 | 哲学、伦理、认知、存在、形而上、批判 |
| 心理·自助 | 心理、精神、情绪、焦虑、自我成长 |
| 社科·政治 | 社会、政治、经济、法律、阶级、文化研究 |
| 科技·科学 | AI、算法、物理、生物、数学、科普 |
| 艺术·设计 | 艺术、绘画、建筑、摄影、音乐、电影 |
| 经管·商业 | 管理、商业、投资、金融、营销、职场 |
| 其他 | 以上都不匹配 |

### 第6步：更新本地Excel

用Python openpyxl操作 `C:\Users\lijin\Documents\豆瓣新书速递.xlsx`：

**6.1 更新「新书速递」Sheet**
1. 在第2行插入N行空行（N=新书数量），原有数据下移
2. 写入新书：A列留空放图片、B列书名（外语书附原作名，格式 `中文名\n（原名）`）、C列作者（外语书附外文名，格式 `中文名\n（外文名）`，注意先检查是否已包含避免重复）、D列出版社、E列完整简介、F列豆瓣链接（超链接）、G列今天日期 YYYY-MM-DD
3. **关键：插入行后，已有图片的锚点不会自动更新**，必须遍历所有已有图片，将 `_from.row` 和 `to.row` 各加N
4. 嵌入书封图片（见下方代码）

**6.2 更新分类Sheets**
对每本新书，在对应分类Sheet末尾追加（A~F列，无G列）。分类Sheet不存在则新建。

**图片嵌入代码（核心，不可简化）**：
```python
from openpyxl.drawing.image import Image
from openpyxl.drawing.spreadsheet_drawing import TwoCellAnchor, AnchorMarker
from openpyxl.utils.units import pixels_to_EMU

MARGIN = pixels_to_EMU(4)
IMG_W, IMG_H = 70, 92

img = Image(img_path)
img.width = IMG_W
img.height = IMG_H
_from = AnchorMarker(col=0, colOff=MARGIN, row=row_idx-1, rowOff=MARGIN)
_to = AnchorMarker(col=0, colOff=pixels_to_EMU(IMG_W)+MARGIN, row=row_idx-1, rowOff=pixels_to_EMU(IMG_H)+MARGIN)
anchor = TwoCellAnchor(_from=_from, to=_to, editAs='oneCell')
img.anchor = anchor
ws.add_image(img)
```

**格式规范**：
- 列宽：A=11, B=35, C=28, D=20, E=70, F=38, G=14
- 行高：数据行80磅，表头28磅
- 字体：表头微软雅黑11号白色加粗(#FFFFFF)，数据微软雅黑9号，书名加粗
- 表头底色：各Sheet不同（新书速递#2F5496，文学·小说#C0504D，历史·传记#E36C09，哲学·思想#7030A0，心理·自助#00B050，社科·政治#0070C0，科技·科学#00B0F0，艺术·设计#FF6699，经管·商业#FFC000，其他#808080）
- 交替行色：偶数行#EDF2F9，奇数行白色
- 边框：薄边框#D0D0D0
- 超链接：Font(name='微软雅黑', size=9, color='0563C1', underline='single')
- 冻结首行：`ws.freeze_panes = 'A2'`

### 第7步：同步更新飞书多维表格

获取 tenant_access_token：
```python
url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
data = {"app_id": "你的APP_ID", "app_secret": "你的APP_SECRET"}
# POST请求，返回 tenant_access_token
```

如果不知道 app_id 和 app_secret，可以通过查看飞书MCP的node进程命令行参数获取：
```powershell
Get-CimInstance Win32_Process -Filter "Name='node.exe'" | Select-Object CommandLine | Format-List
# 找到包含 lark-mcp 的行，-a 后面是 app_id，-s 后面是 app_secret
# 注意：PowerShell输出可能会换行截断，需要将所有行合并为一个字符串后再用正则匹配
```

批量写入新书到多维表格：
```
POST https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_create
Authorization: Bearer {tenant_access_token}
Body: {"records": [{"fields": {"书名": "...", "作者": "...", ...}}, ...]}
```

app_token = `SoIsbtDeJaMZxIsVFvecV5iPnBj`，table_id = `tblDiuNtXVhlYAHR`

每批最多500条，间隔0.5秒。**注意：简介字段不要截断，完整写入。**

### 第8步：飞书群通知

向群 `oc_6c30c41fb7877b7b52439a587ba6c7e7` 发送消息。

**有新书时**，用 `mcp_lark-mcp_im_v1_message_create` 发送卡片消息（msg_type: interactive），内容包含：今日新增N本、按分类列出书名和作者（外语书附原名）、Excel文件位置、多维表格链接。

**无新书时**，发送文本消息：`📚 豆瓣新书速递 - {日期}检查完毕，暂无新书更新。`

### 第9步：更新JSON缓存

将新书数据（含 category、original_title、original_author 字段）追加到 `douban_books_data.json`。

### 第10步：清理临时文件

删除执行过程中产生的所有 .py 临时脚本。

---

## 附录A：首次全量抓取流程

当 `douban_books_data.json` 不存在时，需要执行全量抓取：

1. 抓取全部9页书籍列表（同第1步）
2. 逐一获取每本书的完整简介 + 外语书原名（同第3步，但对所有书执行）
3. 下载所有书封图片（同第4步）
4. 对所有书分类（同第5步）
5. 从零创建Excel（不是插入行，而是直接创建完整工作簿）
6. 创建飞书多维表格并批量写入（参考附录B）
7. 保存JSON缓存
8. 飞书群通知

**全量抓取约需15-20分钟**（主要是逐本访问详情页的等待时间）。

## 附录B：创建飞书多维表格

如果多维表格不存在或需要重建：

1. 调用 `mcp_lark-mcp_bitable_v1_app_create`，name = "豆瓣新书速递"
2. 调用 `mcp_lark-mcp_bitable_v1_appTable_create`，创建"新书速递"表，字段：
   - 书名（Text）、作者（Text）、出版社（Text）、内容简介（Text）、豆瓣链接（Url）、分类（SingleSelect，选项：文学·小说/历史·传记/哲学·思想/心理·自助/社科·政治/科技·科学/艺术·设计/经管·商业/其他）
3. 通过飞书API批量写入所有记录（每批100条，用 tenant_access_token 认证）
4. 记录新的 app_token 和 table_id，更新本prompt中的对应值

---

## 踩坑清单（每条都是血泪教训）

1. **img9.doubanio.com 反爬**：直接下载返回HTML，必须替换为 img1/img2/img3 域名
2. **openpyxl图片默认浮动**：用字符串锚点 `img.anchor = 'A2'` 图片不嵌入单元格，必须手动构造 `TwoCellAnchor` + `editAs='oneCell'`
3. **插入行后旧图片偏移**：openpyxl插入行不会自动更新已有图片锚点，必须手动将所有已有图片的 `_from.row` 和 `to.row` 加上插入行数
4. **豆瓣简介折叠**：详情页有两个 `div.intro`，第1个截断版，第2个完整版，要取第2个
5. **请求频率**：列表页间隔1.5秒、详情页间隔1秒，太快会403或验证码
6. **简介列宽度**：E列必须设70+，太窄行高会被撑到几百像素
7. **分类Sheet图片文件名**：用原始序号 `cover_{原始序号}.jpg`，不是分类内行号
8. **外语书作者名去重**：写入C列前检查作者字段是否已包含外文名，避免重复
9. **排除古籍作者**：`(元)(清)(宋)(明)(唐)` 等是中国古代作者标记，不是外语书
10. **飞书API认证**：批量写入多维表格需要 tenant_access_token，通过 app_id + app_secret 获取，这两个值可以从飞书MCP的node进程命令行参数中提取（注意PowerShell输出换行截断问题，需合并全文再正则匹配）
11. **飞书多维表格简介不要截断**：写入多维表格时不要对简介做 `[:2000]` 截断，飞书多行文本字段支持很长的内容，直接完整写入
12. **数据一致性**：JSON缓存、Excel、飞书多维表格三处的记录数必须一致，每次更新后都要验证
