from django import forms

from .models import ItemType, StoreItem


class StoreItemForm(forms.ModelForm):
    class Meta:
        model = StoreItem
        fields = ["name", "description", "image", "cost", "type", "stock_remaining"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("type") == ItemType.LIMITED:
            if cleaned.get("stock_remaining") is None:
                self.add_error(
                    "stock_remaining",
                    "Limited-stock items need a stock count.",
                )
        else:
            cleaned["stock_remaining"] = None
        return cleaned
