import { NextResponse } from 'next/server';
import { getDiscordEvents } from '@/lib/discord-bot';

export const dynamic = 'force-dynamic';

/**
 * GET /api/events/discord
 * Returns events collected from Discord channels
 */
export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const limit = parseInt(searchParams.get('limit') || '100');

    const events = getDiscordEvents(limit);

    return NextResponse.json({
      events,
      count: events.length,
      source: 'discord',
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error('[Discord API] Error fetching events:', error);
    return NextResponse.json(
      { error: 'Failed to fetch Discord events' },
      { status: 500 }
    );
  }
}

/**
 * DELETE /api/events/discord
 * Clear old Discord events
 */
export async function DELETE(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const maxAgeHours = parseInt(searchParams.get('maxAge') || '24');

    const { clearOldDiscordEvents } = await import('@/lib/discord-bot');
    clearOldDiscordEvents(maxAgeHours);

    return NextResponse.json({
      success: true,
      message: `Cleared events older than ${maxAgeHours} hours`,
    });
  } catch (error) {
    console.error('[Discord API] Error clearing events:', error);
    return NextResponse.json(
      { error: 'Failed to clear events' },
      { status: 500 }
    );
  }
}
