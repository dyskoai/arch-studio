"""
Agent API routes for conversational agents.
Handles session creation, chat interactions, and image search.
"""
import os
import json
import uuid
import base64
import logging
import time
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Body
from vertexai import agent_engines
from google.genai import types as genai_types
from dotenv import load_dotenv

from models.agent_models import (
     ChatRequest, ChatResponse,
    CompanionRequest, CompanionResponse, ImageSearchResponse, ImageSearchResult
)
from utils.auth import verify_bearer_token
from services.image_search import search_by_image
from services.firebase_store import _initialize_firebase
from firebase_admin import firestore as fs_module

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Configuration
GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")
GOOGLE_CLOUD_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

from vertexai import agent_engines


# Check for local agent execution
USE_LOCAL_AGENTS = os.getenv("USE_LOCAL_AGENTS", "false").lower() == "true"

if USE_LOCAL_AGENTS:
    logger.info("Initializing LOCAL AGENTS support...")
    try:
        # 1. Ensure backend/.. is in sys.path to import chat_agent and companion_agent
        import sys
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # adk-agent/backend
        root_dir = os.path.dirname(backend_dir) # adk-agent
        if root_dir not in sys.path:
            sys.path.append(root_dir)
        
        # 2. Import local agents
        # Note: We import inside the block to avoid import errors if requirements aren't met for cloud run
        from chat_agent.agent import root_agent as chat_agent_local
        from companion_agent.agent import root_agent as companion_agent_local
        
        # 3. Import wrapper
        from backend.utils.local_agent import LocalAgentWrapper
        
        # 4. Wrap agents
        chat_remote_app = LocalAgentWrapper(chat_agent_local)
        companion_remote_app = LocalAgentWrapper(companion_agent_local)
        
        # For image agent, we might not have a local equivalent easily wrappable yet 
        # or it might be part of companion. 
        # If user has image agent local value, try to use it, else None.
        # But for now, let's set it to None or try to find it if it exists.
        image_remote_app = None 
        
        logger.info("Successfully initialized LOCAL AGENTS.")
        
    except ImportError as e:
        logger.error(f"Failed to import local agents: {e}")
        # Fallback or re-raise? 
        # If user explicitly asked for local agents, we should probably fail.
        raise e
else:
    # Cloud Agent Engine — IDs are read from env vars at startup time,
    # but the actual agent_engines.get() calls are deferred to first use
    # so the server starts cleanly even if a resource is temporarily unavailable.
    CHAT_AGENT_ENGINE_ID = os.getenv("CHAT_AGENT_ENGINE_ID")
    COMPANION_AGENT_ENGINE_ID = os.getenv("COMPANION_AGENT_ENGINE_ID")
    IMAGE_AGENT_ENGINE_ID = os.getenv("IMAGE_AGENT_ENGINE_ID") or os.getenv("AGENT_ENGINE_ID")

    if not CHAT_AGENT_ENGINE_ID or not COMPANION_AGENT_ENGINE_ID:
        raise ValueError(
            "CHAT_AGENT_ENGINE_ID or COMPANION_AGENT_ENGINE_ID not found in environment variables. "
            "Please set CHAT_AGENT_ENGINE_ID and COMPANION_AGENT_ENGINE_ID as environment variables."
        )

    _chat_remote_app = None
    _companion_remote_app = None
    _image_remote_app = None

    def _get_chat_app():
        global _chat_remote_app
        if _chat_remote_app is None:
            _chat_remote_app = agent_engines.get(CHAT_AGENT_ENGINE_ID)
        return _chat_remote_app

    def _get_companion_app():
        global _companion_remote_app
        if _companion_remote_app is None:
            _companion_remote_app = agent_engines.get(COMPANION_AGENT_ENGINE_ID)
        return _companion_remote_app

    def _get_image_app():
        global _image_remote_app
        if _image_remote_app is None and IMAGE_AGENT_ENGINE_ID:
            _image_remote_app = agent_engines.get(IMAGE_AGENT_ENGINE_ID)
        return _image_remote_app

    # Aliases so the rest of the file works without change
    class _LazyApp:
        """Proxy that initialises the remote app on first attribute access."""
        def __init__(self, getter): self._getter = getter
        def __getattr__(self, name): return getattr(self._getter(), name)

    chat_remote_app      = _LazyApp(_get_chat_app)
    companion_remote_app = _LazyApp(_get_companion_app)
    image_remote_app     = _LazyApp(_get_image_app)


