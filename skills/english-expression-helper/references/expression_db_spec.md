# 表达记录存储规范

## 文件路径

```
~/openclaw-data/english/
├── expressions_2026-03.csv     # 按月存储
├── expressions_2026-04.csv
├── summaries/
│   ├── daily_2026-03-01.md     # 每日汇总
│   └── daily_2026-03-02.md
└── ...
```

按月分文件存储，避免单文件过大。

## CSV 格式

- 编码：UTF-8 with BOM（确保 Excel 正常打开中文）
- 分隔符：逗号
- 首行：字段名 header
- 若字段值含逗号，用双引号包裹

### Header 行

```
id,date,username,query,expression,phonetic,pos,example_sentence,context,tags
```

### 示例数据行

```
a1b2c3d4,2026-03-01,john_doe,故意冷落别人怎么说,cold shoulder,"/koʊld ˈʃoʊl.dɚ/",phrase,"She gave me the cold shoulder after the argument.",日常口语非正式,"社交,情绪"
a5b6c7d8,2026-03-01,john_doe,拖延怎么说,procrastinate,"/prəˈkræs.tɪ.neɪt/",verb,"Stop procrastinating and start working on your project.",日常通用,"习惯,时间管理"
```

## 去重规则

唯一键：`date + username + expression`（同一天同一用户对同一表达不重复记录）

## write_expression.py 调用规范

```bash
python3 scripts/write_expression.py \
  --records-file /tmp/expression_records.json \
  --data-dir ~/openclaw-data/english/
```

脚本逻辑：

1. 根据记录中的 date 判断写入哪个月份文件
2. 若文件不存在，先写入 header 行
3. 追加写入新记录（去重：若 date+username+expression 已存在则跳过，`--overwrite` 可覆盖）
4. 自动生成 UUID 作为 id（若未提供）
5. 返回写入成功的记录数
