import os
import json
from loguru import logger
from dotenv import load_dotenv
from datetime import datetime
from pipecat.services.cartesia import CartesiaTTSService

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.runner.utils import parse_telephony_websocket
from pipecat.serializers.plivo import PlivoFrameSerializer

from pipecat.services.elevenlabs.tts import ElevenLabsTTSService
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.openai.llm import OpenAILLMService

from pipecat.transports.websocket.fastapi import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)

from app.utils.cost_calculator import (
    calculate_stt_cost,
    calculate_llm_cost,
    calculate_tts_cost,
    calculate_telephony_cost
)

load_dotenv()


def calculate_usage_from_transcript(messages: list) -> dict:
    """
    Calculate token and character usage from conversation transcript.
    Uses simple approximation: 1 token ≈ 4 characters (good enough for cost estimation)
    """

    total_input_tokens = 0
    total_output_tokens = 0
    total_tts_characters = 0

    for msg in messages:
        content = msg.get('content', '')
        role = msg.get('role', '')

        # Approximate token count (1 token ≈ 4 chars for English)
        token_estimate = max(1, len(content) // 4)

        if role == 'system' or role == 'user':
            # System and user messages are input tokens
            total_input_tokens += token_estimate
        elif role == 'assistant':
            # Assistant messages are output tokens AND TTS characters
            total_output_tokens += token_estimate
            total_tts_characters += len(content)

    return {
        'llm_input_tokens': total_input_tokens,
        'llm_output_tokens': total_output_tokens,
        'tts_characters': total_tts_characters
    }


async def run_patient_call(websocket, patient_name: str, questions: str, call_id: int, db_session):
    """Run the patient follow-up call using Pipecat"""

    # Parse the Plivo WebSocket connection
    transport_type, call_data = await parse_telephony_websocket(websocket)
    logger.info(f"Detected transport: {transport_type}")

    # Create Plivo serializer
    serializer = PlivoFrameSerializer(
        stream_id=call_data["stream_id"],
        call_id=call_data["call_id"],
        auth_id=os.getenv("PLIVO_AUTH_ID", ""),
        auth_token=os.getenv("PLIVO_AUTH_TOKEN", ""),
    )

    # Create transport
    transport = FastAPIWebsocketTransport(
        websocket=websocket,
        params=FastAPIWebsocketParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            add_wav_header=False,
            vad_analyzer=SileroVADAnalyzer(),
            serializer=serializer,
        ),
    )

    # Create AI services
    llm = OpenAILLMService(api_key=os.getenv("OPENAI_API_KEY"), model="gpt-4o-mini")
    stt = DeepgramSTTService(api_key=os.getenv("DEEPGRAM_API_KEY"))

    # ElevenLabs TTS - faster and higher quality
    # tts = ElevenLabsTTSService(
    #     api_key=os.getenv("ELEVENLABS_API_KEY"),
    #     voice_id=os.getenv("ELEVENLABS_VOICE_ID"),
    #     model="eleven_turbo_v2_5",  # Fastest model
    # )
    tts = CartesiaTTSService(
    api_key=os.getenv("CARTESIA_API_KEY"),
    # voice_id="9cebb910-d4b7-4a4a-85a4-12c79137724c",
    voice_id="bdab08ad-4137-4548-b9db-6142854c7525",
)


    # Conversation context
    messages = [
        {
            "role": "system",
            "content": f"You are a  hospital assistant of presco hospital calling {patient_name}. Your task: {questions}. Start by greeting them warmly and asking the question. Keep responses under 2 sentences."
        },

    ]

    context = OpenAILLMContext(messages)
    context_aggregator = llm.create_context_aggregator(context)

    # Build pipeline
    pipeline = Pipeline([
        transport.input(),
        stt,
        context_aggregator.user(),
        llm,
        tts,
        transport.output(),
        context_aggregator.assistant(),
    ])

    # Create task
    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            audio_in_sample_rate=8000,
            audio_out_sample_rate=8000,
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
    )

    # Event handlers
    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info(f"Call connected for {patient_name} (call_id={call_id})")
        # Bot speaks automatically from pre-filled assistant message

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info(f"Call disconnected for {patient_name} (call_id={call_id})")

        # Get conversation from context
        all_messages = context.get_messages()

        # Calculate usage from transcript (simplified, no blocking operations)
        usage = calculate_usage_from_transcript(all_messages)

        logger.info(f"Usage calculated: {usage}")

        # Save transcript with costs
        await save_transcript(call_id, all_messages, db_session, usage)

        await task.cancel()

    # Run pipeline
    runner = PipelineRunner(handle_sigint=False)
    await runner.run(task)

    logger.info(f"Pipeline finished for call_id={call_id}")