# Create router
router = APIRouter()

ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp", "image/gif"]


@router.post("/trends")
async def get_trends(request_body: dict = Body(...)):
    """Return static trend payload for a given trend_id from data.json.

    The payload contains all data for the requested trend.
    """
    try:
        trend_id = request_body.get("trend_id")
        if not trend_id:
            raise HTTPException(status_code=400, detail="trend_id is required in request body")
        
        # Load data.json from the same directory
        data_file_path = os.path.join(os.path.dirname(__file__), "..", "data.json")
        
        if not os.path.exists(data_file_path):
            raise HTTPException(status_code=500, detail="data.json not found")
        
        with open(data_file_path, 'r', encoding='utf-8') as f:
            trends_data = json.load(f)
        
        # Find the trend with matching trend_id
        for trend in trends_data:
            if trend.get("trend_id") == trend_id:
                return trend
        
        # If trend not found
        raise HTTPException(status_code=404, detail=f"Unknown trend_id: {trend_id}")
        
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("/trends: unexpected error")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/trends-all")
async def get_all_trends():
    """Return all trends from data.json as a list."""
    try:
        # Load data.json from the same directory
        data_file_path = os.path.join(os.path.dirname(__file__), "..", "data.json")
        
        if not os.path.exists(data_file_path):
            raise HTTPException(status_code=500, detail="data.json not found")
        
        with open(data_file_path, 'r', encoding='utf-8') as f:
            trends_data = json.load(f)
        
        # Return all trends as a list
        return {"trends": trends_data, "total": len(trends_data)}
        
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("/trends-all: unexpected error")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, _: dict = Depends(verify_bearer_token)):
    """Chat endpoint that processes messages and returns a response."""
    request_start_time = time.time()
    
    try:
        logger.info("chat REQUEST START | user_id=%s session_id=%s timestamp=%s", 
                   request.user_id, request.session_id, datetime.utcnow().isoformat())
        
        user_id = request.user_id
        session_id = request.session_id
        message = request.message
        # Extract gender from input (if provided)
        gender = getattr(request, "gender", None)
        
        # Create session if not provided 
        session_created = False
        if not session_id:
            logger.info("chat: session_id not provided, creating new remote session")
            session_create_start = time.time()
            session = await chat_remote_app.async_create_session(user_id=user_id)
            session_id = (
                session.get("id")
                or session.get("name")
                or session.get("session_id")
            )
            if not session_id:
                raise ValueError(f"Failed to extract session_id from session object: {session}")
            session_created = True
            logger.debug("chat: session creation took %.2fs", time.time() - session_create_start)
            logger.info("chat: new session created session_id=%s", session_id)
        
        # Collect all events from the stream
        events = []
        try:
            logger.debug("chat: starting async_stream_query user_id=%s session_id=%s", user_id, session_id)
            stream_start = time.time()
            # Combine message and gender into a single payload for the agent
            payload = json.dumps({
                "message": message,
                "gender": gender,
            })
            stream = chat_remote_app.async_stream_query(
                user_id=user_id,
                session_id=session_id,
                message=payload,
            )
            first_event_received = False
            async for event in stream:
                if not first_event_received:
                    logger.debug("chat: TIME TO FIRST RESPONSE %.2fs", time.time() - request_start_time)
                    first_event_received = True
                logger.debug("chat: event=%s", event)
                events.append(event)
            logger.debug("chat: stream_query took %.2fs | events_count=%d", time.time() - stream_start, len(events))
        except Exception as e:
            logger.exception("chat: async_stream_query failed")
            raise HTTPException(
                status_code=500, 
                detail=f"Error during stream query: {str(e)}"
            )
        
        # Extract text and tool results from all events
        process_start = time.time()
        text_parts = []
        tool_result: dict = {}
        
        for event in events:
            logger.debug("chat: event=%s", event)
            # Skip partial streaming chunks — only use the final consolidated event
            if event.get("partial"):
                continue
            if "content" in event and "parts" in event["content"]:
                parts = event["content"]["parts"]
                for part in parts:
                    if "text" in part and not part.get("thought"):
                        text_parts.append(part["text"])
                    # Support both snake_case (Vertex AI) and camelCase (local adk api_server)
                    func_resp = part.get("function_response") or part.get("functionResponse")
                    if func_resp:
                        response_payload = func_resp.get("response")
                        if isinstance(response_payload, dict):
                            tool_result = response_payload
                        elif response_payload is not None:
                            tool_result = {"response": response_payload}
        
        # Combine all text parts into final message
        final_message = " ".join(text_parts).strip()
        
        # If no text response but we have tool results, create a message
        if not final_message and tool_result:
            if "error" in tool_result:
                final_message = f"Search completed but encountered an issue: {tool_result.get('error', 'Unknown error')}"
            elif "requests" in tool_result and len(tool_result.get("requests", [])) == 0:
                final_message = f"Search completed but no products were found. {tool_result.get('error', '')}"
            else:
                final_message = "Search completed successfully."
        
        logger.debug("chat: result processing took %.2fs", time.time() - process_start)
        logger.info("chat: final_message=%s", final_message)
        logger.debug("chat: TOTAL REQUEST TIME %.2fs", time.time() - request_start_time)

        # Persist current_query to Firestore for companion agent context (single canonical format)
        if tool_result and tool_result.get("journey_name"):
            try:
                fs_client = _initialize_firebase()
                payload = {
                    "journey_name": tool_result.get("journey_name", ""),
                    "updated_at": fs_module.SERVER_TIMESTAMP,
                }
                # Always store Algolia batch as JSON string under the same field name for compatibility
                aq = tool_result.get("algolia_query")
                if aq is not None:
                    try:
                        payload["algolia_query"] = json.dumps(aq)
                    except Exception as enc_exc:
                        logger.warning("chat: failed to encode algolia_query to JSON: %s", enc_exc)

                # Save full query input for companion agent context reconstruction
                if tool_result.get("search_term"):
                    payload["search_term"] = tool_result["search_term"]
                if tool_result.get("filters"):
                    payload["filters"] = tool_result["filters"]
                if tool_result.get("index_type"):
                    payload["index_type"] = tool_result["index_type"]
                if tool_result.get("query_type"):
                    payload["query_type"] = tool_result["query_type"]

                fs_client.collection("chatsessionQueries").document(session_id).set(payload, merge=True)
            except Exception as exc:
                print("chat: failed to save current_query to Firestore: %s", exc)
                logger.warning("chat: failed to save current_query to Firestore: %s", exc)

        # Build response
        return ChatResponse(
            message=final_message,
            session_id=session_id,
            result=tool_result,
        )
        
    except HTTPException:
        logger.exception("chat: HTTPException raised")
        raise
    except Exception as e:
        logger.exception("chat: unexpected exception")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/companion", response_model=CompanionResponse)
