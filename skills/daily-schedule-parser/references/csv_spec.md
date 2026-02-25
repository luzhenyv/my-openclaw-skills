# CSV 存储规范

## 文件路径

```
~/openclaw-data/schedules/
├── schedule_2026-02.csv       # 按月存储
├── schedule_2026-03.csv
└── ...
```

按月分文件存储，避免单文件过大。

## CSV 格式

- 编码：UTF-8 with BOM（确保 Excel 正常打开中文）
- 分隔符：逗号
- 首行：字段名 header
- 时间格式：HH:MM（24小时制）
- 若字段值含逗号，用双引号包裹

### Header 行

```
date,username,start_time,end_time,duration_min,category,sub_category,content,reflection,tags
```

### 示例数据行

```
2026-02-25,john_doe,08:54,09:35,41,生活,起床准备,起床后准备上班，收拾个人物品,,起床
2026-02-25,john_doe,09:35,10:40,65,通勤,上班通勤,从家出发乘地铁前往公司,,通勤,地铁
2026-02-25,john_doe,10:40,12:30,110,工作,写作,"查看同事离职信件，撰写年度工作计划，下载《The First Principle the First View》一书",,年度计划,离职信,读书
```

## write_csv.py 调用规范

```python
# 输入：records（list of dict），csv_dir（目标目录）
# 输出：写入对应月份 CSV，若文件不存在则创建并写入 header

python scripts/write_csv.py \
  --records '[{"date":"2026-02-25","username":"john_doe",...}]' \
  --data-dir ~/openclaw-data/schedules/
```

脚本逻辑：

1. 根据记录中的 date 判断写入哪个月份文件
2. 若文件不存在，先写入 header 行
3. 追加写入新记录（避免重复：若 date+username+start_time 已存在则跳过或覆盖，可通过 `--overwrite` 参数控制）
4. 返回写入成功的记录数
