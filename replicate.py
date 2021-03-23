import requests
import os

SOURCE_API = os.environ["SOURCE_API"]
SOURCE_JWT = os.environ["SOURCE_JWT"]
TARGET_API = os.environ["TARGET_API"]
TARGET_JWT = os.environ["TARGET_JWT"]

SYSTEM_NAME = os.environ.get("SYSTEM_NAME", "upstream")
USE_SECRET = os.environ.get("USE_SECRET", "") != ""


def rewrite_pipe(p):
    # figure out what upstream dataset is called
    dataset_name = p.get("sink", {}).get("dataset", p["_id"])
    return {
        "_id": p["_id"],
        "type": "pipe",
        "source": {
            "type": "binary",
            "system": SYSTEM_NAME,
            "url": f'datasets/{dataset_name}/entities',
        },
        "sink": {
            "dataset": dataset_name,
        },
        "pump": {
            "run_at_startup": True
        }
    }


def has_external_source(p):
    # TODO look at conditional sources
    return p.get("source", {}).get("type") not in ["dataset", "merge", "union_datasets", "merge_datasets"]


def has_external_transform(p):
    def is_external_transform(t):
        return t.get("type") in ["http", "rest"]

    # TODO look at conditional transforms
    transforms = p.get("transform")
    if type(transforms) is list:
        for transform in transforms:
            if is_external_transform(transform):
                return True
    if type(transforms) is dict:
        if is_external_transform(transforms):
            return True
    return False


def should_replicate(c):
    tagged = c.get("metadata", {}).get("$replicate", False)
    return has_external_source(c) or has_external_transform(c) or tagged


def rewrite_config(c):
    c = [rewrite_pipe(p) if p.get("type") == 'pipe' and should_replicate(p) else p for p in c]
    c.append({
        "_id": SYSTEM_NAME,
        "authentication": "jwt",
        "jwt_token": "$SECRET(token)" if USE_SECRET else SOURCE_JWT,
        "type": "system:url",
        "url_pattern": f'{SOURCE_API}/%s',
        "verify_ssl": True,
    })
    return c


if __name__ == '__main__':
    # replicate (and rewrite) pipes and systems
    config = requests.get(f'{SOURCE_API}/config', headers={'Authorization': f'bearer {SOURCE_JWT}'}).json()
    config = rewrite_config(config)
    requests.put(f'{TARGET_API}/config?force=true', headers={'Authorization': f'bearer {TARGET_JWT}'}, json=config)\
        .raise_for_status()
    # replicate environment variables
    env = requests.get(f'{SOURCE_API}/env', headers={'Authorization': f'bearer {SOURCE_JWT}'}).json()
    requests.put(f'{TARGET_API}/env', headers={'Authorization': f'bearer {TARGET_JWT}'}, json=env) \
        .raise_for_status()
