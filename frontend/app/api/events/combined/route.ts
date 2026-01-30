import { NextResponse } from 'next/server';
import { searchEvents } from '@/lib/valyu';
import { getDiscordEvents } from '@/lib/discord-bot';
import { getUserDiscordEvents } from '@/lib/discord-user-reader';
import { classifyEvent } from '@/lib/ai-classifier';
import type { ThreatEvent } from '@/types';

export const dynamic = 'force-dynamic';

const THREAT_QUERIES = [
  'breaking news conflict military',
  'geopolitical crisis tensions',
  'protest demonstration unrest',
  'natural disaster emergency',
  'terrorism attack security',
];

/**
 * GET /api/events/combined
 * Combines events from all sources: Discord, Valyu, RSS, etc.
 */
export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const enableValyu = searchParams.get('valyu') !== 'false';
  const enableDiscord = searchParams.get('discord') !== 'false';

  try {
    const allEvents: ThreatEvent[] = [];

    // 1. Fetch Discord events (if enabled)
    if (enableDiscord && process.env.ENABLE_DISCORD === 'true') {
      try {
        // Try bot events first
        let discordEvents = getDiscordEvents(100);

        // If no bot events, try user reader events
        if (discordEvents.length === 0) {
          discordEvents = getUserDiscordEvents(100);
        }

        allEvents.push(...discordEvents);
        console.log(`[Combined API] Loaded ${discordEvents.length} Discord events`);
      } catch (error) {
        console.error('[Combined API] Discord fetch failed:', error);
      }
    }

    // 2. Fetch Valyu events (if enabled)
    if (enableValyu && process.env.ENABLE_VALYU !== 'false') {
      try {
        const searchResultsArrays = await Promise.all(
          THREAT_QUERIES.map((q) => searchEvents(q, { maxResults: 10 }))
        );

        const allResults = searchResultsArrays.flatMap((r) => r.results);

        // Process Valyu results (simplified from original route)
        for (const result of allResults.slice(0, 50)) {
          const classification = await classifyEvent(result.title, result.content);

          if (classification.location) {
            allEvents.push({
              id: `valyu-${Date.now()}-${Math.random()}`,
              title: result.title,
              summary: result.content.slice(0, 500),
              category: classification.category,
              threatLevel: classification.threatLevel,
              location: classification.location,
              timestamp: result.publishedDate || new Date().toISOString(),
              source: 'Valyu',
              sourceUrl: result.url,
              rawContent: result.content,
            });
          }
        }

        console.log(`[Combined API] Processed ${allEvents.length - (discordEvents?.length || 0)} Valyu events`);
      } catch (error) {
        console.error('[Combined API] Valyu fetch failed:', error);
      }
    }

    // 3. Deduplicate by title
    const uniqueEvents = allEvents.filter(
      (event, index, self) =>
        index === self.findIndex((e) => e.title === event.title)
    );

    // 4. Sort by threat level and date
    const THREAT_PRIORITY: Record<string, number> = {
      critical: 0,
      high: 1,
      medium: 2,
      low: 3,
      info: 4,
    };

    const sortedEvents = uniqueEvents.sort((a, b) => {
      const priorityDiff =
        (THREAT_PRIORITY[a.threatLevel] ?? 5) - (THREAT_PRIORITY[b.threatLevel] ?? 5);
      if (priorityDiff !== 0) return priorityDiff;

      return new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime();
    });

    return NextResponse.json({
      events: sortedEvents,
      count: sortedEvents.length,
      sources: {
        discord: enableDiscord ? allEvents.filter((e) => e.source.startsWith('Discord')).length : 0,
        valyu: enableValyu ? allEvents.filter((e) => e.source === 'Valyu').length : 0,
      },
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error('[Combined API] Error:', error);
    return NextResponse.json(
      { error: 'Failed to fetch combined events' },
      { status: 500 }
    );
  }
}
