# Mock Data Scripts

## load_mock_data.sql

在 TablePlus 中导入 mock 数据到 PostgreSQL 数据库。

### 使用方法

1. 用 TablePlus 连接到 `pharmacy_db`（host: localhost, port: 5432, user: pharmacy_user, password: pharmacy_pass）
2. 如果数据库中已有数据且可能和 mock 数据冲突，先执行脚本顶部的 DELETE 块（取消注释）
3. 打开 `load_mock_data.sql`，全选并执行

### 数据内容

- **5 个 Patient**：Jane Smith, John Doe, Maria Garcia, Robert Johnson, Emily Chen（MRN: 100001–100005）
- **3 个 Provider**：Dr. Sarah Williams, Dr. Michael Brown, Dr. Lisa Anderson（NPI: 10 位）
- **5 个 CarePlan**：均为 `status='completed'`，含 `generated_content`，可用于测试搜索、导出、下载
