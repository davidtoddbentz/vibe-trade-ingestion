#!/usr/bin/env python3
"""Simple scheduler that runs batch_job.py periodically."""

import asyncio
import os
import signal
import subprocess
import sys
from pathlib import Path

# Global flag for graceful shutdown
shutdown = False


def signal_handler(sig, frame):
    """Handle shutdown signals gracefully."""
    global shutdown
    print("\n🛑 Stopping scheduler...")
    shutdown = True


async def run_job():
    """Run the batch job."""
    print("🚀 Running ingestion job...")
    batch_job_path = Path(__file__).parent / "batch_job.py"

    try:
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            str(batch_job_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )

        stdout, _ = await process.communicate()

        if process.returncode == 0:
            print("✅ Job completed successfully")
        else:
            print(f"⚠️  Job exited with code {process.returncode}")
            if stdout:
                print(stdout.decode())

    except Exception as e:
        print(f"❌ Error running job: {e}")


async def main():
    """Main scheduler loop."""
    interval_minutes = int(os.getenv("INGESTION_INTERVAL_MINUTES", "1"))
    interval_seconds = interval_minutes * 60

    print(f"📅 Starting ingestion scheduler (every {interval_minutes} minute(s))")
    print("Press Ctrl+C to stop\n")

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run immediately
    await run_job()

    # Then run on schedule
    while not shutdown:
        try:
            await asyncio.sleep(interval_seconds)
            if not shutdown:
                await run_job()
        except asyncio.CancelledError:
            break

    print("✅ Scheduler stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n✅ Scheduler stopped")

