from .p1m1_p2m2 import Matcher1Matcher2Workflow
from .p1m1c1_p2m2c2 import Matcher1Critic1Matcher2Critic2SequentialWorkflow
from .p1m1c1m2c2 import Matcher1Critic1Matcher2Critic2Workflow
from .p1m1m2c import Matcher1CriticMatcher2Workflow
from .workflow import WorkflowConfig


async def run_workflow(**kwargs):
    """Run the appropriate workflow based on configuration."""
    config = WorkflowConfig(**kwargs)
    workflow_map = {
        "p1m1m2c": Matcher1CriticMatcher2Workflow,
        "p1m1c1m2c2": Matcher1Critic1Matcher2Critic2Workflow,
        "p1m1c1_p2m2c2": Matcher1Critic1Matcher2Critic2SequentialWorkflow,
        "p1m1_p2m2": Matcher1Matcher2Workflow,
    }
    workflow_class = workflow_map.get(config.configuration)
    if not workflow_class:
        raise ValueError(f"Unknown configuration: {config.configuration}")
    workflow = workflow_class(config)
    await workflow.run()


__all__ = ["run_workflow"]