async def generate_call_summary(messages: list) -> dict:
    """Generate AI summary of the call conversation"""
    from openai import AsyncOpenAI
    import os

    # Extract conversation (skip system prompt)
    conversation = [msg for msg in messages if msg["role"] != "system"]

    # Build conversation text
    conversation_text = "\n".join([
        f"{msg['role'].upper()}: {msg['content']}"
        for msg in conversation
    ])

    # Prompt for summary
    summary_prompt = f"""Analyze this hospital follow-up call and provide a structured summary in JSON format.

Conversation:
{conversation_text}

Provide a JSON response with:
- sentiment: (positive/neutral/negative/concerned)
- key_points: (list of main topics discussed)
- health_concerns: (list of any health issues mentioned)
- follow_up_needed: (true/false)
- follow_up_reason: (if needed, brief reason)

Be concise and focus on medically relevant information."""

    try:
        client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a medical assistant analyzing patient call transcripts. Always respond with valid JSON."},
                {"role": "user", "content": summary_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.3
        )

        summary_text = response.choices[0].message.content
        logger.info(f"Generated call summary: {summary_text}")
        return summary_text

    except Exception as e:
        logger.error(f"Error generating summary: {e}")
        return json.dumps({
            "sentiment": "unknown",
            "key_points": ["Error generating summary"],
            "health_concerns": [],
            "follow_up_needed": False,
            "follow_up_reason": ""
        })




async def save_transcript(call_id: int, messages: list, db_session, usage: dict):
    """Save transcript and calculate costs"""
    from app.models import Transcript, Call
    from sqlalchemy import select

    # Extract conversation (skip system prompt)
    conversation_messages = [msg for msg in messages if msg["role"] != "system"]

    full_transcript = {
        "conversation": conversation_messages,
        "call_ended_at": datetime.utcnow().isoformat()
    }

    # Generate AI summary
    logger.info(f"Generating summary for call {call_id}")
    summary = await generate_call_summary(messages)

    try:
        # Check if transcript exists
        result = await db_session.execute(
            select(Transcript).where(Transcript.call_id == call_id)
        )
        existing = result.scalar_one_or_none()

        # Get call
        call_result = await db_session.execute(
            select(Call).where(Call.id == call_id)
        )
        call = call_result.scalar_one_or_none()

        # Initialize costs
        stt_cost = 0.0
        llm_cost = 0.0
        tts_cost = 0.0
        telephony_cost = 0.0

        if call:
            call.ended_at = datetime.utcnow()
            call.status = "completed"

            # Calculate duration
            if call.started_at:
                duration = (call.ended_at - call.started_at).total_seconds()
                call.duration = int(duration)

                # Calculate costs
                stt_cost = calculate_stt_cost(call.duration)
                llm_cost = calculate_llm_cost(
                    usage.get('llm_input_tokens', 0),
                    usage.get('llm_output_tokens', 0)
                )
                tts_cost = calculate_tts_cost(usage.get('tts_characters', 0))
                telephony_cost = calculate_telephony_cost(call.duration)

                # Total cost
                total_cost = stt_cost + llm_cost + tts_cost + telephony_cost
                call.cost = round(total_cost, 4)

                logger.info(f"Call {call_id} - Duration: {call.duration}s")
                logger.info(f"Usage - Input: {usage.get('llm_input_tokens', 0)} tokens, Output: {usage.get('llm_output_tokens', 0)} tokens, TTS: {usage.get('tts_characters', 0)} chars")
                logger.info(f"Costs - STT: ${stt_cost}, LLM: ${llm_cost}, TTS: ${tts_cost}, Tel: ${telephony_cost}, Total: ${total_cost}")

        # Save or update transcript with summary
        if existing:
            existing.full_transcript = json.dumps(full_transcript)
            existing.summary = summary  # Add summary
            existing.stt_cost = stt_cost
            existing.llm_cost = llm_cost
            existing.tts_cost = tts_cost
        else:
            transcript = Transcript(
                call_id=call_id,
                full_transcript=json.dumps(full_transcript),
                summary=summary,  # Add summary
                stt_cost=stt_cost,
                llm_cost=llm_cost,
                tts_cost=tts_cost,
            )
            db_session.add(transcript)

        await db_session.commit()
        logger.info(f"Saved transcript with summary for call {call_id}")

    except Exception as e:
        logger.error(f"Error saving transcript: {e}")
        await db_session.rollback()
        raise



