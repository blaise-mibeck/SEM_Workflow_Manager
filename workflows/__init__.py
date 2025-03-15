"""
Workflow modules for SEM Image Workflow Manager.
"""

# Import workflows to expose them at package level
from workflows.mag_grid import MagGridWorkflow
from workflows.compare_grid import CompareGridWorkflow

# Define available workflows
available_workflows = [
    "MagGridWorkflow",
    "CompareGridWorkflow"
]
