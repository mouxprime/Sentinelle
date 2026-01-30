import { Client, GatewayIntentBits, Message, TextChannel } from 'discord.js';
import { classifyEventWithLocalLLM } from './lm-studio-classifier';
import { generateEventId } from './utils';
import type { ThreatEvent } from '@/types';

// Configuration
const DISCORD_TOKEN = process.env.DISCORD_BOT_TOKEN!;
const MONITORED_CHANNELS = process.env.DISCORD_CHANNEL_IDS?.split(',') || [];

// Store events in memory (or use Redis/DB for production)
export const discordEvents: ThreatEvent[] = [];

// Extract tweet text from Discord message
function extractTweetContent(message: Message): string | null {
  const content = message.content;

  // Pattern 1: Direct tweet link with quoted text
  const tweetQuoteMatch = content.match(/https:\/\/(?:twitter|x)\.com\/\w+\/status\/\d+[\s\n]+"([^"]+)"/s);
  if (tweetQuoteMatch) return tweetQuoteMatch[1];

  // Pattern 2: Embedded tweet (Discord shows preview)
  if (message.embeds.length > 0) {
    const embed = message.embeds[0];
    if (embed.url?.includes('twitter.com') || embed.url?.includes('x.com')) {
      return embed.description || embed.title || null;
    }
  }

  // Pattern 3: Tweet link + text below
  const lines = content.split('\n');
  const hasTweetLink = lines.some(line =>
    line.includes('twitter.com/') || line.includes('x.com/')
  );

  if (hasTweetLink) {
    const textLines = lines.filter(line =>
      !line.includes('http') && line.trim().length > 20
    );
    return textLines.join('\n') || null;
  }

  // Pattern 4: Plain text (no link, just content)
  if (content.length > 50 && !content.startsWith('http')) {
    return content;
  }

  return null;
}

// Extract tweet URL from message
function extractTweetUrl(message: Message): string | null {
  const urlMatch = message.content.match(/(https:\/\/(?:twitter|x)\.com\/\w+\/status\/\d+)/);
  return urlMatch ? urlMatch[1] : null;
}

// Process incoming Discord message
async function processDiscordMessage(message: Message): Promise<void> {
  // Ignore bot messages
  if (message.author.bot) return;

  // Check if channel is monitored
  if (MONITORED_CHANNELS.length > 0 && !MONITORED_CHANNELS.includes(message.channel.id)) {
    return;
  }

  const tweetContent = extractTweetContent(message);
  if (!tweetContent) {
    console.log('[Discord Bot] No tweet content found in message:', message.id);
    return;
  }

  console.log('[Discord Bot] Processing tweet:', tweetContent.slice(0, 100));

  try {
    // Classify with local LLM (LM Studio)
    const classification = await classifyEventWithLocalLLM(
      tweetContent.slice(0, 150), // title
      tweetContent // full content
    );

    if (!classification.location) {
      console.log('[Discord Bot] No location found, skipping');
      return;
    }

    const event: ThreatEvent = {
      id: generateEventId(),
      title: tweetContent.slice(0, 150),
      summary: tweetContent.slice(0, 500),
      category: classification.category,
      threatLevel: classification.threatLevel,
      location: classification.location,
      timestamp: message.createdAt.toISOString(),
      source: `Discord: ${(message.channel as TextChannel).name}`,
      sourceUrl: extractTweetUrl(message) || message.url,
      entities: classification.entities || [],
      keywords: classification.keywords || [],
      rawContent: tweetContent,
    };

    // Store event
    discordEvents.unshift(event);

    // Keep only last 500 events
    if (discordEvents.length > 500) {
      discordEvents.pop();
    }

    console.log('[Discord Bot] Event created:', event.id, event.title.slice(0, 50));

    // Optional: React to message to confirm processing
    await message.react('✅');
  } catch (error) {
    console.error('[Discord Bot] Error processing message:', error);
    await message.react('❌');
  }
}

// Initialize Discord bot
export async function startDiscordBot(): Promise<Client> {
  const client = new Client({
    intents: [
      GatewayIntentBits.Guilds,
      GatewayIntentBits.GuildMessages,
      GatewayIntentBits.MessageContent,
    ],
  });

  client.on('ready', () => {
    console.log(`[Discord Bot] Logged in as ${client.user?.tag}`);
    console.log(`[Discord Bot] Monitoring channels:`, MONITORED_CHANNELS);
  });

  client.on('messageCreate', async (message) => {
    await processDiscordMessage(message);
  });

  client.on('error', (error) => {
    console.error('[Discord Bot] Error:', error);
  });

  await client.login(DISCORD_TOKEN);

  return client;
}

// Get recent events from Discord
export function getDiscordEvents(limit: number = 100): ThreatEvent[] {
  return discordEvents.slice(0, limit);
}

// Clear old events (run periodically)
export function clearOldDiscordEvents(maxAgeHours: number = 24): void {
  const cutoff = Date.now() - maxAgeHours * 60 * 60 * 1000;
  const before = discordEvents.length;

  for (let i = discordEvents.length - 1; i >= 0; i--) {
    if (new Date(discordEvents[i].timestamp).getTime() < cutoff) {
      discordEvents.splice(i, 1);
    }
  }

  console.log(`[Discord Bot] Cleaned ${before - discordEvents.length} old events`);
}
