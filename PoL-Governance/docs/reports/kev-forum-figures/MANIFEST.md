# 论坛图片清单

将本目录下的 PNG 上传到论坛（或图床）后，把帖子中的 data URI 图片替换为对应链接。
若论坛保留 data URI 图片，则无需上传。

## 1. fig-01-dataset.png

- 文件：fig-01-dataset.png
- 图注：图 1　数据集形态：左为输入文本长度（字符），右为每题的候选选项数（对数横轴）。

## 2. fig-02-accuracy.png

- 文件：fig-02-accuracy.png
- 图注：图 2　四个权重的准确率与 95% Wilson 置信区间（n=7,347）。

## 3. fig-03-forest.png

- 文件：fig-03-forest.png
- 图注：图 3　三个 seed 相对原版的变化（准确率、Brier、NLL），配对 cluster bootstrap 95% 区间。

## 4. fig-04-bootstrap.png

- 文件：fig-04-bootstrap.png
- 图注：图 4　seed-43 相对原版的配对 bootstrap 分布（准确率、Brier、NLL）。

## 5. fig-05-permutation.png

- 文件：fig-05-permutation.png
- 图注：图 5　置换检验：如果两个模型其实一样好，差值会落在灰色分布里；红线是实际观测值。

## 6. fig-06-kind-bars.png

- 文件：fig-06-kind-bars.png
- 图注：图 6　按题型分层的准确率（95% Wilson CI）。

## 7. fig-07-length-bars.png

- 文件：fig-07-length-bars.png
- 图注：图 7　按领域分层的准确率。

## 8. fig-08-domain-bars.png

- 文件：fig-08-domain-bars.png
- 图注：图 8　按输入长度分层的准确率（95% CI）。

## 9. fig-09-option-curve.png

- 文件：fig-09-option-curve.png
- 图注：图 9　准确率随选项数变化（对数式分桶，95% CI）。

## 10. fig-10-heatmap.png

- 文件：fig-10-heatmap.png
- 图注：图 10　seed-43 相对原版的准确率变化（百分点），按“题型 × 领域”切分。

## 11. fig-11-kind-brier.png

- 文件：fig-11-kind-brier.png
- 图注：图 11　按题型的概率误差（Brier，越低越好）。

## 12. fig-12-score-error-hist.png

- 文件：fig-12-score-error-hist.png
- 图注：图 12　打分题的绝对等级误差分布。

## 13. fig-13-sample-size.png

- 文件：fig-13-sample-size.png
- 图注：图 13　准确率置信区间半宽随题目数变化。

## 14. fig-14-reliability.png

- 文件：fig-14-reliability.png
- 图注：图 14　可靠性图：横轴为预测置信度，纵轴为实际正确率；虚线为完美校准。

## 15. fig-15-noul-reliability.png

- 文件：fig-15-noul-reliability.png
- 图注：图 15　是/否题的二元校准：预测“是”的概率 vs 实际“是”的比例。

## 16. fig-16-brier-decomp.png

- 文件：fig-16-brier-decomp.png
- 图注：图 16　Brier 分解（是/否题）：reliability（校准误差，越低越好）与 resolution（区分能力，越高越好）。

## 17. fig-17-risk-coverage.png

- 文件：fig-17-risk-coverage.png
- 图注：图 17　风险-覆盖曲线：覆盖率越高，错误率越高；红色虚线为 5% 错误预算。

## 18. fig-18-confidence-deciles.png

- 文件：fig-18-confidence-deciles.png
- 图注：图 18　按置信度十分位看准确率与平均置信度。

## 19. fig-19-variant-ecdf.png

- 文件：fig-19-variant-ecdf.png
- 图注：图 19　两类扰动的累积分布：横轴为同题最大概率变化，纵轴为不超过该变化的题目比例。

## 20. fig-20-jev-radar.png

- 文件：fig-20-jev-radar.png
- 图注：图 20　JevBench 五个维度的本地结果与官方 Kev-4B 公布值。

## 21. fig-21-jev-leaderboard.png

- 文件：fig-21-jev-leaderboard.png
- 图注：图 21　公开 JevBench 榜（点）与我们的两次本地复跑（虚线）。

## 22. fig-22-latency.png

- 文件：fig-22-latency.png
- 图注：图 22　每道题的 GPU 延迟（对数纵轴；实心为 median，半透明为 p95）。
