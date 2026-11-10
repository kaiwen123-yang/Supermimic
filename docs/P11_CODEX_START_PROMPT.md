# P11 正在运行：下一窗口接续

核实时间：2026-11-10T11:23:31.198241+08:00。两路已从P10 hard27000完整恢复并执行真实联合更新。P10已完成，不重复启动。

服务器autodl-d57；工作树/root/autodl-tmp/robot-repro/supermimic-p11-root-height-consistency；source activate.sh。

先读取AGENTS.md、P11计划/协议和campaign summary，再读取现有tmux及run下budget.json、metrics.jsonl。保留当前活跃进程、replay和LR。

| job | tmux | 观察iteration | 新增联合更新 | 新阶段秒 |
|---|---|---:|---:|---:|
| full8k_residual_control | sm-p11-residual | 27015 | 15 | 84.518 |
| full8k_velocity_height | sm-p11-velocity-height | 27008 | 8 | 44.889 |

运行目录：outputs/runs/20261110-p11-root-height-consistency-s0-<job>；日志outputs/campaigns/<run>.train.log。表中为带时间快照。

两路8192真实/8192想象/WM10×4096，k8/H32、原12.5%hard reset配额与其他配方保持。唯一变量world_root_height_mode=residual或velocity_trapezoid。后者z_next=z+.01*(vz+predicted_vz_next)，下一vz来自同次WM。

每路27001–36000或累计新阶段20h先到。已各填充一次64步replay；不因交接重新填充或重新获得预算。仅真实进程退出才按该run最新checkpoint与--resume-in-place继续。

全BONES和LAFAN共同节点30000/33000/36000及实际终点。复用父27000评分；原1024长度排序评分、完整逐clip CSV、同次尾窗保持。训练脚本自动请求publish_p11，结束后run脚本自动调用finish_p11。

父固定七窗已完成7条/224预测步：evidence/parent_hard27000。终点各WM只对相同输入再做一次，总21条/672步。不要重跑父证据、新物理或扫描起点。候选残差为零不算成功；比较真实预测误差、控制、保持。

GPU证据/评分/Git发布共用P6 work/p2-publication.lock，总并发1；训练不持锁。每训练/评分Torch2线程，两路8k，不增加第三learner。正常节点记录cgroup anon/file/inactive_file及GPU占用。

LAFAN达到0.82的既有复现成功保持。预算结束如实评分发布，不延长、安装升级、测试/benchmark、Release、tar、本地归档、自动阶段清理或开P12。大产物留服务器，用户备份未确认。
