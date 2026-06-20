from __future__ import annotations

from datetime import datetime
from pathlib import Path

import click
import frontmatter

from social_agent.agents.ideator import IdeatorAgent
from social_agent.agents.writer import WriterAgent
from social_agent.collectors import LinkScraperCollector, RSSCollector, WebScraperCollector
from social_agent.collectors.social import LinkedInCollector, TwitterCollector
from social_agent.config import settings
from social_agent.models.draft import Draft, DraftStatus
from social_agent.models.idea import Idea, IdeaStatus
from social_agent.models.seed import Seed, SeedStatus
from social_agent.models.source import Source, SourceType
from social_agent.storage import (
    get_draft_repository,
    get_idea_repository,
    get_seed_repository,
    get_source_repository,
)
from social_agent.utils import html_to_markdown

DATA_DIR = settings.data_dir.resolve()
SEEDS_DIR = DATA_DIR / "seeds"
IDEAS_DIR = DATA_DIR / "ideas"
DRAFTS_DIR = DATA_DIR / "drafts"
SOURCES_DIR = DATA_DIR / "sources"

seed_store = get_seed_repository()
idea_store = get_idea_repository()
draft_store = get_draft_repository()
source_store = get_source_repository()


@click.group()
def cli() -> None:
    """social-agent: Sistema de agentes para redes sociales."""


# ── LinkedIn Auth ──


@cli.group()
def linkedin() -> None:
    """LinkedIn authentication and tools."""


@linkedin.command("auth")
@click.option("--save", is_flag=True, help="Save token to .env file")
@click.option("--env-file", default=".env", help="Path to .env file (default: .env)")
@click.option("--port", default=8080, type=int,
              help="Port for OAuth callback server (default: 8080)")
def linkedin_auth(save: bool, env_file: str, port: int) -> None:
    """Authorize with LinkedIn and get an access token."""
    import asyncio

    if not settings.linkedin_client_id or not settings.linkedin_client_secret:
        click.echo(
            "LinkedIn client ID and secret not configured.\n"
            "Set SOCIAL_AGENT_LINKEDIN_CLIENT_ID and "
            "SOCIAL_AGENT_LINKEDIN_CLIENT_SECRET in .env"
        )
        return

    from .linkedin_auth import auth_flow

    asyncio.run(auth_flow(
        client_id=settings.linkedin_client_id,
        client_secret=settings.linkedin_client_secret,
        port=port,
        save=save,
        env_file=env_file,
    ))


# ── Sources ──


@cli.group()
def sources() -> None:
    """Manage information sources."""


@sources.command("list")
def sources_list() -> None:
    """List all configured sources."""
    items = source_store.list()
    if not items:
        click.echo("No sources configured.")
        return
    for s in items:
        click.echo(f"  [{s.id}] {s.name} ({s.source_type.value}) - priority {s.priority.value}")


@sources.command("add")
@click.argument("name")
@click.argument("source_type")
@click.argument("url")
@click.option("--priority", default=2, type=int, help="Priority 1 (high) to 3 (low)")
@click.option("--tags", default="", help="Comma-separated tags")
@click.option("--config", default="", help='JSON config (e.g. \'{"url_pattern":"/blog/.+","max_items":5}\')')
def sources_add(name: str, source_type: str, url: str, priority: int, tags: str, config: str) -> None:
    """Add a new information source."""
    import json

    from social_agent.models.source import SourcePriority, SourceType

    parsed_config = json.loads(config) if config else {}
    source = Source(
        name=name,
        source_type=SourceType(source_type),
        url=url,
        priority=SourcePriority(priority),
        tags=[t.strip() for t in tags.split(",") if t.strip()],
        config=parsed_config,
    )
    path = source_store.save(source)
    click.echo(f"Source added: {source.id}")
    click.echo(f"  Saved to: {path}")


# ── Seeds ──


@cli.group()
def seeds() -> None:
    """Manage collected articles (seeds)."""


