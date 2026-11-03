# P4 启动提示词：C0-9000连续完整联合续训

2026-11-03发布。P3已完成，当前P4尚未启动。复制下面整段交给具有D57访问能力的Codex执行。

~~~text
读取 https://github.com/kaiwen123-yang/Supermimic 最新AGENTS.md、README.md、docs/REPRODUCTION_PLAN.md的P4、configs/next_stage_continuation_protocol.json，以及P3 summary/comparison。执行P4，不重复旧P3两组任务。

P3结果：C0保留辅助BCE，9000轮达到29/40、完整归一化回报0.615404、起身3/6；C1删除BCE只有15/40、0.482603。本轮保留有效C0，继续真实采样→WM→Actor/Critic完整联合训练，不再预设BCE有害。论文Eq.(1)没有要求BCE对预测状态detach；k8/H32是默认，9000轮且仍改善不是收敛证据。论文LAFAN回报0.82作参照，不承诺这轮必达，不盲跑320000轮。

使用autodl-d57现有项目 /root/autodl-tmp/robot-repro/supermimic，source activate.sh；必要时使用明确的独立源码工作树，不能放在待清理缓存中。保留原.venv、锁、激活脚本和G1资产，禁止安装/升级/重建/清理环境，不动其他项目或任务。

只恢复C0-9000完整checkpoint和既有LAFAN40 processed工作缓存，不取回全部历史、不重跑retarget：
父权重 https://github.com/kaiwen123-yang/Supermimic/releases/download/sm-20261102-h32-bce-s0-h32_aux_bce-i0009000/checkpoint_0009000.pt
动作数据 https://github.com/kaiwen123-yang/Supermimic/releases/download/sm-20261101-goal-feedback-s0-final/lafan40_working_data.tar.gz
它们原服务器副本已清理；若当前已有同一工作副本且仍在使用就直接复用，不重复下载。父版本9000已有完整评估，不再回放。

建立一个新run，建议campaign 20261103-c0-continuation-s0、run后缀h32_aux_bce。从C0实际配置继承，仅调整run/续训来源、max_iterations=18000、max_hours=12。保持robot_root、目标710维、H32、k8、aux_bce、analytic_smooth温度0.05、4096环境、原70维state mean、reward、物理终止、PD、随机化/噪声、sampler、网络、optimizer和250000轮全局LR日程。

恢复完整网络/优化器/sampler/Torch及CUDA RNG。新run只做一次64步replay预热，连续运行9001–18000，新增9000次联合更新，训练阶段最多12小时（含预热、旧累计耗时单列），最终评估/视频/上传收尾另计。按实测速率预计约9.7小时，共享GPU可能变化；到时的非整千节点也正常完整发布。单个Codex交互窗口≤4小时，使用独立tmux，窗口交接不停止/重启训练，不重建replay或重置LR，不为窗口交接重复请求启动授权。

先完成实际必要的单run入口/收尾适配，然后直接正式训练。旧run_tracking_continuation_d57.sh和finish_tracking_campaign.py固定B6000、C0/C1两组、7000起点和双组视频，不能原样运行P4。复用现成发布/渲染函数，不新建通用框架。publish已published早退不会自动升级final标志，需正确记录实际最终节点；最终汇总区别训练快照的full_clip_evaluation_done=false与后来已完成的评估。不要重做已完成的上传和评估。

每轮保存完整checkpoint，滚动保留最近20轮、父版本、全部1000轮节点和最终版本。每新增1000轮（10000–18000）全40动作评估并发布。使用原高度/倾斜终止和完整时长归一化分母，最终评分和视频用同一真实轨迹，不能缩短片段或拼接逐动作最佳checkpoint。报告6条起身、4条跑步、原11条失败和已有成功动作的保持；特别关注fallAndGetUp2_subject2早失败及米级位置漂移。已有训练统计继续记录，仅对实际最终失败的跑步/起身尾窗复用现有分析，不再做双模型全套对照。coverage不是论文成功率；训练MSE不能替代真实完整回报。

禁止防御性编程、单元/mock/冒烟/导入/形状/哈希测试、摘要重算、恢复演练、全盘扫描、通用fallback或监控框架、独立benchmark和机械起点扫描。遇到真实运行错误才定位并修复。不要自动开C1复跑、BCE权重/detach、H16、XYZ、乘70、PPO、多seed或数据扩展。

源码、配置、紧凑结果和现有单一索引推GitHub；权重、原始数组/轨迹、视频、大日志从D57直传Release，原始记录≤1GiB分卷，上传一次。不在我电脑做任何大产物镜像或归档。只确认Git推送成功、Release为uploaded、名称/字节数和下载URL；不哈希、不重下载核验。训练/评估/渲染/上传消费者结束后删除已上传的精确实验副本，阶段结束清理已发布保留产物和无消费者的输入副本；未上传项保留并报告。

永久保护源码、.git/stash、.venv、依赖锁、激活脚本、G1 XML/网格、工作树、恢复元数据、其他项目与共享依赖，禁止删除整个项目、outputs、.cache或work，不调用旧整体清理任务。

完成后更新现有计划、README、运行索引及P4协议状态，交付真实成绩/逐动作变化、更新量/耗时、尚未解释的问题、GitHub链接、实际删除路径/释放空间及未发布项。以实际趋势判断下一步，不自动追加新分支。
~~~