# !!!! above one is working for english




# import os
# import json
# from loguru import logger
# from dotenv import load_dotenv
# from datetime import datetime

# from pipecat.audio.vad.silero import SileroVADAnalyzer
# from pipecat.pipeline.pipeline import Pipeline
# from pipecat.pipeline.runner import PipelineRunner
# from pipecat.pipeline.task import PipelineParams, PipelineTask
# from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
# from pipecat.runner.utils import parse_telephony_websocket
# from pipecat.serializers.plivo import PlivoFrameSerializer

# from pipecat.services.cartesia import CartesiaTTSService
# from pipecat.services.deepgram.stt import DeepgramSTTService
# from pipecat.services.openai.llm import OpenAILLMService

# from pipecat.transports.websocket.fastapi import (
#     FastAPIWebsocketParams,
#     FastAPIWebsocketTransport,
# )

# from app.utils.cost_calculator import (
#     calculate_stt_cost,
#     calculate_llm_cost,
#     calculate_tts_cost,
#     calculate_telephony_cost
# )

# load_dotenv()


# def calculate_usage_from_transcript(messages: list) -> dict:
#     """Calculate token and character usage from conversation transcript"""
#     total_input_tokens = 0
#     total_output_tokens = 0
#     total_tts_characters = 0

#     for msg in messages:
#         content = msg.get('content', '')
#         role = msg.get('role', '')
#         token_estimate = max(1, len(content) // 4)

#         if role == 'system' or role == 'user':
#             total_input_tokens += token_estimate
#         elif role == 'assistant':
#             total_output_tokens += token_estimate
#             total_tts_characters += len(content)

#     return {
#         'llm_input_tokens': total_input_tokens,
#         'llm_output_tokens': total_output_tokens,
#         'tts_characters': total_tts_characters
#     }


# async def run_patient_call(websocket, patient_name: str, questions: str, call_id: int, db_session, patient_language: str = "english"):
#     """Run the patient follow-up call using Pipecat"""

#     transport_type, call_data = await parse_telephony_websocket(websocket)
#     logger.info(f"Detected transport: {transport_type}")

#     serializer = PlivoFrameSerializer(
#         stream_id=call_data["stream_id"],
#         call_id=call_data["call_id"],
#         auth_id=os.getenv("PLIVO_AUTH_ID", ""),
#         auth_token=os.getenv("PLIVO_AUTH_TOKEN", ""),
#     )

#     transport = FastAPIWebsocketTransport(
#         websocket=websocket,
#         params=FastAPIWebsocketParams(
#             audio_in_enabled=True,
#             audio_out_enabled=True,
#             add_wav_header=False,
#             vad_analyzer=SileroVADAnalyzer(),
#             serializer=serializer,
#         ),
#     )