def _build_collector(source: Source):
    match source.source_type:
        case SourceType.rss:
            return RSSCollector(source.id, source.name, source.url, source.tags, config=source.config)
        case SourceType.webpage:
            return WebScraperCollector(source.id, source.name, source.url, source.tags)
        case SourceType.link_scraper:
            return LinkScraperCollector(source.id, source.name, source.url, source.tags, config=source.config)
        case SourceType.social:
            if "twitter" in source.url:
                return TwitterCollector(
                    source.id, source.name, source.url, source.tags,
                    bearer_token=settings.twitter_bearer_token,
                )
            if "linkedin" in source.url:
                return LinkedInCollector(
                    source.id, source.name, source.url, source.tags,
                    access_token=settings.linkedin_access_token,
                )
            return None
        case _:
            return None


@seeds.command("generate")
@click.option("--source-id", multiple=True, help="Filter by source ID(s) (may be repeated)")
@click.option("--force", is_flag=True, help="Allow duplicate seeds for same URL")
def seeds_generate(source_id: tuple[str, ...], force: bool) -> None:
    """Collect articles from sources and save as seeds."""
    sources = source_store.list(filter_fn=lambda s: s.enabled)
    if source_id:
        sources = [s for s in sources if s.id in source_id]
        missing = [sid for sid in source_id if sid not in {s.id for s in sources}]
        if missing:
            click.echo(f"Source(s) not found or not enabled: {', '.join(missing)}")
            return

    if not sources:
        click.echo("No enabled sources found. Add one first: social-agent sources add ...")
        return

    existing_urls: set[str] = set()
    if not force:
        existing = seed_store.list()
        existing_urls = {
            s.source_url for s in existing
            if s.source_url and s.status in (SeedStatus.pending, SeedStatus.approved)
        }

    created = 0
    skipped = 0
    for src in sources:
        collector = _build_collector(src)
        if collector is None:
            continue
        click.echo(f"Fetching: {src.name} ({src.source_type.value})...")
        try:
            items = collector.fetch()
            click.echo(f"  -> {len(items)} items")
            for item in items:
                if not force and item.url and item.url in existing_urls:
                    click.echo(f"  Skipped (duplicate URL): {item.title}")
                    skipped += 1
                    continue
                content = html_to_markdown(item.content)
                seed = Seed(
                    title=item.title,
                    content=content,
                    source_id=item.source_id,
                    source_url=item.url,
                    source_name=item.source_name,
                    tags=item.tags,
                )
                seed_store.save(seed)
                created += 1
                preview = seed.content[:80].replace("\n", " ")
                click.echo(f"  Created: {seed.id} - {seed.title}")
                click.echo(f"    {preview}...")
        except Exception as e:
            click.echo(f"  -> Error: {e}")

    click.echo(f"\nDone. {created} seeds created ({skipped} duplicates skipped).")


@seeds.command("list")
@click.option("--status", default=None, help="Filter by status (pending, approved, used, discarded)")
def seeds_list(status: str | None) -> None:
    """List collected seeds."""
    def _match_status(s: Seed) -> bool:
        return s.status.value == status

    filter_fn = _match_status if status else None
    items = seed_store.list(filter_fn)
    if not items:
        click.echo("No seeds found.")
        return
    for s in items:
        click.echo(f"  [{s.id}] {s.title} ({s.status.value})")


@seeds.command("show")
@click.argument("seed_id")
def seeds_show(seed_id: str) -> None:
    """Show a collected seed."""
    seed = seed_store.get(seed_id)
    if not seed:
        click.echo(f"Seed '{seed_id}' not found.")
        return
    click.echo(f"ID:        {seed.id}")
    click.echo(f"Title:     {seed.title}")
    click.echo(f"Status:    {seed.status.value}")
    click.echo(f"Source:    {seed.source_url or seed.source_id or '(none)'}")
    click.echo(f"Source:    {seed.source_name}")
    click.echo(f"Tags:      {', '.join(seed.tags) if seed.tags else '(none)'}")
    click.echo("─" * 40)
    click.echo(seed.content[:2000] if seed.content else "(empty)")
    if len(seed.content) > 2000:
        click.echo(f"... ({len(seed.content) - 2000} more characters)")


