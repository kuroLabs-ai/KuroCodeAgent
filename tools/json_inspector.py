def json_inspector(text: str, indent: int = 2) -> dict:
    """Format, validate and inspect JSON text."""
    import json
    try:
        data = json.loads(text)
        return {
            "success": True,
            "valid": True,
            "formatted": json.dumps(data, indent=indent),
            "type": type(data).__name__,
            "keys": list(data.keys()) if isinstance(data, dict) else len(data),
        }
    except Exception as e:
        return {"success": False, "valid": False, "error": str(e)}
