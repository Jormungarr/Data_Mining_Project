# 探索脚本（历史存档）

⚠️ **这些脚本不参与主管道，且大部分已无法直接运行。** 保留它们是为了留下
方案筛选过程的证据链。

## 为什么不能直接运行

探索阶段的数据目录结构是扁平的：

```
data/f1_traffic/  data/f1_aqhi/  data/f3_flu/  data/ha_extra/  ...
```

管道定稿后重整为：

```
data/raw/  data/processed/  data/_exploratory/
```

因此脚本里写死的路径（如 `data/f3_flu/flux_data.csv`）已不存在。
若需要重跑某个探索脚本，先把对应的原始文件从 `data/_exploratory/` 复制到它期望的位置。

## 这些脚本各自做了什么

方案可行性核查阶段（对应 `REPORT.md`）：

| 脚本 | 用途 |
| --- | --- |
| `00`–`11` | 用 data.gov.hk 的 CKAN API 定位数据集、探查字段与粒度 |
| `12` | 批量下载三个候选方案的全部候选数据集 |
| `13` | 探查 HA 每日服务量 JSON 的结构 |
| `20_test_f1.py` | **方案一实测**：证明车程时间只有年度粒度，无法与逐小时 AQHI 对齐 |
| `21_test_f2.py` | **方案二实测**：证明食肆牌照 XML 无发牌日期；历史存档 API 返回 0 个版本 |
| `22_test_f3.py` | **方案三实测**：证明死亡统计缺少「周 × 65+ × 呼吸系统疾病」切片 |
| `23_alt.py` `24_alt2.py` | 核查方案一的替代数据源（月度交通摘要、即时车程指标等） |

方案三深化阶段（对应 `PROPOSAL3.md`）：

| 脚本 | 用途 |
| --- | --- |
| `30_ha_full.py` | HA 数据集完整结构剖析（8 个季节窗口、928 天、非连续） |
| `31_ha_panel.py` | 构建逐周与逐医院面板的初步探索 |
| `32_tradeoff.py` | 量化「月度 vs 逐周」的样本量与波解析度取舍 |
| `40_build_master.py` | 初版主表构建（已被 `pipeline/02_build.py` 取代） |
| `41_verify.py` | 初版验证（已被 `pipeline/03_validate.py` 取代） |
| `42_fetch_hko.py` | 首次抓取天文台气温（已被 `pipeline/01_download.py` 吸收） |

## 需要复现请用主管道

```bash
./pipeline/run_all.sh
```

见项目根目录的 [`README.md`](../../README.md)。
