import requests
import os

SOURCE_API = os.environ["SOURCE_API"]
SOURCE_JWT = os.environ["SOURCE_JWT"]
TARGET_API = os.environ["TARGET_API"]
TARGET_JWT = os.environ["TARGET_JWT"]

SYSTEM_NAME = os.environ.get("SYSTEM_NAME", "upstream")


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
    }


def should_replicate(c):
    # TODO replicate pipes that use external transforms
    return c.get("source", {}).get("type") not in ["dataset", "merge", "union_datasets", "merge_datasets"] \
           or c.get("metadata", {}).get("$replicate", False)


def rewrite_config(c):
    c = [rewrite_pipe(p) if p.get("type") == 'pipe' and should_replicate(p) else p for p in c]
    # TODO use secret for token
    c.append({
        "_id": SYSTEM_NAME,
        "authentication": "jwt",
        "jwt_token": SOURCE_JWT,
        "type": "system:url",
        "url_pattern": f'{SOURCE_API}/%s',
        "verify_ssl": True,
    })
    return c


if __name__ == '__main__':
    f = open('Sesam Sesam Prod.json', 'r')
    config = requests.get(f'{SOURCE_API}/config', headers={'Authorization': f'bearer {SOURCE_JWT}'}).json()
    config = rewrite_config(config)
    requests.put(f'{TARGET_API}/config?force=true', headers={'Authorization': f'bearer {TARGET_JWT}'}, json=config)\
        .raise_for_status()
