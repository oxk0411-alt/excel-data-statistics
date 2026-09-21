# 表格清洗、统计与可视化

这是一个可直接在 VSCode 中运行的 Python 工具，用于读取、清洗、统计和分析 CSV/Excel 表格。

程序基于以下成熟依赖构建：

- pandas：表格读取、清洗、统计和导出
- openpyxl / xlrd：支持 `.xlsx` 和旧版 `.xls`
- Streamlit：本地交互界面
- Plotly：交互式图表

## 功能

- 上传或读取 CSV、XLSX、XLS
- 自动尝试 UTF-8、UTF-8 BOM、GB18030、GBK、Big5 等常见编码
- 读取多工作表 Excel
- 数据概览：行数、字段数、缺失率、重复行、内存占用
- 字段质量画像：类型、缺失数、唯一值、示例值
- 清洗规则：
  - 规范化列名
  - 删除文本首尾空白
  - 删除全空行、全空列
  - 删除重复行
  - 自动识别数值和日期字段
  - 保留、删除或填充缺失值
  - 均值、中位数、众数、固定值填充
- 统计：
  - 数值字段描述统计、中位数、偏度
  - 文本和分类字段频数统计
  - Pearson、Spearman、Kendall 相关性
  - 分组计数和分组聚合
- 可视化：
  - 缺失值条形图
  - 直方图
  - 箱线图
  - 分类计数图
  - 折线图
  - 散点图
  - 相关性热力图
- 导出清洗后的 CSV 或 Excel
- 默认启用公式注入防护：导出时会处理以 `=`、`+`、`-`、`@` 开头的文本

## 在 VSCode 中运行

1. 在 VSCode 中打开本目录：

   ```text
   outputs/table_cleaner
   ```

2. 打开终端并执行：

   ```powershell
   .\setup.ps1
   ```

3. 选择 Python 解释器：

   ```text
   .\.venv\Scripts\python.exe
   ```

4. 按 `F5`，选择 `Streamlit: 启动应用`。

也可以直接运行：

```powershell
.\run_app.ps1
```

浏览器会自动打开 `http://localhost:8501`。

## 手动安装

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## 运行测试

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## 项目结构

```text
table_cleaner/
├── app.py
├── table_cleaner/
│   ├── cleaning.py
│   ├── export.py
│   ├── io_utils.py
│   ├── statistics.py
│   └── visualization.py
├── tests/
├── data/
│   └── messy_sales.csv
├── .vscode/
│   ├── extensions.json
│   ├── launch.json
│   ├── settings.json
│   └── tasks.json
├── requirements.txt
├── pyproject.toml
├── setup.ps1
└── run_app.ps1
```

## 使用说明

未上传文件时，程序自动使用 `data/messy_sales.csv` 演示数据。

上传文件后：

1. 在“数据概览”检查字段质量和缺失情况。
2. 在“数据清洗”配置规则并点击“应用清洗”。
3. 在侧边栏选择使用原始数据或清洗后数据。
4. 在“统计分析”和“可视化”中分析数据。
5. 在“导出”下载 CSV 或 Excel。

## 安全与限制

- 数据默认只在本机处理，不会主动上传到外部服务器。
- 导出时建议保持“防止 CSV/Excel 公式注入”开启，尤其是在文件会交给其他人打开时。
- 自动类型转换可能会把不规范的数值转为缺失值；如字段值包含“元”“件”等单位，建议先做文本替换。
- 自动填充只适合基础场景。ID、手机号、日期等字段不应随意使用均值或众数填充。
- 程序会把整个表格加载到内存，超大文件需要改用分块读取或数据库方案。
- `xlrd` 只负责读取旧版 `.xls`；`.xlsx` 使用 `openpyxl`。

## 可扩展方向

- 增加规则配置文件和批处理模式
- 增加敏感字段脱敏
- 增加异常值检测
- 增加 Excel 多工作表批量处理
- 增加 PDF 或 HTML 分析报告
- 增加数据库读取，例如 SQLite、PostgreSQL

## 在线部署

本项目已经准备好部署到 Streamlit Community Cloud。详细步骤见 [DEPLOYMENT.md](DEPLOYMENT.md)。

云端入口文件：

```text
app.py
```

依赖清单：

```text
requirements.txt
```
