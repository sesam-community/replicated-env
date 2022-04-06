import requests
import os


def rewrite_pipe(p, system_name):
    # figure out what upstream dataset is called
    dataset_name = p.get("sink", {}).get("dataset", p["_id"])
    return {
        "_id": p["_id"],
        "type": "pipe",
        "source": {
            "type": "binary",
            "system": system_name,
            "url": f'datasets/{dataset_name}/entities',
        },
        "sink": {
            "dataset": dataset_name,
        },
        "pump": {
            "run_at_startup": True,
        },
        "metadata": {
            "$replicate.py": {
                "original": p,
            }
        },
    }


def has_external_source(p):
    source = p.get("source")
    source_type = source.get("type")
    if source_type == "conditional":
        condition = source["condition"]
        if condition.startswith("$ENV"):
            # We assume that the alternative we need is "prod"
            condition = "prod"
        source = source["alternatives"][condition]
        source_type = source.get("type")
    return source_type not in ["dataset", "merge", "union_datasets", "merge_datasets"]


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
    return c.get("type") == 'pipe' and has_external_source(c) or has_external_transform(c) or tagged


def should_filter(c):
    return c.get("type") == 'pipe' and has_external_source(c) and c.get("sink", {}).get("type", "dataset") != "dataset"


def rewrite_config(c, source_api, system_name):
    c = [rewrite_pipe(p, system_name) if should_replicate(p) else p for p in c if not should_filter(p)]
    c.append({
        "_id": system_name,
        "authentication": "jwt",
        "jwt_token": "$SECRET(token)",
        "type": "system:url",
        "url_pattern": f'{source_api}/%s',
        "verify_ssl": True,
    })
    return c


if __name__ == '__main__':
    SOURCE_API = os.environ["SOURCE_API"]
    SOURCE_JWT = os.environ["SOURCE_JWT"]
    TARGET_API = os.environ["TARGET_API"]
    TARGET_JWT = os.environ["TARGET_JWT"]
    UPSTREAM_SYSTEM_JWT = os.environ.get("UPSTREAM_SYSTEM_JWT", SOURCE_JWT)
    SYSTEM_NAME = os.environ.get("SYSTEM_NAME", "upstream")

    # replicate (and rewrite) pipes and systems
    response = requests.get(f'{SOURCE_API}/config', headers={'Authorization': f'bearer {SOURCE_JWT}'})
    response.raise_for_status()

    config = rewrite_config(response.json(), SOURCE_API, SYSTEM_NAME)
    requests.put(f'{TARGET_API}/config?force=true', headers={'Authorization': f'bearer {TARGET_JWT}'}, json=config)\
        .raise_for_status()
    # replicate environment variables
    env = requests.get(f'{SOURCE_API}/env', headers={'Authorization': f'bearer {SOURCE_JWT}'}).json()
    requests.put(f'{TARGET_API}/env', headers={'Authorization': f'bearer {TARGET_JWT}'}, json=env) \
        .raise_for_status()
    # store the jwt token secret in the "upstream" system
    requests.put(f'{TARGET_API}/systems/{SYSTEM_NAME}/secrets', headers={'Authorization': f'bearer {TARGET_JWT}'},
                 json={"token": UPSTREAM_SYSTEM_JWT}
                 ).raise_for_status()
