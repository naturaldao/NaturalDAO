# smoke：冒烟与离线联调产物

- **luna-limit5/**：唯一一次真实付费冒烟（Luna gpt-6-luna，--limit 5 → 3 组最小对立对 6 条 case）。
  含 train.cases.jsonl / train.questions.jsonl、qa/families.jsonl、calls.jsonl（token 与延迟）、
  errors/（首次 403 Cloudflare 1010 的记录）、run.json。真实生成数据，可用于结构检查。
- **fixture-e2e/**：--fixture 离线合成数据跑完 generate → teacher（两个 fixture 来源）→ adjudicate。
  **全部是合成数据，不是真值，不得用于训练或评测**；只用于演示与回归。

两者都不含 private_holdout 内容、密钥或原始凭据；分配表只在仓库外被读取。
