from __future__ import annotations

from pathlib import Path

import click

from social_agent.models.draft import Draft, DraftStatus
from social_agent.models.seed import Seed, SeedStatus
from social_agent.models.source import Source
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


@seeds.command("list")
@click.option("--status", default=None, help="Filter by status (pending, used, discarded)")
def seeds_list(status: str | None) -> None:
    """List seed ideas."""
    filter_fn = None
    if status:
        filter_fn = lambda s: s.status.value == status

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
    click.echo(f"ID:      {seed.id}")
    click.echo(f"Title:   {seed.title}")
    click.echo(f"Status:  {seed.status.value}")
    click.echo(f"Tags:    {', '.join(seed.tags)}")
    click.echo(f"Summary: {seed.summary}")


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
    """Mark a draft as published."""
    from datetime import datetime

    draft = draft_store.get(draft_id)
    if not draft:
        click.echo(f"Draft '{draft_id}' not found.")
        return
    if draft.status != DraftStatus.approved:
        click.echo("Only approved drafts can be published. Use 'approve' first.")
        return
    draft.status = DraftStatus.published
    draft.published_at = datetime.utcnow()
    draft_store.save(draft)
    click.echo(f"Draft '{draft_id}' published.")


if __name__ == "__main__":
    cli()
