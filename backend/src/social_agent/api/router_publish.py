from __future__ import annotations

from fastapi import APIRouter, HTTPException

from social_agent.config import settings
from social_agent.models.draft import Draft, DraftStatus
from social_agent.publishers.linkedin import LinkedInPublisher
from social_agent.publishers.twitter import TwitterPublisher
from social_agent.storage.markdown_store import MarkdownStore

DATA_DIR = settings.data_dir.resolve()
draft_store = MarkdownStore[Draft](DATA_DIR / "drafts", Draft)

router = APIRouter(tags=["publish"])


def _get_publisher(platform: str) -> TwitterPublisher | LinkedInPublisher | None:
    if platform == "twitter":
        if not all([
            settings.twitter_api_key,
            settings.twitter_api_secret,
            settings.twitter_access_token,
            settings.twitter_access_token_secret,
        ]):
            return None
        return TwitterPublisher(
            consumer_key=settings.twitter_api_key,
            consumer_secret=settings.twitter_api_secret,
            access_token=settings.twitter_access_token,
            access_token_secret=settings.twitter_access_token_secret,
        )
    if platform == "linkedin":
        if not settings.linkedin_access_token:
            return None
        return LinkedInPublisher(
            access_token=settings.linkedin_access_token,
            author_urn=settings.linkedin_author_urn,
        )
    return None


@router.post("/publish/{draft_id}")
def publish_draft(draft_id: str) -> Draft:
    draft = draft_store.get(draft_id)
    if not draft:
        raise HTTPException(404, f"Draft '{draft_id}' not found")

    if draft.status != DraftStatus.approved:
        msg = f"Draft is {draft.status.value}, only approved drafts can be published"
        raise HTTPException(400, msg)

    publisher = _get_publisher(draft.platform)
    if publisher is None:
        raise HTTPException(400, f"No publisher configured for platform '{draft.platform}'")

    draft.publish_attempts += 1
    result = publisher.publish(draft)

    if result.success:
        draft.status = DraftStatus.published
        draft.platform_post_id = result.platform_post_id
        draft.published_at = result.published_at
        draft.publish_error = None
    else:
        draft.status = DraftStatus.failed
        draft.publish_error = result.error

    draft_store.save(draft)
    return draft