#     # Create AI services with language support
#     llm = OpenAILLMService(api_key=os.getenv("OPENAI_API_KEY"), model="gpt-4o-mini")

#     # STT - Deepgram supports Hindi
#     if patient_language.lower() == "hindi":
#         stt = DeepgramSTTService(
#             api_key=os.getenv("DEEPGRAM_API_KEY"),
#             language="hi"
#         )
#     else:
#         stt = DeepgramSTTService(api_key=os.getenv("DEEPGRAM_API_KEY"))

#     # TTS - Cartesia with language-specific voice
#     if patient_language.lower() == "hindi":
#         tts = CartesiaTTSService(
#             api_key=os.getenv("CARTESIA_API_KEY"),
#             voice_id=os.getenv("CARTESIA_HINDI_VOICE", "4d2fd738-3b3d-4368-957a-bb4805275bd9"),
#             language="hi"
#         )
#         logger.info(f"Using Hindi voice for {patient_name}")
#     else:
#         tts = CartesiaTTSService(
#             api_key=os.getenv("CARTESIA_API_KEY"),
#             voice_id=os.getenv("CARTESIA_ENGLISH_VOICE", "bdab08ad-4137-4548-b9db-6142854c7525"),
#         )
#         logger.info(f"Using English voice for {patient_name}")

#     # System prompt based on language
#     if patient_language.lower() == "hindi":
#       system_prompt = f"""आप प्रेस्को अस्पताल की सहायक हैं जो {patient_name} को फोन कर रही हैं।

# आपका काम: {questions}

# नियम:
# - केवल एक सवाल पूछें
# - छोटे वाक्य बोलें
# - धीरे और साफ बोलें
# - पहले नमस्ते कहें, फिर एक सवाल पूछें

# उदाहरण: "नमस्ते! आपका मूत्राशय कैसा है?"
# """
#     else:
#         system_prompt = f"""You are a hospital assistant of presco hospital calling {patient_name}.
# Your task: {questions}. Start by greeting them warmly and asking the question. Keep responses under 2 sentences."""

#     messages = [{"role": "system", "content": system_prompt}]

#     context = OpenAILLMContext(messages)
#     context_aggregator = llm.create_context_aggregator(context)

#     pipeline = Pipeline([
#         transport.input(),
#         stt,
#         context_aggregator.user(),
#         llm,
#         tts,
#         transport.output(),
#         context_aggregator.assistant(),
#     ])

#     task = PipelineTask(
#         pipeline,
#         params=PipelineParams(
#             audio_in_sample_rate=8000,
#             audio_out_sample_rate=8000,
#             enable_metrics=True,
#             enable_usage_metrics=True,
#         ),
#     )

#     @transport.event_handler("on_client_connected")
#     async def on_client_connected(transport, client):
#         logger.info(f"Call connected for {patient_name} (call_id={call_id}, language={patient_language})")

#     @transport.event_handler("on_client_disconnected")
#     async def on_client_disconnected(transport, client):
#         logger.info(f"Call disconnected for {patient_name} (call_id={call_id})")
#         all_messages = context.get_messages()
#         usage = calculate_usage_from_transcript(all_messages)
#         logger.info(f"Usage calculated: {usage}")
#         await save_transcript(call_id, all_messages, db_session, usage)
#         await task.cancel()

#     runner = PipelineRunner(handle_sigint=False)
#     await runner.run(task)
#     logger.info(f"Pipeline finished for call_id={call_id}")


# async def generate_call_summary(messages: list) -> dict:
#     """Generate AI summary of the call conversation"""
#     from openai import AsyncOpenAI

#     conversation = [msg for msg in messages if msg["role"] != "system"]
#     conversation_text = "\n".join([
#         f"{msg['role'].upper()}: {msg['content']}"
#         for msg in conversation
#     ])

#     summary_prompt = f"""Analyze this hospital follow-up call and provide a structured summary in JSON format.

# Conversation:
# {conversation_text}