async def companion(request: CompanionRequest, _: dict = Depends(verify_bearer_token)):
    """Chat endpoint that processes messages and returns a response."""
    request_start_time = time.time()
    try:
        logger.info("companion called with user_id=%s session_id=%s", request.user_id, request.session_id)
        
        user_id = request.user_id
        session_id = request.session_id
        message = request.message
        chat_session_id = request.chat_session_id
        object_id = request.object_id
        index_name = request.index_name
        journey_name = request.journey_name
        filters = request.filters
        index_type = request.index_type

        # Create session if not provided
        session_created = False
        if not session_id:
            logger.info("companion: session_id not provided, creating new remote session")
            session_create_start = time.time()
            session = await companion_remote_app.async_create_session(user_id=user_id)
            session_id = (
                session.get("id")
                or session.get("name")
                or session.get("session_id")
            )
            if not session_id:
                raise ValueError(f"Failed to extract session_id from session object: {session}")
            session_created = True
            logger.debug("companion: session creation took %.2fs", time.time() - session_create_start)
            logger.info("companion: new session created session_id=%s", session_id)
        
        payload = json.dumps({
            "message": message,
            "chat_session_id": chat_session_id,
            "object_id": object_id,
            "index_name": index_name,
            "journey_name": journey_name,
            "filters": filters,
            "index_type": index_type,
        })
        # Collect all events from the stream
        events = []
        try:
            logger.debug("companion: starting async_stream_query user_id=%s session_id=%s", user_id, session_id)
            stream_start = time.time()
            stream = companion_remote_app.async_stream_query(
                user_id=user_id,
                session_id=session_id,
                message=payload,
            )
            first_event_received = False
            async for event in stream:
                if not first_event_received:
                    logger.debug("companion: TIME TO FIRST RESPONSE %.2fs", time.time() - request_start_time)
                    first_event_received = True
                logger.debug("companion: event=%s", event)
                events.append(event)
            logger.debug("companion: stream_query took %.2fs | events_count=%d", time.time() - stream_start, len(events))
        except Exception as e:
            logger.exception("companion: async_stream_query failed")
            raise HTTPException(
                status_code=500, 
                detail=f"Error during stream query: {str(e)}"
            )
        
        # Extract text and tool results from all events
        process_start = time.time()
        text_parts = []
        tool_result: dict = {}
        
        for event in events:
            logger.debug("companion: event=%s", event)
            # Skip partial streaming chunks — only use the final consolidated event
            if event.get("partial"):
                continue
            if "content" in event and "parts" in event["content"]:
                parts = event["content"]["parts"]
                for part in parts:
                    if "text" in part and not part.get("thought"):
                        text_parts.append(part["text"])
                    # Support both snake_case (Vertex AI) and camelCase (local adk api_server)
                    func_resp = part.get("function_response") or part.get("functionResponse")
                    if func_resp:
                        response_payload = func_resp.get("response")
                        if isinstance(response_payload, dict):
                            tool_result = response_payload
                        elif response_payload is not None:
                            tool_result = {"response": response_payload}
        
        # Combine all text parts into final message
        final_message = " ".join(text_parts).strip()
        
        # If no text response but we have tool results, create a message
        if not final_message and tool_result:
            if "error" in tool_result:
                final_message = f"Search completed but encountered an issue: {tool_result.get('error', 'Unknown error')}"
            elif "requests" in tool_result and len(tool_result.get("requests", [])) == 0:
                final_message = f"Search completed but no products were found. {tool_result.get('error', '')}"
            else:
                final_message = "Search completed successfully."
        
        # Handle delegation to chat_agent (backend routing)
        if tool_result.get("status") == "delegated_to_chat_agent":
            delegation_type = tool_result.get("delegation_type", "new_search")
            delegated_query = tool_result.get("delegated_query", message)
            delegated_gender = tool_result.get("gender", "Women")
            logger.info(
                "companion: delegating to chat_agent type=%s query=%s",
                delegation_type, delegated_query,
            )

            chat_payload = json.dumps({
                "message": delegated_query,
                "gender": delegated_gender,
            })
            chat_text_parts = []
            chat_tool_result: dict = {}
            try:
                chat_stream = chat_remote_app.async_stream_query(
                    user_id=user_id,
                    session_id=chat_session_id,
                    message=chat_payload,
                )
                async for evt in chat_stream:
                    if evt.get("partial"):
                        continue
                    if "content" in evt and "parts" in evt["content"]:
                        for p in evt["content"]["parts"]:
                            if "text" in p and not p.get("thought"):
                                chat_text_parts.append(p["text"])
                            fr = p.get("function_response") or p.get("functionResponse")
                            if fr:
                                rp = fr.get("response")
                                if isinstance(rp, dict):
                                    chat_tool_result = rp
                                elif rp is not None:
                                    chat_tool_result = {"response": rp}
            except Exception as del_exc:
                logger.exception("companion: delegation to chat_agent failed")
                return CompanionResponse(
                    message="Sorry, I couldn't process your request right now.",
                    session_id=session_id,
                    result={"error": str(del_exc), "status": "delegation_failed"},
                )

            # Save delegated result to Firestore
            if chat_tool_result and chat_tool_result.get("journey_name"):
                try:
                    fs_client = _initialize_firebase()
                    del_payload = {
                        "journey_name": chat_tool_result.get("journey_name", ""),
                        "updated_at": fs_module.SERVER_TIMESTAMP,
                    }
                    aq = chat_tool_result.get("algolia_query")
                    if aq is not None:
                        try:
                            del_payload["algolia_query"] = json.dumps(aq)
                        except Exception:
                            pass
                    if chat_tool_result.get("search_term"):
                        del_payload["search_term"] = chat_tool_result["search_term"]
                    if chat_tool_result.get("filters"):
                        del_payload["filters"] = chat_tool_result["filters"]
                    if chat_tool_result.get("index_type"):
                        del_payload["index_type"] = chat_tool_result["index_type"]
                    if chat_tool_result.get("query_type"):
                        del_payload["query_type"] = chat_tool_result["query_type"]
                    fs_client.collection("chatsessionQueries").document(chat_session_id).set(del_payload, merge=True)
                except Exception as fs_exc:
                    logger.warning("companion: delegation firestore save failed: %s", fs_exc)

            del_message = " ".join(chat_text_parts).strip()
            if not del_message:
                del_message = final_message or "Here are some options for you."

            logger.debug("companion: delegation took %.2fs total", time.time() - request_start_time)
            return CompanionResponse(
                message=del_message,
                session_id=session_id,
                result=chat_tool_result or tool_result,
            )

        # If query_type is "filter", remove journey_name from result
        if tool_result.get("query_type") == "filter" and "journey_name" in tool_result:
            del tool_result["journey_name"]

        # Build response
        logger.debug("companion: result processing took %.2fs", time.time() - process_start)
        logger.info("companion: final_message=%s", final_message)
        logger.debug("companion: TOTAL REQUEST TIME %.2fs", time.time() - request_start_time)
        return CompanionResponse(
            message=final_message,
            session_id=session_id,
            result=tool_result,
        )
        
    except HTTPException:
        logger.exception("companion: HTTPException raised")
        raise
    except Exception as e:
        logger.exception("companion: unexpected exception")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Image Search Endpoint
