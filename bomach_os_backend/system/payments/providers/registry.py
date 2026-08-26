from system.payments.providers.base import PaymentProvider, PaymentProviderError

_PROVIDERS: dict[str, PaymentProvider] = {}


def _provider_name(provider_or_name) -> str:
    value = (
        provider_or_name
        if isinstance(provider_or_name, str)
        else getattr(provider_or_name, "name", "")
    )
    return (value or "").strip().lower()


def register_provider(provider: PaymentProvider, *, replace: bool = False):
    name = _provider_name(provider)
    if not name:
        raise PaymentProviderError("Payment providers must define a non-empty name.")
    if name in _PROVIDERS and not replace:
        raise PaymentProviderError(f"Payment provider '{name}' is already registered.")
    _PROVIDERS[name] = provider
    return provider


def get_provider(name: str) -> PaymentProvider:
    normalized = _provider_name(name)
    try:
        return _PROVIDERS[normalized]
    except KeyError as exc:
        raise PaymentProviderError(
            f"Payment provider '{normalized or name}' is not registered."
        ) from exc


def clear_provider_registry():
    """Test/support helper. Production code should register providers explicitly."""
    _PROVIDERS.clear()
