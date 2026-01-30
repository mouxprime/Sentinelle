/**
 * Discord User Account Reader (Safe Mode)
 *
 * ⚠️ IMPORTANT SAFETY NOTES:
 *
 * 1. Use a SECONDARY Discord account (not your main one)
 * 2. This is READ-ONLY - no messages, no reactions, no automated actions
 * 3. Behave like a normal user who reads channels manually
 * 4. Add delays between requests to avoid detection
 * 5. Discord ToS technically prohibits automation, use at your own risk
 *
 * SAFEST APPROACH:
 * - Create a free secondary Discord account
 * - Join the server normally (ask server members for invite)
 * - Use this account ONLY for reading, never automate actions
 */

import { Client, GatewayIntentBits, Message, TextChannel } from 'discord.js';
import { classifyEventWithLocalLLM } from './lm-studio-classifier';
import { generateEventId } from './utils';
import type { ThreatEvent } from '@/types';

const USER_TOKEN = process.env.DISCORD_USER_TOKEN!;
const MONITORED_CHANNELS = process.env.DISCORD_CHANNEL_IDS?.split(',') || [];

// Safety: Rate limiting to appear human-like
const PROCESSING_DELAY = 5000; // 5 seconds between processing messages
const MAX_MESSAGES_PER_HOUR = 100; // Don't process more than 100 msgs/hour

export const userDiscordEvents: ThreatEvent[] = [];
let messagesProcessedThisHour = 0;
let lastProcessingTime = Date.now();

// Reset counter every hour
setInterval(() => {
  messagesProcessedThisHour = 0;
}, 60 * 60 * 1000);

// Human-like delay
function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// Extract tweet content (same as bot version)
function extractTweetContent(message: Message): string | null {
  const content = message.content;

  const tweetQuoteMatch = content.match(/https:\/\/(?:twitter|x)\.com\/\w+\/status\/\d+[\s\n]+"([^"]+)"/s);
  if (tweetQuoteMatch) return tweetQuoteMatch[1];

  if (message.embeds.length > 0) {
    const embed = message.embeds[0];
    if (embed.url?.includes('twitter.com') || embed.url?.includes('x.com')) {
      return embed.description || embed.title || null;
    }
  }

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

  if (content.length > 50 && !content.startsWith('http')) {
    return content;
  }

  return null;
}

function extractTweetUrl(message: Message): string | null {
  const urlMatch = message.content.match(/(https:\/\/(?:twitter|x)\.com\/\w+\/status\/\d+)/);
  return urlMatch ? urlMatch[1] : null;
}

// Process message with safety checks
async function processMessageSafely(message: Message): Promise<void> {
  // Safety: Don't process our own messages
  if (message.author.id === message.client.user?.id) return;

  // Safety: Check rate limit
  if (messagesProcessedThisHour >= MAX_MESSAGES_PER_HOUR) {
    console.log('[Discord Reader] Rate limit reached, skipping message');
    return;
  }

  // Safety: Check if channel is monitored
  if (MONITORED_CHANNELS.length > 0 && !MONITORED_CHANNELS.includes(message.channel.id)) {
    return;
  }

  // Safety: Human-like delay between processing
  const timeSinceLastProcessing = Date.now() - lastProcessingTime;
  if (timeSinceLastProcessing < PROCESSING_DELAY) {
    const waitTime = PROCESSING_DELAY - timeSinceLastProcessing;
    await sleep(waitTime);
  }

  const tweetContent = extractTweetContent(message);
  if (!tweetContent) return;

  console.log('[Discord Reader] Processing message (read-only mode)');

  try {
    const classification = await classifyEventWithLocalLLM(
      tweetContent.slice(0, 150),
      tweetContent
    );

    if (!classification.location) {
      console.log('[Discord Reader] No location found, skipping');
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

    userDiscordEvents.unshift(event);

    if (userDiscordEvents.length > 500) {
      userDiscordEvents.pop();
    }

    messagesProcessedThisHour++;
    lastProcessingTime = Date.now();

    console.log('[Discord Reader] Event created:', event.id);

    // ⚠️ NO REACTIONS - This would be automating actions and could trigger detection
    // await message.react('✅'); // DISABLED FOR SAFETY

  } catch (error) {
    console.error('[Discord Reader] Error processing message:', error);
  }
}

// Start user account reader (safe mode)
export async function startDiscordUserReader(): Promise<Client> {
  const client = new Client({
    intents: [
      GatewayIntentBits.Guilds,
      GatewayIntentBits.GuildMessages,
      GatewayIntentBits.MessageContent,
    ],
  });

  client.on('ready', () => {
    console.log(`[Discord Reader] Connected as ${client.user?.tag}`);
    console.log(`[Discord Reader] READ-ONLY MODE - No automated actions`);
    console.log(`[Discord Reader] Monitoring channels:`, MONITORED_CHANNELS);
    console.log(`[Discord Reader] Rate limit: ${MAX_MESSAGES_PER_HOUR} messages/hour`);
  });

  // Only listen to new messages (don't fetch history to avoid suspicion)
  client.on('messageCreate', async (message) => {
    await processMessageSafely(message);
  });

  client.on('error', (error) => {
    console.error('[Discord Reader] Error:', error);
  });

  // Login with user token (not bot token)
  await client.login(USER_TOKEN);

  return client;
}

// Get events from user reader
export function getUserDiscordEvents(limit: number = 100): ThreatEvent[] {
  return userDiscordEvents.slice(0, limit);
}

// Clear old events
export function clearOldUserDiscordEvents(maxAgeHours: number = 24): void {
  const cutoff = Date.now() - maxAgeHours * 60 * 60 * 1000;
  const before = userDiscordEvents.length;

  for (let i = userDiscordEvents.length - 1; i >= 0; i--) {
    if (new Date(userDiscordEvents[i].timestamp).getTime() < cutoff) {
      userDiscordEvents.splice(i, 1);
    }
  }

  console.log(`[Discord Reader] Cleaned ${before - userDiscordEvents.length} old events`);
}

/**
 * SAFETY CHECKLIST:
 *
 * ✅ Use secondary Discord account (not your main)
 * ✅ Read-only mode (no reactions, no messages)
 * ✅ Human-like delays (5 seconds between processing)
 * ✅ Rate limiting (100 messages/hour max)
 * ✅ No message history fetching
 * ✅ Only process new messages as they arrive
 * ✅ Minimal API calls
 *
 * ⚠️ STILL RISKY:
 * - Discord ToS prohibits automated user accounts
 * - Use at your own risk
 * - Consider asking server admin to add a proper bot instead
 */