# =============================================================================

@router.post("/image-search", response_model=ImageSearchResponse)
async def image_search(
    image_url: Optional[str] = Form(None, description="Image URL (http/https/gs)"),
    file: Optional[UploadFile] = File(None, description="Image file upload"),
    text_message: Optional[str] = Form(None, description="Optional user text message/context"),
    gender: Optional[str] = Form(None, description="Gender filter"),
    session_id: Optional[str] = Form(None, description="Session ID (auto-generated if not provided)"),
    use_boosting: bool = Form(True, description="Use imageLabels for boosting"),
    extra_filters: Optional[str] = Form(None, description="Additional Algolia filters"),
    _: dict = Depends(verify_bearer_token)
):
    """
    Search for products using an image.
    
    Provide either:
    - `image_url`: URL to an image (http, https, or gs://)
    - `file`: Upload an image file (JPEG, PNG, WebP, GIF)
    """
    try:
        request_start_time = time.time()
        # Generate session_id if not provided
        if not session_id:
            session_id = str(uuid.uuid4().int)[:19]
        
        # Validate input
        if not image_url and not file:
            raise HTTPException(status_code=400, detail="Provide either 'image_url' or 'file'")
        
        if image_url and file:
            raise HTTPException(status_code=400, detail="Provide either 'image_url' or 'file', not both")
        
        # Process input into Parts for the image_search_agent
        process_input_start = time.time()
        if not image_remote_app:
            # Fallback to legacy local search when image agent engine not configured
            if image_url:
                image_input = image_url
                logger.info(f"[image_search] session={session_id} URL: {image_url[:50]}...")
            else:
                if file.content_type not in ALLOWED_IMAGE_TYPES:
                    raise HTTPException(status_code=400, detail=f"Invalid file type: {file.content_type}")
                content = await file.read()
                image_input = f"data:{file.content_type};base64,{base64.b64encode(content).decode()}"
                logger.info(f"[image_search] session={session_id} File: {file.filename}")
            logger.debug(f"[image_search] input processing took {time.time() - process_input_start:.2f}s (legacy)")
            # Legacy local search
            search_start = time.time()
            result = search_by_image(
                image_input=image_input,
                gender=gender,
                use_optional_filters=use_boosting,
                additional_filter_string=extra_filters
            )
            logger.debug(f"[image_search] search_by_image took {time.time() - search_start:.2f}s")
            logger.debug(f"[image_search] result={result}")
            if result["success"]:
                logger.info(f"[image_search] Success: session={session_id} found {result['total_found']} products")
                logger.debug(f"[image_search] TOTAL REQUEST TIME {time.time() - request_start_time:.2f}s")
                return ImageSearchResponse(
                    message=result.get("message") or "Here are some products I found based on the image you sent",
                    session_id=session_id,
                    result=ImageSearchResult(
                        journey_name=result["journey_name"],
                        requests=result["requests"],
                        status=result["status"],
                        total_found=result["total_found"],
                        returned=result["returned"],
                        filters=result["filters"],
                        optional_filters=result["optional_filters"]
                    )
                )
            else:
                logger.info(f"[image_search] No results: session={session_id} error={result.get('error')}")
                logger.debug(f"[image_search] TOTAL REQUEST TIME {time.time() - request_start_time:.2f}s")
                return ImageSearchResponse(
                    message="Sorry, I couldn't find any products matching your image",
                    session_id=session_id,
                    result=ImageSearchResult(
                        journey_name=result["journey_name"],
                        requests=[],
                        status=result["status"],
                        total_found=0,
                        returned=0,
                        filters=result.get("filters", {}),
                        optional_filters=result.get("optional_filters", {})
                    ),
                    error=result.get("error")
                )

        # Modern path: call image_search_agent via Agent Engine with Parts
        parts = []

        def infer_mime_from_name(name: str) -> str:
            n = (name or "").lower()
            if n.endswith(".png"): return "image/png"
            if n.endswith(".webp"): return "image/webp"
            if n.endswith(".gif"): return "image/gif"
            return "image/jpeg"

        if image_url:
            s = image_url.strip()
            if s.startswith("data:") and "," in s:
                header, b64 = s.split(",", 1)
                mime = header.split(":")[1].split(";")[0]
                try:
                    data_bytes = base64.b64decode(b64)
                except Exception:
                    raise HTTPException(status_code=400, detail="Invalid data URL encoding")
                parts.append(genai_types.Part.from_bytes(data=data_bytes, mime_type=mime))
            elif s.startswith("http://") or s.startswith("https://") or s.startswith("gs://"):
                mime = infer_mime_from_name(s)
                parts.append(genai_types.Part.from_uri(file_uri=s, mime_type=mime))
            else:
                raise HTTPException(status_code=400, detail="Unsupported image_url format")
            logger.info(f"[image_search] session={session_id} URL->Parts: {image_url[:50]}...")
        else:
            if file.content_type not in ALLOWED_IMAGE_TYPES:
                raise HTTPException(status_code=400, detail=f"Invalid file type: {file.content_type}")
            content = await file.read()
            parts.append(genai_types.Part.from_bytes(data=content, mime_type=file.content_type))
            logger.info(f"[image_search] session={session_id} File->Parts: {file.filename}")

        # Add the text message as a formatted string with gender
        text_part_str = f"text_message:{text_message or ''}, gender:{gender or ''}"
        parts.insert(0, genai_types.Part.from_text(text=text_part_str))

        logger.debug(f"[image_search] input processing took {time.time() - process_input_start:.2f}s (parts)")

        # Ensure session exists on remote image agent
        if not session_id:
            logger.info("image_search: creating new remote session for image agent")
            img_session = await image_remote_app.async_create_session(user_id="image_user")
            session_id = img_session.get("id") or img_session.get("name") or img_session.get("session_id")
            if not session_id:
                raise HTTPException(status_code=500, detail="Failed to create image agent session")

        # Stream query to image agent
        events = []
        try:
            stream = image_remote_app.async_stream_query(
                user_id="image_user",
                session_id=session_id,
                # Per ADK docs, pass a list of Parts for multimodal inputs
                message=parts,
            )
            async for event in stream:
                events.append(event)
        except Exception as e:
            logger.exception("[image_search] image agent async_stream_query failed")
            raise HTTPException(status_code=500, detail=f"Image agent error: {e}")

        # Extract tool results
        text_parts = []
        tool_result: dict = {}
        for event in events:
            if "content" in event and "parts" in event["content"]:
                for part in event["content"]["parts"]:
                    if "text" in part and not part.get("thought"):
                        text_parts.append(part["text"])
                    elif "function_response" in part:
                        resp = part["function_response"].get("response")
                        if isinstance(resp, dict):
                            tool_result = resp
                        elif resp is not None:
                            tool_result = {"response": resp}

        final_message = " ".join(text_parts).strip() or ""
        if tool_result.get("status") == "success":
            return ImageSearchResponse(
                message=final_message or "Here are similar products",
                session_id=session_id,
                result=ImageSearchResult(
                    journey_name=tool_result.get("journey_name", "image search"),
                    requests=tool_result.get("requests", []),
                    status=tool_result.get("status", "success"),
                    total_found=tool_result.get("total_found", 0),
                    returned=tool_result.get("returned", 0),
                    filters=tool_result.get("filters", {}),
                    optional_filters=tool_result.get("optional_filters", {}),
                ),
            )
        else:
            return ImageSearchResponse(
                message=final_message or "Sorry, I couldn't find any products matching your image",
                session_id=session_id,
                result=ImageSearchResult(
                    journey_name=tool_result.get("journey_name", "image search"),
                    requests=tool_result.get("requests", []),
                    status=tool_result.get("status", "error"),
                    total_found=tool_result.get("total_found", 0),
                    returned=tool_result.get("returned", 0),
                    filters=tool_result.get("filters", {}),
                    optional_filters=tool_result.get("optional_filters", {}),
                ),
                error=tool_result.get("error")
            )     
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("[image_search] Error")
        raise HTTPException(status_code=500, detail=str(e))

