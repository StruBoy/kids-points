from django.conf import settings
from django.db import models


class PurchaseStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    DENIED = "denied", "Denied"
    FULFILLED = "fulfilled", "Fulfilled"


SPENT_STATUSES = (PurchaseStatus.APPROVED, PurchaseStatus.FULFILLED)
ACTIVE_STATUSES = (
    PurchaseStatus.PENDING,
    PurchaseStatus.APPROVED,
    PurchaseStatus.FULFILLED,
)


class PurchaseRequest(models.Model):
    kid = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="purchase_requests",
    )
    item = models.ForeignKey(
        "store.StoreItem",
        on_delete=models.PROTECT,
        related_name="purchase_requests",
    )
    cost_at_request = models.PositiveIntegerField()
    status = models.CharField(
        max_length=10,
        choices=PurchaseStatus.choices,
        default=PurchaseStatus.PENDING,
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="purchase_decisions",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-requested_at"]

    def __str__(self):
        return f"{self.kid.name} → {self.item.name} ({self.status})"
