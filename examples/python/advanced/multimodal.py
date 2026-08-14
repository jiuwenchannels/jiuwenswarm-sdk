"""14_multimodal.py — vision and audio inputs to agents.

Corresponds to §14 of the usage examples.

Shows:
  - ImageInput.from_file() and ImageInput.from_url()
  - VisionModelConfig for the vision model
  - AudioInput.from_file() with AudioModelConfig
  - Passing images= and audio= to agent.run()

Run:
    python examples/14_multimodal.py
"""

import asyncio
from openjiuwen.sdk import Agent, ModelConfig
from openjiuwen.sdk.multimodal import ImageInput, AudioInput, VisionModelConfig, AudioModelConfig


async def vision_example():
    agent = await Agent.create(
        "vision-agent",
        model=ModelConfig.from_env(),
        vision_config=VisionModelConfig(model="gpt-4o"),
    )

    # Describe an image from a local file
    result = await agent.run(
        "What is shown in this image? List every object you can identify.",
        images=[ImageInput.from_file("/path/to/diagram.png")],
    )
    print(result.text)

    # Images from URLs — compare two charts
    result = await agent.run(
        "Compare these two charts and summarise the key difference.",
        images=[
            ImageInput.from_url("https://example.com/chart_a.png"),
            ImageInput.from_url("https://example.com/chart_b.png"),
        ],
    )
    print(result.text)


async def audio_example():
    agent = await Agent.create(
        "audio-agent",
        model=ModelConfig.from_env(),
        audio_config=AudioModelConfig(model="whisper-1"),
    )

    result = await agent.run(
        "Transcribe this recording and extract any action items mentioned.",
        audio=[AudioInput.from_file("/path/to/meeting.mp3")],
    )
    print(result.text)


async def main():
    await vision_example()
    await audio_example()


if __name__ == "__main__":
    asyncio.run(main())