@seeds.command("approve")
@click.argument("seed_id")
def seeds_approve(seed_id: str) -> None:
    """Approve a seed for idea generation."""
    seed = seed_store.get(seed_id)
    if not seed:
        click.echo(f"Seed '{seed_id}' not found.")
        return
    if seed.status != SeedStatus.pending:
        click.echo(f"Seed '{seed_id}' is {seed.status.value}. Only pending seeds can be approved.")
        return
    seed.status = SeedStatus.approved
    seed_store.save(seed)
    click.echo(f"Seed '{seed_id}' approved.")


@seeds.command("discard")
@click.argument("seed_id")
def seeds_discard(seed_id: str) -> None:
    """Discard a seed."""
    seed = seed_store.get(seed_id)
    if not seed:
        click.echo(f"Seed '{seed_id}' not found.")
        return
    seed.status = SeedStatus.discarded
    seed_store.save(seed)
    click.echo(f"Seed '{seed_id}' discarded.")


# ── Ideas ──


@cli.group()
def ideas() -> None:
    """Manage generated ideas."""


@ideas.command("generate")
@click.argument("seed_id")
@click.option("--interests", default=None, help="Path to interests prompt file")
@click.option("--dry-run", is_flag=True, help="Show raw LLM response without saving")
def ideas_generate(seed_id: str, interests: str | None, dry_run: bool) -> None:
    """Generate an idea from an approved seed."""
    seed = seed_store.get(seed_id)
    if not seed:
        click.echo(f"Seed '{seed_id}' not found.")
        return

    if seed.status != SeedStatus.approved:
        click.echo(f"Seed '{seed_id}' is {seed.status.value}. Only approved seeds can generate ideas.")
        return

    interests_path = Path(interests) if interests else settings.prompts_dir / "interests.md"
    if not interests_path.exists():
        click.echo(f"Interests file not found: {interests_path}")
        return

    with open(interests_path) as f:
        post = frontmatter.load(f)
        interests_text = post.content.strip()

    click.echo(f"Generating idea from seed '{seed_id}'...")
    ideator = IdeatorAgent()
    result = ideator.generate_idea(seed, interests_text, dry_run=dry_run)

    if dry_run:
        import textwrap
        click.echo("\n── Raw LLM response ──")
        click.echo(textwrap.indent(str(result), "  "))
        click.echo("─────────────────────")
        return

    if result is None:
        click.echo("Ideator returned an invalid response.")
        return

    idea_store.save(result)
    seed.status = SeedStatus.used
    seed_store.save(seed)
    click.echo(f"  Created: {result.id} - {result.title}")
    click.echo(f"  Summary: {result.summary}")


@ideas.command("list")
@click.option("--status", default=None, help="Filter by status (pending, used, discarded)")
def ideas_list(status: str | None) -> None:
    """List generated ideas."""
    def _match_status(i: Idea) -> bool:
        return i.status.value == status

    filter_fn = _match_status if status else None
    items = idea_store.list(filter_fn)
    if not items:
        click.echo("No ideas found.")
        return
    for i in items:
        click.echo(f"  [{i.id}] {i.title} ({i.status.value})")


@ideas.command("show")
@click.argument("idea_id")
def ideas_show(idea_id: str) -> None:
    """Show a generated idea."""
    idea = idea_store.get(idea_id)
    if not idea:
        click.echo(f"Idea '{idea_id}' not found.")
        return
    click.echo(f"ID:        {idea.id}")
    click.echo(f"Seed ID:   {idea.seed_id}")
    click.echo(f"Title:     {idea.title}")
    click.echo(f"Status:    {idea.status.value}")
    click.echo(f"Source:    {idea.source_url or '(none)'}")
    click.echo(f"Summary:   {idea.summary}")
    if idea.comment:
        click.echo(f"Comment:   {idea.comment}")


@ideas.command("comment")
@click.argument("idea_id")
@click.argument("text", required=False)
@click.option("--clear", is_flag=True, help="Eliminar el comentario")
def ideas_comment(idea_id: str, text: str | None, clear: bool) -> None:
    """Fija o elimina el comentario del autor en una idea.

    El comentario se incluye en el prompt del agente escritor, separado del
    resumen de la noticia, para aportar contexto o instrucciones de enfoque.

    Ejemplos:

      social-agent ideas comment idea_123 "estaré probando este modelo esta semana"
      social-agent ideas comment idea_123 --clear
    """
    idea = idea_store.get(idea_id)
    if not idea:
        click.echo(f"Idea '{idea_id}' not found.")
        return

    if clear:
        idea.comment = None
        idea_store.save(idea)
        click.echo(f"Comment cleared from idea '{idea_id}'.")
        return

    if not text:
        click.echo("Provide the comment text or use --clear to remove it.")
        return

    idea.comment = text
    idea_store.save(idea)
    click.echo(f"Comment set on idea '{idea_id}'.")


