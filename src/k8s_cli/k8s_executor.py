import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import kr8s
from kr8s.objects import Job

from k8s_cli.task_models import TaskDefinition, TaskStatus


class KubernetesTaskExecutor:
    """Executes tasks on Kubernetes using kr8s"""

    def __init__(self):
        self.api = kr8s.api()
        self.namespace = "default"
        self.task_label = "skypilot-task"

    async def submit_task(self, task_def: TaskDefinition, username: str) -> str:
        """Submit a task to Kubernetes and return task ID"""
        task_id = str(uuid.uuid4())[:8]
        task_name = task_def.name or f"task-{task_id}"

        # Build container spec
        container_spec = {
            "name": "task",
            "image": self._get_image(task_def),
            "command": ["/bin/bash", "-c"],
            "args": [self._build_command(task_def)],
        }

        # Add resource requests/limits
        if task_def.resources:
            container_spec["resources"] = self._build_resources(task_def.resources)

        # Add environment variables
        if task_def.envs:
            container_spec["env"] = [
                {"name": k, "value": v} for k, v in task_def.envs.items()
            ]

        # Create Job specification
        job_spec = {
            "apiVersion": "batch/v1",
            "kind": "Job",
            "metadata": {
                "name": f"{task_name}-{task_id}",
                "namespace": self.namespace,
                "labels": {
                    self.task_label: "true",
                    "task-id": task_id,
                    "task-name": task_name,
                    "username": username,
                },
                "annotations": {
                    "created-at": datetime.utcnow().isoformat(),
                },
            },
            "spec": {
                "backoffLimit": 0,
                "template": {
                    "metadata": {
                        "labels": {
                            self.task_label: "true",
                            "task-id": task_id,
                            "username": username,
                        }
                    },
                    "spec": {
                        "restartPolicy": "Never",
                        "containers": [container_spec],
                    },
                },
            },
        }

        # Create the job
        job = Job(job_spec)
        await job.create()

        return task_id

    async def stop_task(self, task_id: str, username: str) -> bool:
        """Stop a running task"""
        jobs = list(
            self.api.get(
                "jobs", namespace=self.namespace, label_selector=f"task-id={task_id},username={username}"
            )
        )

        if not jobs:
            return False

        for job in jobs:
            await job.delete(propagation_policy="Background")

        return True

    async def list_tasks(self, username: str) -> List[TaskStatus]:
        """List all tasks for a specific user"""
        jobs = list(
            self.api.get(
                "jobs",
                namespace=self.namespace,
                label_selector=f"{self.task_label}=true,username={username}",
            )
        )

        tasks = []
        for job in jobs:
            task_status = await self._get_task_status(job)
            tasks.append(task_status)

        return tasks

    async def get_task_status(self, task_id: str, username: str) -> Optional[TaskStatus]:
        """Get status of a specific task for a specific user"""
        jobs = list(
            self.api.get(
                "jobs", namespace=self.namespace, label_selector=f"task-id={task_id},username={username}"
            )
        )

        if not jobs:
            return None

        return await self._get_task_status(jobs[0])

    async def _get_task_status(self, job: Job) -> TaskStatus:
        """Convert Job object to TaskStatus"""
        metadata = job.raw.get("metadata", {})
        status = job.raw.get("status", {})
        labels = metadata.get("labels", {})
        annotations = metadata.get("annotations", {})

        task_id = labels.get("task-id", "unknown")
        task_name = labels.get("task-name")
        created_at = annotations.get("created-at", "")

        # Determine status
        if status.get("succeeded", 0) > 0:
            task_status = "completed"
        elif status.get("failed", 0) > 0:
            task_status = "failed"
        elif status.get("active", 0) > 0:
            task_status = "running"
        else:
            task_status = "pending"

        return TaskStatus(
            task_id=task_id,
            name=task_name,
            status=task_status,
            created_at=created_at,
            updated_at=datetime.utcnow().isoformat(),
            metadata={
                "job_name": metadata.get("name"),
                "namespace": metadata.get("namespace"),
            },
        )

    def _get_image(self, task_def: TaskDefinition) -> str:
        """Get container image for task"""
        if task_def.resources and task_def.resources.image_id:
            return task_def.resources.image_id
        return "python:3.13-slim"

    def _build_command(self, task_def: TaskDefinition) -> str:
        """Build command to run in container"""
        commands = []

        # Change to workdir if specified
        if task_def.workdir:
            commands.append(f"cd {task_def.workdir}")

        # Run setup commands
        if task_def.setup:
            commands.append(task_def.setup)

        # Run main command
        commands.append(task_def.run)

        return " && ".join(commands)

    def _build_resources(self, resources) -> Dict[str, Any]:
        """Build Kubernetes resource requests/limits"""
        resource_spec = {"requests": {}, "limits": {}}

        if resources.cpus:
            resource_spec["requests"]["cpu"] = resources.cpus
            resource_spec["limits"]["cpu"] = resources.cpus

        if resources.memory:
            resource_spec["requests"]["memory"] = resources.memory
            resource_spec["limits"]["memory"] = resources.memory

        # Handle GPU requests
        if resources.accelerators:
            # Parse format like "V100:1" or "1"
            parts = resources.accelerators.split(":")
            gpu_count = parts[-1]
            resource_spec["limits"]["nvidia.com/gpu"] = gpu_count

        return resource_spec
