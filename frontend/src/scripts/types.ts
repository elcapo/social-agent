export interface Source {
  id: string;
  name: string;
  source_type: string;
  url: string;
  priority: number;
  tags?: string[];
  config?: Record<string, unknown>;
  enabled?: boolean;
  created_at?: string;
}

export interface Seed {
  id: string;
  title: string;
  content?: string;
  source_name?: string;
  source_url?: string;
  tags?: string[];
  status: string;
  created_at?: string;
}

export interface Idea {
  id: string;
  title: string;
  summary?: string;
  comment?: string;
  seed_id?: string;
  source_url?: string;
  source_name?: string;
  status: string;
  created_at?: string;
}

export interface Draft {
  id: string;
  platform: string;
  idea_id?: string;
  content: string;
  media_urls?: string[];
  media_paths?: string[];
  scheduled_at?: string | null;
  notes?: string;
  status: string;
  publish_error?: string | null;
  publish_attempts?: number;
  platform_post_id?: string | null;
  created_at?: string;
}

export interface ScheduledDraft extends Draft {}

export interface ScheduledItemResult {
  draft_id: string;
  platform: string;
  success: boolean;
  platform_post_id?: string | null;
  error?: string | null;
}

export interface SchedulerResult {
  published: number;
  failed: number;
  results?: ScheduledItemResult[];
}

export interface ScrapeResult {
  title?: string;
  content?: string;
}

export interface ApiError {
  detail?: string | Array<{ msg: string }>;
}