@ideas.command("discard")
@click.argument("idea_id")
def ideas_discard(idea_id: str) -> None:
    """Discard a generated idea."""
    idea = idea_store.get(idea_id)
    if not idea:
        click.echo(f"Idea '{idea_id}' not found.")
        return
    idea.status = IdeaStatus.discarded
    idea_store.save(idea)
    click.echo(f"Idea '{idea_id}' discarded.")


# ── Drafts ──


@cli.group()
def drafts() -> None:
    """Manage post drafts."""


@drafts.command("generate")
@click.argument("idea_id")
@click.option("--platform", "-p", multiple=True, help="Target platform(s)")
@click.option("--dry-run", is_flag=True, help="Show raw LLM response without saving")
def drafts_generate(idea_id: str, platform: tuple[str, ...], dry_run: bool) -> None:
    """Generate drafts from an idea for one or more platforms."""
    idea = idea_store.get(idea_id)
    if not idea:
        click.echo(f"Idea '{idea_id}' not found.")
        return

    if idea.status != IdeaStatus.pending:
        click.echo(f"Idea '{idea_id}' is {idea.status.value}. Only pending ideas can be used.")
        return

    platforms_dir = settings.prompts_dir / "platforms"
    if not platforms_dir.exists():
        click.echo(f"No platform prompts found in {platforms_dir}")
        return

    available = sorted(p.stem for p in platforms_dir.glob("*.md"))
    if not platform:
        platform = tuple(available)

    if not platform:
        click.echo("No platforms available.")
        return

    writer = WriterAgent()
    created = []

    for p in platform:
        if p not in available:
            click.echo(f"Platform '{p}' not found in {platforms_dir}, skipping.")
            continue

        path = platforms_dir / f"{p}.md"
        with open(path) as f:
            post = frontmatter.load(f)

        instructions = post.content.strip()
        platform_name = post.metadata.get("title", p)
        max_chars = post.metadata.get("max_chars", 0)

        click.echo(f"Generating {p} draft...")
        result = writer.generate_draft(
            idea=idea,
            platform=p,
            platform_instructions=instructions,
            platform_name=platform_name,
            max_chars=max_chars,
            dry_run=dry_run,
        )

        if dry_run:
            click.echo(f"\n── {p} draft ──")
            click.echo(str(result))
            click.echo("─────" + "─" * len(p) + "──────")
        elif result is None:
            click.echo(f"  Failed: LLM returned empty content for {p} after retry")
        else:
            draft_store.save(result)
            click.echo(f"  Created: {result.id}")
            created.append(result)

    if not dry_run:
        idea.status = IdeaStatus.used
        idea_store.save(idea)
        click.echo(f"\nDone. {len(created)} draft(s) generated from idea '{idea_id}'.")


@drafts.command("list")
@click.option("--platform", default=None, help="Filter by platform")
@click.option("--status", default=None, help="Filter by status")
def drafts_list(platform: str | None, status: str | None) -> None:
    """List post drafts."""
    def filter_fn(d: Draft) -> bool:
        if platform and d.platform != platform:
            return False
        if status and d.status.value != status:
            return False
        return True

    items = draft_store.list(filter_fn)
    if not items:
        click.echo("No drafts found.")
        return
    for d in items:
        click.echo(f"  [{d.id}] ({d.platform}) {d.status.value}")


@drafts.command("show")
@click.argument("draft_id")
def drafts_show(draft_id: str) -> None:
    """Show a post draft."""
    draft = draft_store.get(draft_id)
    if not draft:
        click.echo(f"Draft '{draft_id}' not found.")
        return
    click.echo(f"ID:       {draft.id}")
    click.echo(f"Idea ID:  {draft.idea_id}")
    click.echo(f"Platform: {draft.platform}")
    click.echo(f"Status:   {draft.status.value}")
    click.echo(f"Notes:    {draft.notes or ''}")
    click.echo("─" * 40)
    click.echo(draft.content)


