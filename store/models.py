from django.db import models


class ItemType(models.TextChoices):
    REPEATABLE = "repeatable", "Repeatable"
    LIMITED = "limited", "Limited stock"


class StoreItem(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="store/", blank=True, null=True)
    cost = models.PositiveIntegerField()
    type = models.CharField(
        max_length=12,
        choices=ItemType.choices,
        default=ItemType.REPEATABLE,
    )
    stock_remaining = models.PositiveIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def is_limited(self):
        return self.type == ItemType.LIMITED

    @property
    def in_stock(self):
        if not self.is_limited:
            return True
        return (self.stock_remaining or 0) > 0
