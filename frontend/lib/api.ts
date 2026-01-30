/**
 * API Client for OSINT Aggregator Backend
 * Replaces the old Valyu API client
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface Event {
  id: number;
  title?: string;
  raw_content: string;
  category?: string;
  threat_level?: string;
  summary?: string;
  entities?: string[];
  keywords?: string[];
  country?: string;
  location_name?: string;
  latitude?: number;
  longitude?: number;
  event_time?: string;
  collected_at: string;
  processed_at?: string;
  is_processed: boolean;
  source_id: number;
  metadata?: Record<string, any>;
}

export interface EventsResponse {
  events: Event[];
  total: number;
  page: number;
  page_size: number;
}

export interface Stats {
  total_events: number;
  events_by_category: Record<string, number>;
  events_by_threat_level: Record<string, number>;
  events_by_country: Record<string, number>;
  recent_events_count: number;
  active_sources: number;
}

/**
 * Fetch events with optional filters
 */
export async function fetchEvents(params?: {
  page?: number;
  page_size?: number;
  category?: string;
  threat_level?: string;
  country?: string;
  search?: string;
  min_lat?: number;
  min_lon?: number;
  max_lat?: number;
  max_lon?: number;
}): Promise<EventsResponse> {
  const queryParams = new URLSearchParams();

  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        queryParams.append(key, String(value));
      }
    });
  }

  const url = `${API_BASE_URL}/api/events?${queryParams.toString()}`;
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`Failed to fetch events: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Fetch a single event by ID
 */
export async function fetchEvent(id: number): Promise<Event> {
  const response = await fetch(`${API_BASE_URL}/api/events/${id}`);

  if (!response.ok) {
    throw new Error(`Failed to fetch event: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Fetch platform statistics
 */
export async function fetchStats(): Promise<Stats> {
  const response = await fetch(`${API_BASE_URL}/api/stats`);

  if (!response.ok) {
    throw new Error(`Failed to fetch stats: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Create a new event manually
 */
export async function createEvent(event: Partial<Event>): Promise<Event> {
  const response = await fetch(`${API_BASE_URL}/api/events`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(event),
  });

  if (!response.ok) {
    throw new Error(`Failed to create event: ${response.statusText}`);
  }

  return response.json();
}

/**
 * WebSocket connection for real-time events
 */
export function connectToEventStream(
  onMessage: (event: Event) => void,
  onError?: (error: Error) => void
): WebSocket {
  const wsUrl = API_BASE_URL.replace('http://', 'ws://').replace('https://', 'wss://');
  const ws = new WebSocket(`${wsUrl}/ws/events`);

  ws.onmessage = (message) => {
    try {
      const data = JSON.parse(message.data);
      if (data.type === 'event') {
        onMessage(data.event);
      }
    } catch (error) {
      if (onError) {
        onError(error as Error);
      }
    }
  };

  ws.onerror = (error) => {
    if (onError) {
      onError(new Error('WebSocket error'));
    }
  };

  return ws;
}

/**
 * Manually trigger data collection
 */
export async function triggerCollection(): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/admin/collect`, {
    method: 'POST',
  });

  if (!response.ok) {
    throw new Error(`Failed to trigger collection: ${response.statusText}`);
  }
}

/**
 * Manually trigger LLM processing
 */
export async function triggerProcessing(): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/admin/process`, {
    method: 'POST',
  });

  if (!response.ok) {
    throw new Error(`Failed to trigger processing: ${response.statusText}`);
  }
}