@drafts.command("approve")
@click.argument("draft_id")
def drafts_approve(draft_id: str) -> None:
    """Approve a draft for publishing."""
    draft = draft_store.get(draft_id)
    if not draft:
        click.echo(f"Draft '{draft_id}' not found.")
        return
    draft.status = DraftStatus.approved
    draft_store.save(draft)
    click.echo(f"Draft '{draft_id}' approved.")


@drafts.command("reject")
@click.argument("draft_id")
@click.option("--notes", default="", help="Reason for rejection")
def drafts_reject(draft_id: str, notes: str) -> None:
    """Reject a draft."""
    draft = draft_store.get(draft_id)
    if not draft:
        click.echo(f"Draft '{draft_id}' not found.")
        return
    draft.status = DraftStatus.rejected
    draft.notes = notes or draft.notes
    draft_store.save(draft)
    click.echo(f"Draft '{draft_id}' rejected.")


@drafts.command("edit")
@click.argument("draft_id")
@click.argument("new_content")
def drafts_edit(draft_id: str, new_content: str) -> None:
    """Edit draft content (pass new content as argument)."""
    draft = draft_store.get(draft_id)
    if not draft:
        click.echo(f"Draft '{draft_id}' not found.")
        return
    draft.content = new_content
    draft.status = DraftStatus.draft
    draft_store.save(draft)
    click.echo(f"Draft '{draft_id}' updated.")


@drafts.command("publish")
@click.argument("draft_id")
@click.option("--media-url", multiple=True, help="URL of image to attach (may be repeated)")
@click.option("--media-path", multiple=True, help="Local path of image to attach (may be repeated)")
def drafts_publish(draft_id: str, media_url: tuple[str, ...], media_path: tuple[str, ...]) -> None:
    """Publish a draft to its social media platform."""
    from social_agent.publishers.linkedin import LinkedInPublisher
    from social_agent.publishers.twitter import TwitterPublisher

    draft = draft_store.get(draft_id)
    if not draft:
        click.echo(f"Draft '{draft_id}' not found.")
        return
    if draft.status != DraftStatus.approved:
        click.echo("Only approved drafts can be published. Use 'approve' first.")
        return

    if draft.platform == "twitter":
        if not all([
            settings.twitter_api_key,
            settings.twitter_api_secret,
            settings.twitter_access_token,
            settings.twitter_access_token_secret,
        ]):
            click.echo("Twitter credentials not configured. Set SOCIAL_AGENT_TWITTER_API_KEY, etc.")
            return
        publisher = TwitterPublisher(
            consumer_key=settings.twitter_api_key,
            consumer_secret=settings.twitter_api_secret,
            access_token=settings.twitter_access_token,
            access_token_secret=settings.twitter_access_token_secret,
        )
    elif draft.platform == "linkedin":
        if not settings.linkedin_access_token:
            click.echo(
                "LinkedIn access token not configured. "
                "Set SOCIAL_AGENT_LINKEDIN_ACCESS_TOKEN"
            )
            return
        publisher = LinkedInPublisher(
            access_token=settings.linkedin_access_token,
            author_urn=settings.linkedin_author_urn,
        )
    else:
        click.echo(f"Unknown platform '{draft.platform}'.")
        return

    if media_url:
        draft.media_urls = list(media_url)
    if media_path:
        draft.media_paths = list(media_path)
    draft.publish_attempts += 1
    result = publisher.publish(draft)

    if result.success:
        draft.status = DraftStatus.published
        draft.platform_post_id = result.platform_post_id
        draft.published_at = result.published_at
        draft.publish_error = None
        draft_store.save(draft)
        click.echo(
            f"Draft '{draft_id}' published to {draft.platform} "
            f"(id: {result.platform_post_id})."
        )
    else:
        draft.status = DraftStatus.failed
        draft.publish_error = result.error
        draft_store.save(draft)
        click.echo(f"Failed to publish draft '{draft_id}': {result.error}")


# ── Schedule ──


