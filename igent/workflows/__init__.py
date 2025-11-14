from .configurable_workflow import ConfigurableWorkflow
from .p1m1_p2m2 import Matcher1Matcher2Workflow
from .p1m1c1_p2m2c2 import Matcher1Critic1Matcher2Critic2SequentialWorkflow
from .p1m1c1m2c2 import Matcher1Critic1Matcher2Critic2Workflow
from .p1m1m2c import Matcher1CriticMatcher2Workflow
from .workflow import WorkflowConfig


async def run_workflow(**kwargs):
    """Run workflow using the unified ConfigurableWorkflow (recommended).

    This function now uses the new configuration-driven approach via YAML
    constellation files. The old workflow classes are deprecated but still
    available for backward compatibility.

    Args:
        constellation: Workflow constellation name (e.g., "p1m1m2c")
        model: Model name (e.g., "zai_glm4_5_air", "openai_gpt4o")
        stream: Whether to stream responses
        business_line: Business line (default: "sbus")
        registrations_file: Path to registrations JSON
        offers_file: Path to offers JSON
        incentives_file: Optional path to incentives JSON
        matches_file: Path to output matches JSON
        pos_file: Path to output POS JSON
        stats_file: Path to output stats CSV
        max_items: Maximum number of registrations to process

    Example:
        >>> await run_workflow(
        ...     constellation="p1m1m2c",
        ...     model="zai_glm4_5_air",
        ...     registrations_file="data/sbus/registrations/full_dataset.json",
        ...     offers_file="data/sbus/offers/base_offers.json",
        ...     max_items=10
        ... )
    """
    config = WorkflowConfig(**kwargs)

    # Use new ConfigurableWorkflow
    workflow = ConfigurableWorkflow(config)
    await workflow.run()


__all__ = [
    "run_workflow",
    "ConfigurableWorkflow",
    "WorkflowConfig",
    # Old classes (deprecated, kept for backward compatibility)
    "Matcher1CriticMatcher2Workflow",
    "Matcher1Critic1Matcher2Critic2Workflow",
    "Matcher1Critic1Matcher2Critic2SequentialWorkflow",
    "Matcher1Matcher2Workflow",
]