# Provide a JSON response with:
# - sentiment: (positive/neutral/negative/concerned)
# - key_points: (list of main topics discussed)
# - health_concerns: (list of any health issues mentioned)
# - follow_up_needed: (true/false)
# - follow_up_reason: (if needed, brief reason)

# Be concise and focus on medically relevant information."""

#     try:
#         client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
#         response = await client.chat.completions.create(
#             model="gpt-4o-mini",
#             messages=[
#                 {"role": "system", "content": "You are a medical assistant analyzing patient call transcripts. Always respond with valid JSON."},
#                 {"role": "user", "content": summary_prompt}
#             ],
#             response_format={"type": "json_object"},
#             temperature=0.3
#         )
#         summary_text = response.choices[0].message.content
#         logger.info(f"Generated call summary: {summary_text}")
#         return summary_text
#     except Exception as e:
#         logger.error(f"Error generating summary: {e}")
#         return json.dumps({
#             "sentiment": "unknown",
#             "key_points": ["Error generating summary"],
#             "health_concerns": [],
#             "follow_up_needed": False,
#             "follow_up_reason": ""
#         })


# async def save_transcript(call_id: int, messages: list, db_session, usage: dict):
#     """Save transcript and calculate costs"""
#     from app.models import Transcript, Call
#     from sqlalchemy import select

#     conversation_messages = [msg for msg in messages if msg["role"] != "system"]
#     full_transcript = {
#         "conversation": conversation_messages,
#         "call_ended_at": datetime.utcnow().isoformat()
#     }

#     logger.info(f"Generating summary for call {call_id}")
#     summary = await generate_call_summary(messages)

#     try:
#         result = await db_session.execute(
#             select(Transcript).where(Transcript.call_id == call_id)
#         )
#         existing = result.scalar_one_or_none()

#         call_result = await db_session.execute(
#             select(Call).where(Call.id == call_id)
#         )
#         call = call_result.scalar_one_or_none()

#         stt_cost = 0.0
#         llm_cost = 0.0
#         tts_cost = 0.0
#         telephony_cost = 0.0

#         if call:
#             call.ended_at = datetime.utcnow()
#             call.status = "completed"

#             if call.started_at:
#                 duration = (call.ended_at - call.started_at).total_seconds()
#                 call.duration = int(duration)

#                 stt_cost = calculate_stt_cost(call.duration)
#                 llm_cost = calculate_llm_cost(
#                     usage.get('llm_input_tokens', 0),
#                     usage.get('llm_output_tokens', 0)
#                 )
#                 tts_cost = calculate_tts_cost(usage.get('tts_characters', 0))
#                 telephony_cost = calculate_telephony_cost(call.duration)

#                 total_cost = stt_cost + llm_cost + tts_cost + telephony_cost
#                 call.cost = round(total_cost, 4)

#                 logger.info(f"Call {call_id} - Duration: {call.duration}s")
#                 logger.info(f"Usage - Input: {usage.get('llm_input_tokens', 0)} tokens, Output: {usage.get('llm_output_tokens', 0)} tokens, TTS: {usage.get('tts_characters', 0)} chars")
#                 logger.info(f"Costs - STT: ${stt_cost}, LLM: ${llm_cost}, TTS: ${tts_cost}, Tel: ${telephony_cost}, Total: ${total_cost}")

#         if existing:
#             existing.full_transcript = json.dumps(full_transcript)
#             existing.summary = summary
#             existing.stt_cost = stt_cost
#             existing.llm_cost = llm_cost
#             existing.tts_cost = tts_cost
#         else:
#             transcript = Transcript(
#                 call_id=call_id,
#                 full_transcript=json.dumps(full_transcript),
#                 summary=summary,
#                 stt_cost=stt_cost,
#                 llm_cost=llm_cost,
#                 tts_cost=tts_cost,
#             )
#             db_session.add(transcript)

#         await db_session.commit()
#         logger.info(f"Saved transcript with summary for call {call_id}")

#     except Exception as e:
#         logger.error(f"Error saving transcript: {e}")
#         await db_session.rollback()
#         raise
