"""Global promotional pricing applied to all paid services."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app import texts

OfferKind = Literal["none", "percent", "amount", "fixed"]


@dataclass(frozen=True)
class OfferConfig:
    enabled: bool
    kind: OfferKind
    value: int

    @property
    def is_active(self) -> bool:
        return self.enabled and self.kind != "none" and self.value > 0


def apply_offer(base_price: int, offer: OfferConfig) -> int:
    """Return final toman price; free (0) and inactive offers unchanged."""
    if base_price <= 0 or not offer.is_active:
        return base_price

    if offer.kind == "percent":
        pct = min(99, max(1, offer.value))
        return max(0, round(base_price * (100 - pct) / 100))

    if offer.kind == "amount":
        return max(0, base_price - offer.value)

    if offer.kind == "fixed":
        return max(0, offer.value)

    return base_price


def describe_offer(offer: OfferConfig) -> str:
    if not offer.is_active:
        return "خاموش"
    if offer.kind == "percent":
        return f"{offer.value}٪ تخفیف روی همه سرویس‌ها"
    if offer.kind == "amount":
        return f"{texts.format_price(offer.value)} تخفیف از هر قیمت"
    if offer.kind == "fixed":
        return f"قیمت ثابت {texts.format_price(offer.value)} برای همه"
    return "خاموش"


def format_price_with_offer(base_price: int, final_price: int) -> str:
    if final_price < base_price:
        return (
            f"<s>{texts.format_price(base_price)}</s> → "
            f"<b>{texts.format_price(final_price)}</b>"
        )
    return texts.format_price(final_price)


def format_button_price(base_price: int, final_price: int) -> str:
    """Plain text for inline buttons (no HTML)."""
    if final_price < base_price:
        return f"{final_price:,} (از {base_price:,})"
    return f"{final_price:,}"
