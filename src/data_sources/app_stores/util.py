
def synth_url(store_name: str, review_id) -> str:
    """Synthesize a URL from a store name and review ID"""

    # NOTE: I used a fake domain here
    return f"https://{store_name}/{review_id}"