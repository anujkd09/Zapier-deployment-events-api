# Deployment Events API

A small backend service that stores and serves **deployment events** — a record of
a service shipping a version, with its status, how long it took, and when.

Built with **FastAPI** + **SQLite**. A deployment looks like this:

```json
{
  "id": "deploy_001",
  "service": "billing-api",
  "status": "failed",
  "duration": 320,
  "timestamp": "2025-04-28T14:32:00Z",
  "commit_sha": "abc123"
}
```

> `duration` is in seconds.
> `status` is one of: `success`, `failed`, `in_progress`, `rolled_back`.

---

## Get started

Requires Python 3.10+.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python -m app.seed          # load 30 sample deployments
uvicorn app.main:app --reload
```

The API is now running at **http://127.0.0.1:8000**.

The easiest way to explore it is the built-in docs — open
**http://127.0.0.1:8000/docs** and click "Try it out" on any endpoint.

---

## Endpoints

| Method | Path                  | What it does                          |
| ------ | --------------------- | ------------------------------------- |
| `GET`  | `/deployments`        | List deployments (with filters).      |
| `GET`  | `/deployments/{id}`   | Get one deployment by its id.         |
| `GET`  | `/health`             | Health check.                         |

**List deployments** — optionally filter by `service` and/or `status`:

```bash
# Everything
curl http://127.0.0.1:8000/deployments

# Just the failed billing-api deploys
curl 'http://127.0.0.1:8000/deployments?service=billing-api&status=failed'
```

**Get one deployment** — put the id in the path:

```bash
curl http://127.0.0.1:8000/deployments/deploy_001
```

You'll get a clear `404` for an unknown id and a `422` if a filter value isn't valid.

---

## Run the tests

```bash
pytest -q
```

---

## Good to know

- Data lives in a local `deployments.db` SQLite file — re-run `python -m app.seed`
  any time to reset it with fresh sample data.
- The code is organized in layers (`api` → `services` → `repositories` → `models`
  → `data`) so it's easy to find things and extend.
