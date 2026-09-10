# Research Plagiarism Checker deployment — 172.31.255.56

Deployed on 10 September 2026 from commit `a060eada6e52ae1af744d0ecbebf272ac0face7b` in `C:\Users\ramanareddy\Documents\antigravity\magical-carson`.

## Endpoint and services

| Component | State | Exposure |
|---|---|---|
| Portal, dashboards, FastAPI | Healthy | `http://172.31.255.56:8100` |
| Attention worker | Running | Docker network only |
| PostgreSQL 15 | Healthy | Docker network only; no host port |

Useful routes:

- Portal: `http://172.31.255.56:8100/`
- Plagiarism checker: `http://172.31.255.56:8100/plagiarism`
- Research attention: `http://172.31.255.56:8100/attention`
- OpenAPI: `http://172.31.255.56:8100/docs`

The Compose project is `research-plagiarism`. Its files and evidence are under `/home/oracle/research-plagiarism-checker` on the server. PostgreSQL and plagiarism indexes use named persistent volumes. The generated database password is stored only in the server-side `.env`, which is restricted to its owner.

Resource limits:

| Component | CPU limit | Memory limit |
|---|---:|---:|
| Web/API | 2 | 4 GiB |
| Worker | 1 | 768 MiB |
| PostgreSQL | 1 | 512 MiB |

Web and worker run as UID/GID `1000:1000`, drop all Linux capabilities, use `no-new-privileges`, and load the bundled Hugging Face models offline after startup. Docker logs rotate at 10 MB with three files per service. All services use `restart: unless-stopped`.

## Correction made during deployment

Live testing found that synchronous document analysis blocked FastAPI's event loop. While one analysis ran, the portal could time out. The two upload handlers now run blocking analysis in Starlette's thread pool while a shared semaphore serializes model/index access. This keeps page and health requests responsive without creating concurrent model workloads.

The same correction and regression test are included in this repository:

- `src/api.py`
- `tests/test_api_responsiveness.py`

## Verification evidence

- Database migration `abbe683d138f` applied successfully.
- Focused rebuilt-image suite: **10 passed** in 179.90 seconds.
- Local repository regression suite: **3 passed** in 82.21 seconds.
- Live synthetic plagiarism analysis: HTTP 200, engine `2.0.0`, result returned in 100.83 seconds.
- Portal response during that live analysis: 4 ms from the server and 50 ms from the Windows client.
- Peak observed web usage during analysis: about 2.54 GiB of 4 GiB and two CPU cores.
- Public DOI lookup completed through the worker: one completed job and 51 persisted evidence records.
- Final audit confirmed web/database health, worker execution, private database exposure, restart policies, non-root controls, and valid Compose configuration.
- All 15 containers running before this deployment retained their original container IDs.

Evidence files on the server include `build.log`, `startup.log`, `responsiveness-before.log`, `live-smoke.json`, `live-concurrency.json`, `verification.json`, and `existing-containers.json`.

## Operational notes

```sh
cd /home/oracle/research-plagiarism-checker
docker compose ps
docker compose logs --tail 100 web worker db
docker compose restart web worker
```

The service is bound to the machine's private address, not all host interfaces. The application itself does not provide user authentication for the portal or plagiarism upload endpoints, so access is controlled by reachability of the private network/SSH tunnel. The attention refresh action uses the repository's existing built-in internal key in both its page and API; this behavior was preserved for compatibility and should not be treated as strong authentication.

The application queries external scholarly providers during analysis and attention collection. Manuscript processing remains in memory as designed, but extracted search concepts may be sent to those providers according to the application's existing behavior.
