"""21_custom_backends.py — plug in custom session store and checkpointer backends.

Corresponds to §21 of the usage examples.

Shows:
  - BaseSessionStore: abstract interface to implement
  - register_store() to plug in a PostgreSQL-backed session store
  - BaseCheckpointer: abstract interface to implement
  - register_checkpointer() to plug in an S3-backed checkpointer
  - Agent.create(checkpoint_store="s3") to use the registered backend

Run:
    python examples/21_custom_backends.py

Note:
    The PostgreSQL and S3 backends shown here are illustrative stubs.
    Replace the ... bodies with your actual database/S3 logic.
"""

import asyncio
import json

from openjiuwen.sdk.extensions import register_store, register_checkpointer
from openjiuwen.sdk.extensions.store import BaseSessionStore, SessionRecord
from openjiuwen.sdk.extensions.checkpointer import BaseCheckpointer


# ---------------------------------------------------------------------------
# Custom session store — PostgreSQL example
# ---------------------------------------------------------------------------

class PostgresSessionStore(BaseSessionStore):
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    async def save(self, record: SessionRecord) -> None:
        # INSERT or UPDATE into your sessions table
        ...

    async def load(self, session_id: str) -> SessionRecord | None:
        # SELECT from your sessions table
        ...

    async def list(self) -> list[SessionRecord]:
        ...

    async def delete(self, session_id: str) -> None:
        ...


# ---------------------------------------------------------------------------
# Custom checkpointer — S3 example
# ---------------------------------------------------------------------------

class S3Checkpointer(BaseCheckpointer):
    def __init__(self, bucket: str) -> None:
        import boto3
        self._s3 = boto3.client("s3")
        self._bucket = bucket

    async def save(self, checkpoint_id: str, state: dict) -> None:
        self._s3.put_object(
            Bucket=self._bucket,
            Key=f"checkpoints/{checkpoint_id}.json",
            Body=json.dumps(state),
        )

    async def load(self, checkpoint_id: str) -> dict:
        obj = self._s3.get_object(
            Bucket=self._bucket,
            Key=f"checkpoints/{checkpoint_id}.json",
        )
        return json.loads(obj["Body"].read())


# ---------------------------------------------------------------------------
# Registration and usage
# ---------------------------------------------------------------------------

async def main():
    # Register before creating any agents
    register_store("postgres", PostgresSessionStore(dsn="postgresql://localhost/mydb"))
    register_checkpointer("s3", S3Checkpointer(bucket="my-agent-checkpoints"))

    # Use the S3 checkpointer via the checkpoint_store= argument
    from openjiuwen.sdk import Agent, ModelConfig
    agent = await Agent.create(
        "persistent-agent",
        model=ModelConfig.from_env(),
        checkpoint_store="s3",
    )

    await agent.run("Draft an outline for a 10-chapter book on distributed systems.")
    checkpoint_id = await agent.checkpoint()
    print(f"Checkpoint saved to S3: {checkpoint_id}")


if __name__ == "__main__":
    asyncio.run(main())
