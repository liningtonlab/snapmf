import uuid
from enum import Enum
from django.db import models


class FileFormat(str, Enum):
    graphml = "graphml"
    cytoscape = "cytoscape"


class Status(str, Enum):
    queued = "queued"
    running = "running"
    failed = "failed"
    completed = "completed"


class Job(models.Model):
    """Model for tracking SnapMS Jobs.
    Automatically creates a UUID and sets status to queued when created.

    Tracks date created, archived (for when over expiry date: probably 6 months),
    status, inputfile name, and parameters used.
    """

    id = models.CharField(
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        editable=False,
        max_length=32,
    )
    created = models.DateTimeField(auto_now_add=True)
    archived = models.BooleanField(default=False)
    status = models.CharField(max_length=128, default=Status.queued.value)
    inputfile = models.CharField(max_length=256)
    parameters = models.TextField()
