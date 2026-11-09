"""Background export jobs (sample under review). A job is a dict row from the jobs table."""

MAX_ATTEMPTS = 3
LEASE_SECONDS = 300


def new_job(job_id):
    return {
        "id": job_id, "state": "queued", "worker": None, "attempts": 0, "cancelled": False,
        "started_at": None, "heartbeat_at": None, "finished_at": None, "result_url": None, "error": None,
    }


def claim(job, worker_id, now):
    if job["state"] != "queued":
        return False
    job["state"] = "running"
    job["worker"] = worker_id
    job["started_at"] = now
    job["attempts"] += 1
    return True


def heartbeat(job, now):
    job["heartbeat_at"] = now


def complete(job, url, now):
    job["result_url"] = url
    job["finished_at"] = now
    job["state"] = "done"


def fail(job, error, now):
    job["error"] = error
    job["finished_at"] = now
    if job["attempts"] < MAX_ATTEMPTS:
        job["state"] = "queued"
    else:
        job["state"] = "failed"


def requeue_stale(jobs, now):
    for job in jobs:
        if job["state"] == "running" and now - job["started_at"] > LEASE_SECONDS:
            job["state"] = "queued"


def cancel(job, now):
    job["cancelled"] = True
    job["finished_at"] = now


def is_finished(job):
    return job["finished_at"] is not None


def pending_count(jobs):
    return sum(1 for job in jobs if not is_finished(job))


def progress_label(job):
    if job["cancelled"]:
        return "cancelled"
    if job["result_url"]:
        return "ready"
    if job["error"]:
        return "failed"
    return job["state"]
