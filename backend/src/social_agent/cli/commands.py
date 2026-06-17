from __future__ import annotations

from pathlib import Path

import click
import frontmatter

from social_agent.agents.ideator import IdeatorAgent
from social_agent.agents.writer import WriterAgent
from social_agent.collectors import RSSCollector, WebScraperCollector
from social_agent.collectors.social import LinkedInCollector, TwitterCollector
from social_agent.config import settings
from social_agent.models.draft import Draft, DraftStatus
from social_agent.models.seed import Seed, SeedStatus
from social_agent.models.source import Source, SourceType
from social_agent.storage.markdown_store import MarkdownStore

DATA_DIR = Path("data")
SEEDS_DIR = DATA_DIR / "seeds"
DRAFTS_DIR = DATA_DIR / "drafts"
SOURCES_DIR = DATA_DIR / "sources"

seed_store = MarkdownStore[Seed](SEEDS_DIR, Seed)
draft_store = MarkdownStore[Draft](DRAFTS_DIR, Draft)
source_store = MarkdownStore[Source](SOURCES_DIR, Source)


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
def sources_add(name: str, source_type: str, url: str, priority: int, tags: str) -> None:
    """Add a new information source."""
    from social_agent.models.source import SourcePriority, SourceType

    source = Source(
        name=name,
        source_type=SourceType(source_type),
        url=url,
        priority=SourcePriority(priority),
        tags=[t.strip() for t in tags.split(",") if t.strip()],
    )
    path = source_store.save(source)
    click.echo(f"Source added: {source.id}")
    click.echo(f"  Saved to: {path}")


# ── Seeds ──


@cli.group()
def seeds() -> None:
    """Manage seed ideas."""


def _build_collector(source: Source):
    match source.source_type:
        case SourceType.rss:
            return RSSCollector(source.id, source.name, source.url, source.tags)
        case SourceType.webpage:
            return WebScraperCollector(source.id, source.name, source.url, source.tags)
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
@click.option("--interests", default=None, help="Path to interests prompt file")
@click.option("--dry-run", is_flag=True, help="Show raw LLM response without saving seeds")
def seeds_generate(interests: str | None, dry_run: bool) -> None:
    """Generate seed ideas from sources + interests."""
    interests_path = Path(interests) if interests else settings.prompts_dir / "interests.md"
    if not interests_path.exists():
        click.echo(f"Interests file not found: {interests_path}")
        click.echo("Create it from template: cp templates/prompts/interests.md data/prompts/")
        return

    with open(interests_path) as f:
        post = frontmatter.load(f)
        interests_text = post.content.strip()

    sources = source_store.list(filter_fn=lambda s: s.enabled)
    if not sources:
        click.echo("No enabled sources found. Add one first: social-agent sources add ...")
        return

    all_items = []
    for src in sources:
        collector = _build_collector(src)
        if collector is None:
            continue
        click.echo(f"Fetching: {src.name} ({src.source_type.value})...")
        try:
            items = collector.fetch()
            all_items.extend(items)
            click.echo(f"  -> {len(items)} items")
        except Exception as e:
            click.echo(f"  -> Error: {e}")

    if not all_items:
        click.echo("No content collected from any source.")
        return

    click.echo(f"\nGenerating seeds with Ideator ({len(all_items)} items)...")
    ideator = IdeatorAgent()
    result = ideator.generate_seeds(interests_text, all_items, dry_run=dry_run)

    if dry_run:
        import textwrap
        click.echo("\n── Raw LLM response ──")
        click.echo(textwrap.indent(str(result), "  "))
        click.echo("─────────────────────")
        return

    for seed in result:
        seed_store.save(seed)
        click.echo(f"  Created: {seed.id} - {seed.title}")

    click.echo(f"\nDone. {len(result)} seeds generated.")


@seeds.command("list")
@click.option("--status", default=None, help="Filter by status (pending, used, discarded)")
def seeds_list(status: str | None) -> None:
    """List seed ideas."""
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
    """Show a seed idea."""
    seed = seed_store.get(seed_id)
    if not seed:
        click.echo(f"Seed '{seed_id}' not found.")
        return
    click.echo(f"ID:        {seed.id}")
    click.echo(f"Title:     {seed.title}")
    click.echo(f"Status:    {seed.status.value}")
    click.echo(f"Tags:      {', '.join(seed.tags)}")
    click.echo(f"Source:    {seed.source_url or seed.source_id or '(none)'}")
    click.echo(f"Summary:   {seed.summary}")


@seeds.command("discard")
@click.argument("seed_id")
def seeds_discard(seed_id: str) -> None:
    """Discard a seed idea."""
    seed = seed_store.get(seed_id)
    if not seed:
        click.echo(f"Seed '{seed_id}' not found.")
        return
    seed.status = SeedStatus.discarded
    seed_store.save(seed)
    click.echo(f"Seed '{seed_id}' discarded.")


# ── Drafts ──


@cli.group()
def drafts() -> None:
    """Manage post drafts."""


@drafts.command("generate")
@click.argument("seed_id")
@click.option("--platform", "-p", multiple=True, help="Target platform(s)")
@click.option("--dry-run", is_flag=True, help="Show raw LLM response without saving")
def drafts_generate(seed_id: str, platform: tuple[str, ...], dry_run: bool) -> None:
    """Generate drafts from a seed for one or more platforms."""
    seed = seed_store.get(seed_id)
    if not seed:
        click.echo(f"Seed '{seed_id}' not found.")
        return

    if seed.status != SeedStatus.pending:
        click.echo(f"Seed '{seed_id}' is {seed.status.value}. Only pending seeds can be used.")
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
            seed=seed,
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
        else:
            draft_store.save(result)
            click.echo(f"  Created: {result.id}")
            created.append(result)

    if not dry_run:
        seed.status = SeedStatus.used
        seed_store.save(seed)
        click.echo(f"\nDone. {len(created)} draft(s) generated from seed '{seed_id}'.")


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
    click.echo(f"Seed ID:  {draft.seed_id}")
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
def drafts_publish(draft_id: str) -> None:
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


if __name__ == "__main__":
    cli()
