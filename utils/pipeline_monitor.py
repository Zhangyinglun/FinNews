import time
from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class ModuleStatus:
    """单个模块或数据源的状态"""

    name: str
    status: str = "PENDING"  # PENDING, SUCCESS, FAILED, WARNING
    error: Optional[str] = None
    count: Optional[int] = None
    duration: float = 0.0


@dataclass
class StepStatus:
    """执行步骤(如：数据采集、数据处理)"""

    name: str
    modules: List[ModuleStatus] = field(default_factory=list)


class PipelineMonitor:
    """管道监控器 - 负责整理日志、统计成功率和汇总错误"""

    def __init__(self):
        self.steps: List[StepStatus] = []
        self.current_step: Optional[StepStatus] = None
        self.start_time = time.time()

    def start_step(self, name: str):
        """开启一个新步骤"""
        step = StepStatus(name=name)
        self.steps.append(step)
        self.current_step = step

    def report_module(
        self,
        name: str,
        success: bool,
        error: Optional[str] = None,
        count: Optional[int] = None,
        duration: float = 0.0,
        warning: bool = False,
    ):
        """报告模块运行状态"""
        if not self.current_step:
            self.start_step("默认步骤")

        status = "SUCCESS" if success else "FAILED"
        if success and warning:
            status = "WARNING"

        module = ModuleStatus(
            name=name, status=status, error=error, count=count, duration=duration
        )
        self.current_step.modules.append(module)

    def get_summary(self) -> str:
        """生成结构化总结报告"""
        lines = ["\n" + "=" * 60, "📊 FinNews 管道执行总结", "=" * 60]
        total_modules = 0
        success_count = 0
        errors = []

        for step in self.steps:
            lines.append(f"\n步骤: {step.name}")
            for m in step.modules:
                total_modules += 1
                if m.status in ("SUCCESS", "WARNING"):
                    success_count += 1

                status_icon = (
                    "✅"
                    if m.status == "SUCCESS"
                    else "⚠️" if m.status == "WARNING" else "❌"
                )
                count_str = f" ({m.count} 条记录)" if m.count is not None else ""
                lines.append(
                    f"  {status_icon} {m.name:.<35} {m.status}{count_str} [{m.duration:.2f}s]"
                )

                if m.error:
                    errors.append((m.name, m.error))

        lines.append("\n" + "-" * 60)
        success_rate = (success_count / total_modules * 100) if total_modules > 0 else 0
        lines.append(
            f"运行概览: 总计 {total_modules} 模块 | 成功: {success_count} | 失败: {total_modules - success_count}"
        )
        lines.append(f"总成功率: {success_rate:.1f}%")
        lines.append(f"总耗时: {time.time() - self.start_time:.2f}s")

        if errors:
            lines.append("\n集中错误列表:")
            for name, err in errors:
                # 截断过长的错误信息
                short_err = str(err)[:100] + "..." if len(str(err)) > 100 else str(err)
                lines.append(f"  [{name}]: {short_err}")

        lines.append("=" * 60)
        return "\n".join(lines)
