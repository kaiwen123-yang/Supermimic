# O3 官方 BONES 稳定性对照

状态：**plan_published_not_started**。本次仅发布 O2 复核与 O3 方案，O3 必要适配及服务器运行尚未开始。

两路同 O2 3h 权重热启动，三网络及 normalizer 继承；optimizer、replay、sampler、RNG 新建，full_resume=false。单卡各4096环境，BONES-only 130394条。control固定LR2e-4，quarter固定LR5e-5，其他官方算法相同。

各新增32000联合更新；整个campaign共享一个8h训练墙钟期限。保存+8k/+16k/+32k和实际final，两个训练子进程退出后串行完成所有实际节点的BONES及LAFAN跨库评分。当前没有新成绩。

- [O2复核](../../docs/O2_REVIEW_20261112.md)
- [O3实施方案](../../docs/O3_OFFICIAL_BONES_STABILITY_PLAN.md)
- [固定协议](../../configs/o3_official_bones_stability_protocol.json)
- [Codex启动词](../../docs/O3_CODEX_START_PROMPT.md)

O2 3h R=.93501955、130215/130394完整继续作为质量锚点；6h保留为困难覆盖参照。O1/P6成功结论保留，P12暂缓。大产物留服务器，不自动归档、阶段清理或启动O4。

