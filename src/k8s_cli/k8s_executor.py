import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import kr8s
from kr8s.objects import Job, PersistentVolumeClaim

from k8s_cli.task_models import TaskDefinition, TaskStatus, VolumeDefinition, VolumeStatus


class KubernetesTaskExecutor:
    """Executes tasks on Kubernetes using kr8s"""

    def __init__(self):
        self.api = kr8s.api()
        self.namespace = "default"
        self.task_label = "skypilot-task"
        self.volume_label = "skypilot-volume"

    def _sanitize_username(self, username: str) -> str:
        """Sanitize username for use in Kubernetes labels.

        Replaces characters not allowed in DNS-1123 subdomain labels:
        - '@' becomes '-'

        Example: first.last@domain.com -> first.last-domain.com
        """
        return username.replace("@", "-")

    def submit_task(self, task_def: TaskDefinition, username: str) -> str:
        """Submit a task to Kubernetes and return task ID"""
        task_id = str(uuid.uuid4())[:8]
        task_name = task_def.name or f"task-{task_id}"
        sanitized_username = self._sanitize_username(username)

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
                    "username": sanitized_username,
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
                            "username": sanitized_username,
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
        job.create()

        return task_id

    def stop_task(self, task_id: str, username: str) -> bool:
        """Stop a running task"""
        sanitized_username = self._sanitize_username(username)
        jobs = list(
            self.api.get(
                "jobs", namespace=self.namespace, label_selector=f"task-id={task_id},username={sanitized_username}"
            )
        )

        if not jobs:
            return False

        for job in jobs:
            job.delete(propagation_policy="Background")

        return True

    def stop_all_tasks(self, username: Optional[str] = None) -> int:
        """Stop all tasks for a user or all users if username is None

        Returns the number of tasks stopped
        """
        if username:
            sanitized_username = self._sanitize_username(username)
            label_selector = f"{self.task_label}=true,username={sanitized_username}"
        else:
            label_selector = f"{self.task_label}=true"

        jobs = list(
            self.api.get(
                "jobs",
                namespace=self.namespace,
                label_selector=label_selector,
            )
        )

        count = 0
        for job in jobs:
            job.delete(propagation_policy="Background")
            count += 1

        return count

    def list_tasks(self, username: Optional[str] = None) -> List[TaskStatus]:
        """List all tasks for a specific user or all users if username is None"""
        if username:
            sanitized_username = self._sanitize_username(username)
            label_selector = f"{self.task_label}=true,username={sanitized_username}"
        else:
            label_selector = f"{self.task_label}=true"

        jobs = list(
            self.api.get(
                "jobs",
                namespace=self.namespace,
                label_selector=label_selector,
            )
        )

        tasks = []
        for job in jobs:
            task_status = self._get_task_status(job)
            tasks.append(task_status)

        return tasks

    def get_task_status(self, task_id: str, username: str) -> Optional[TaskStatus]:
        """Get status of a specific task for a specific user"""
        sanitized_username = self._sanitize_username(username)
        jobs = list(
            self.api.get(
                "jobs", namespace=self.namespace, label_selector=f"task-id={task_id},username={sanitized_username}"
            )
        )

        if not jobs:
            return None

        return self._get_task_status(jobs[0])

    def _get_task_status(self, job: Job) -> TaskStatus:
        """Convert Job object to TaskStatus"""
        metadata = job.raw.get("metadata", {})
        status = job.raw.get("status", {})
        labels = metadata.get("labels", {})
        annotations = metadata.get("annotations", {})

        task_id = labels.get("task-id", "unknown")
        task_name = labels.get("task-name")
        username = labels.get("username")
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
            username=username,
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

    def create_volume(self, volume_def: VolumeDefinition, username: str) -> str:
        """Create a PersistentVolumeClaim and return volume ID"""
        volume_id = str(uuid.uuid4())[:8]
        pvc_name = f"{volume_def.name}-{volume_id}"
        sanitized_username = self._sanitize_username(username)

        pvc_spec = {
            "apiVersion": "v1",
            "kind": "PersistentVolumeClaim",
            "metadata": {
                "name": pvc_name,
                "namespace": self.namespace,
                "labels": {
                    self.volume_label: "true",
                    "volume-id": volume_id,
                    "volume-name": volume_def.name,
                    "username": sanitized_username,
                },
                "annotations": {
                    "created-at": datetime.utcnow().isoformat(),
                },
            },
            "spec": {
                "accessModes": volume_def.access_modes,
                "resources": {
                    "requests": {
                        "storage": volume_def.size,
                    }
                },
            },
        }

        if volume_def.storage_class:
            pvc_spec["spec"]["storageClassName"] = volume_def.storage_class

        pvc = PersistentVolumeClaim(pvc_spec)
        pvc.create()

        return volume_id

    def delete_volume(self, volume_id: str, username: str) -> bool:
        """Delete a PersistentVolumeClaim"""
        sanitized_username = self._sanitize_username(username)
        pvcs = list(
            self.api.get(
                "persistentvolumeclaims",
                namespace=self.namespace,
                label_selector=f"volume-id={volume_id},username={sanitized_username}",
            )
        )

        if not pvcs:
            return False

        for pvc in pvcs:
            pvc.delete()

        return True

    def list_volumes(self, username: Optional[str] = None) -> List[VolumeStatus]:
        """List all volumes for a specific user or all users if username is None"""
        if username:
            sanitized_username = self._sanitize_username(username)
            label_selector = f"{self.volume_label}=true,username={sanitized_username}"
        else:
            label_selector = f"{self.volume_label}=true"

        pvcs = list(
            self.api.get(
                "persistentvolumeclaims",
                namespace=self.namespace,
                label_selector=label_selector,
            )
        )

        volumes = []
        for pvc in pvcs:
            volume_status = self._get_volume_status(pvc)
            volumes.append(volume_status)

        return volumes

    def get_volume_status(self, volume_id: str, username: str) -> Optional[VolumeStatus]:
        """Get status of a specific volume for a specific user"""
        sanitized_username = self._sanitize_username(username)
        pvcs = list(
            self.api.get(
                "persistentvolumeclaims",
                namespace=self.namespace,
                label_selector=f"volume-id={volume_id},username={sanitized_username}",
            )
        )

        if not pvcs:
            return None

        return self._get_volume_status(pvcs[0])

    def _get_volume_status(self, pvc: PersistentVolumeClaim) -> VolumeStatus:
        """Convert PVC object to VolumeStatus"""
        metadata = pvc.raw.get("metadata", {})
        spec = pvc.raw.get("spec", {})
        status = pvc.raw.get("status", {})
        labels = metadata.get("labels", {})
        annotations = metadata.get("annotations", {})

        volume_id = labels.get("volume-id", "unknown")
        volume_name = labels.get("volume-name")
        username = labels.get("username")
        created_at = annotations.get("created-at", "")

        size = spec.get("resources", {}).get("requests", {}).get("storage", "unknown")
        storage_class = spec.get("storageClassName")
        access_modes = spec.get("accessModes", [])
        phase = status.get("phase", "Unknown")

        return VolumeStatus(
            volume_id=volume_id,
            name=volume_name,
            size=size,
            storage_class=storage_class,
            access_modes=access_modes,
            status=phase,
            created_at=created_at,
            username=username,
            metadata={
                "pvc_name": metadata.get("name"),
                "namespace": metadata.get("namespace"),
            },
        )