@cli.group()
def schedule() -> None:
    """Schedule drafts for future publishing."""


def _parse_scheduled_at(raw: str) -> datetime:
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        raise click.BadParameter(
            "Invalid datetime format. Use ISO 8601, e.g. '2026-06-20T15:30:00' "
            "(optionally with timezone)."
        )


@schedule.command("set")
@click.argument("draft_id")
@click.argument("scheduled_at")
def schedule_set(draft_id: str, scheduled_at: str) -> None:
    """Set a publication time for a draft (ISO 8601 datetime)."""
    draft = draft_store.get(draft_id)
    if not draft:
        click.echo(f"Draft '{draft_id}' not found.")
        return
    if draft.status == DraftStatus.published:
        click.echo("Cannot schedule a draft that is already published.")
        return

    when = _parse_scheduled_at(scheduled_at)
    draft.scheduled_at = when
    draft.status = DraftStatus.approved
    draft_store.save(draft)
    click.echo(f"Draft '{draft_id}' scheduled for {when.isoformat()}.")


@schedule.command("list")
def schedule_list() -> None:
    """List scheduled drafts."""
    items = [d for d in draft_store.list() if d.scheduled_at is not None]
    if not items:
        click.echo("No scheduled drafts.")
        return
    items.sort(key=lambda d: d.scheduled_at)
    for d in items:
        click.echo(f"  [{d.id}] ({d.platform}) {d.status.value} -> {d.scheduled_at.isoformat()}")


@schedule.command("cancel")
@click.argument("draft_id")
def schedule_cancel(draft_id: str) -> None:
    """Remove the schedule from a draft."""
    draft = draft_store.get(draft_id)
    if not draft:
        click.echo(f"Draft '{draft_id}' not found.")
        return
    if draft.scheduled_at is None:
        click.echo(f"Draft '{draft_id}' is not scheduled.")
        return
    draft.scheduled_at = None
    draft_store.save(draft)
    click.echo(f"Schedule cancelled for draft '{draft_id}'.")


@schedule.command("publish")
def schedule_publish() -> None:
    """Publish all drafts whose scheduled time has arrived."""
    from social_agent.scheduler import run_once

    results = run_once(draft_store)
    if not results:
        click.echo("No drafts due for publishing.")
        return
    published = 0
    failed = 0
    for r in results:
        if r.success:
            published += 1
            click.echo(f"  Published: {r.draft_id} ({r.platform}) -> {r.platform_post_id}")
        else:
            failed += 1
            click.echo(f"  Failed:    {r.draft_id} ({r.platform}) -> {r.error}")
    click.echo(f"\nDone. {published} published, {failed} failed.")


@schedule.command("worker")
@click.option("--interval", default=300, type=int, help="Check interval in seconds (default: 300)")
def schedule_worker(interval: int) -> None:
    """Run the scheduler worker in the foreground (checks periodically)."""
    import asyncio

    from social_agent.scheduler import run_loop

    click.echo(f"Starting scheduler worker (interval: {interval}s). Press Ctrl+C to stop.")
    try:
        asyncio.run(run_loop(draft_store, interval_seconds=interval))
    except KeyboardInterrupt:
        click.echo("\nScheduler worker stopped.")


# ── Database ──


@cli.group()
def db() -> None:
    """Database management (SQLite migration, etc.)."""


@db.command("migrate")
@click.option(
    "--data-dir",
    default=None,
    type=click.Path(exists=True, file_okay=False),
    help="Source data directory (defaults to settings.data_dir).",
)
@click.option(
    "--sqlite-path",
    default=None,
    type=click.Path(dir_okay=False),
    help="Target SQLite file (defaults to settings.sqlite_path or <data_dir>/social_agent.db).",
)
def db_migrate(data_dir: str | None, sqlite_path: str | None) -> None:
    """Migrate existing Markdown data into the SQLite database."""
    from social_agent.storage.migrate_to_sqlite import migrate

    d = Path(data_dir) if data_dir else None
    s = Path(sqlite_path) if sqlite_path else None
    click.echo("Migrating Markdown data to SQLite...")
    report = migrate(data_dir=d, sqlite_path=s)
    click.echo(str(report))


if __name__ == "__main__":
    cli()
