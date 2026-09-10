"""Keep page requests responsive while CPU/blocking analysis is in progress."""
import asyncio
from pathlib import Path
import runpy
import time
from types import SimpleNamespace
from unittest.mock import patch

import httpx
import pytest


@pytest.mark.parametrize("endpoint", ["/api/analyze", "/api/plagiarism/v2/check"])
def test_portal_remains_responsive_during_analysis(endpoint):
    def slow_analysis(*args):
        time.sleep(2)
        if endpoint.endswith("/check"):
            return SimpleNamespace(to_dict=lambda: {"engine_version": "2.0.0"})
        return {"status": "ok"}

    agent = SimpleNamespace(
        analyze_document=slow_analysis,
        analyze_document_v2=slow_analysis,
    )
    with patch("src.agent.ResearchGuardrailAgent", return_value=agent):
        namespace = runpy.run_path(
            str(Path(__file__).resolve().parents[1] / "src" / "api.py")
        )

    async def scenario():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=namespace["app"]),
            base_url="http://test",
        ) as client:
            started = time.monotonic()
            upload = asyncio.create_task(
                client.post(
                    endpoint,
                    files={"file": ("test.txt", b"Synthetic test", "text/plain")},
                )
            )
            await asyncio.sleep(0.05)
            response = await client.get("/")
            elapsed = time.monotonic() - started
            result = await upload
            assert response.status_code == 200
            assert result.status_code == 200
            assert elapsed < 1.5, f"Portal was blocked by analysis for {elapsed:.2f}s"

    asyncio.run(scenario())


def test_analysis_requests_are_serialized():
    active = 0
    maximum = 0

    def slow_analysis(*args):
        nonlocal active, maximum
        active += 1
        maximum = max(maximum, active)
        time.sleep(0.2)
        active -= 1
        return {"status": "ok"}

    agent = SimpleNamespace(analyze_document=slow_analysis)
    with patch("src.agent.ResearchGuardrailAgent", return_value=agent):
        namespace = runpy.run_path(
            str(Path(__file__).resolve().parents[1] / "src" / "api.py")
        )

    async def scenario():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=namespace["app"]),
            base_url="http://test",
        ) as client:
            results = await asyncio.gather(
                *(
                    client.post(
                        "/api/analyze",
                        files={"file": ("test.txt", b"Test")},
                    )
                    for _ in range(2)
                )
            )
            assert all(result.status_code == 200 for result in results)

    asyncio.run(scenario())
    assert maximum == 1
