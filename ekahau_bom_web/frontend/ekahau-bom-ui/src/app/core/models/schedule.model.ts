/**
 * Schedule models for automated batch processing.
 */

export enum TriggerType {
  Cron = 'cron',
  Directory = 'directory',
  S3 = 's3'
}

export enum ScheduleStatus {
  Success = 'success',
  Failed = 'failed',
  Partial = 'partial',
  Running = 'running'
}

export interface TriggerConfig {
  directory?: string;
  s3_bucket?: string;
  s3_prefix?: string;
  batch_template_id?: string;
  pattern?: string;
  recursive?: boolean;
}

export interface NotificationConfig {
  email?: string[];
  webhook_url?: string;
  slack_webhook?: string;
  notify_on_success?: boolean;
  notify_on_failure?: boolean;
  notify_on_partial?: boolean;
}

export interface Schedule {
  schedule_id: string;
  name: string;
  description: string;
  cron_expression: string;
  enabled: boolean;
  trigger_type: TriggerType;
  trigger_config: TriggerConfig;
  notification_config: NotificationConfig;
  next_run_time: string | null;
  last_run_time: string | null;
  last_run_status: ScheduleStatus | null;
  last_batch_id: string | null;
  execution_count: number;
  created_at: string;
  updated_at: string;
  created_by: string;
}

export interface ScheduleListItem {
  schedule_id: string;
  name: string;
  description: string;
  cron_expression: string;
  enabled: boolean;
  trigger_type: TriggerType;
  next_run_time: string | null;
  last_run_time: string | null;
  last_run_status: ScheduleStatus | null;
  execution_count: number;
}

export interface ScheduleRun {
  run_id: string;
  schedule_id: string;
  executed_at: string;
  status: ScheduleStatus;
  batch_id: string | null;
  duration_seconds: number;
  projects_processed: number;
  projects_succeeded: number;
  projects_failed: number;
  error_message: string | null;
  files_found: number;
  files_processed: number;
}

export interface ScheduleCreateRequest {
  name: string;
  description?: string;
  cron_expression: string;
  enabled?: boolean;
  trigger_type: TriggerType;
  trigger_config: TriggerConfig;
  notification_config?: NotificationConfig;
}

export interface ScheduleUpdateRequest {
  name?: string;
  description?: string;
  cron_expression?: string;
  enabled?: boolean;
  trigger_type?: TriggerType;
  trigger_config?: TriggerConfig;
  notification_config?: NotificationConfig;
}

/**
 * Cron expression presets for common schedules.
 */
export const CRON_PRESETS = {
  DAILY_2AM: {
    expression: '0 2 * * *',
    label: 'Daily at 2:00 AM',
    description: 'Runs every day at 2:00 AM UTC'
  },
  WEEKLY_SUNDAY: {
    expression: '0 2 * * 0',
    label: 'Weekly (Sunday 2:00 AM)',
    description: 'Runs every Sunday at 2:00 AM UTC'
  },
  MONTHLY_FIRST: {
    expression: '0 2 1 * *',
    label: 'Monthly (1st day, 2:00 AM)',
    description: 'Runs on the 1st day of each month at 2:00 AM UTC'
  },
  HOURLY: {
    expression: '0 * * * *',
    label: 'Every Hour',
    description: 'Runs at the start of every hour'
  },
  EVERY_6_HOURS: {
    expression: '0 */6 * * *',
    label: 'Every 6 Hours',
    description: 'Runs every 6 hours (00:00, 06:00, 12:00, 18:00)'
  },
  WEEKDAYS_9AM: {
    expression: '0 9 * * 1-5',
    label: 'Weekdays at 9:00 AM',
    description: 'Runs Monday through Friday at 9:00 AM UTC'
  },
  FRIDAY_5PM: {
    expression: '0 17 * * 5',
    label: 'Friday at 5:00 PM',
    description: 'Runs every Friday at 5:00 PM UTC'
  }
} as const;

/**
 * Parse cron expression into human-readable description.
 */
export function parseCronExpression(expression: string): string {
  // Check if it matches a preset
  for (const [, preset] of Object.entries(CRON_PRESETS)) {
    if (preset.expression === expression) {
      return preset.description;
    }
  }

  // Basic parsing for custom expressions
  const parts = expression.split(' ');
  if (parts.length !== 5) {
    return 'Custom schedule';
  }

  const [minute, hour, dayOfMonth, month, dayOfWeek] = parts;

  // Build description
  let desc = 'Runs ';

  // Frequency
  if (dayOfWeek !== '*') {
    const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    if (dayOfWeek.includes(',')) {
      desc += 'on selected days';
    } else if (dayOfWeek.includes('-')) {
      desc += 'on weekdays';
    } else {
      const dayNum = parseInt(dayOfWeek, 10);
      desc += `every ${days[dayNum]}`;
    }
  } else if (dayOfMonth !== '*') {
    desc += `on day ${dayOfMonth} of each month`;
  } else {
    desc += 'every day';
  }

  // Time
  if (hour !== '*' && minute !== '*') {
    const h = parseInt(hour, 10);
    const m = parseInt(minute, 10);
    desc += ` at ${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}`;
  } else if (hour.startsWith('*/')) {
    const interval = hour.substring(2);
    desc += ` every ${interval} hours`;
  }

  desc += ' UTC';

  return desc;
}

/**
 * Validate cron expression format.
 */
export function validateCronExpression(expression: string): { valid: boolean; error?: string } {
  const parts = expression.trim().split(/\s+/);

  if (parts.length !== 5) {
    return {
      valid: false,
      error: 'Cron expression must have exactly 5 fields: minute hour day month weekday'
    };
  }

  // Basic validation for each field
  const [minute, hour, dayOfMonth, month, dayOfWeek] = parts;

  // Minute: 0-59
  if (!isValidCronField(minute, 0, 59) && minute !== '*') {
    return { valid: false, error: 'Invalid minute field (0-59)' };
  }

  // Hour: 0-23
  if (!isValidCronField(hour, 0, 23) && hour !== '*') {
    return { valid: false, error: 'Invalid hour field (0-23)' };
  }

  // Day of month: 1-31
  if (!isValidCronField(dayOfMonth, 1, 31) && dayOfMonth !== '*') {
    return { valid: false, error: 'Invalid day of month field (1-31)' };
  }

  // Month: 1-12
  if (!isValidCronField(month, 1, 12) && month !== '*') {
    return { valid: false, error: 'Invalid month field (1-12)' };
  }

  // Day of week: 0-6 (0=Sunday)
  if (!isValidCronField(dayOfWeek, 0, 6) && dayOfWeek !== '*') {
    return { valid: false, error: 'Invalid day of week field (0-6, 0=Sunday)' };
  }

  return { valid: true };
}

function isValidCronField(field: string, min: number, max: number): boolean {
  // Single value
  if (/^\d+$/.test(field)) {
    const num = parseInt(field, 10);
    return num >= min && num <= max;
  }

  // Range (e.g., 1-5)
  if (/^\d+-\d+$/.test(field)) {
    const [start, end] = field.split('-').map(n => parseInt(n, 10));
    return start >= min && end <= max && start < end;
  }

  // Step (e.g., */5)
  if (/^\*\/\d+$/.test(field)) {
    const step = parseInt(field.substring(2), 10);
    return step > 0 && step <= max;
  }

  // List (e.g., 1,3,5)
  if (/^\d+(,\d+)+$/.test(field)) {
    const nums = field.split(',').map(n => parseInt(n, 10));
    return nums.every(n => n >= min && n <= max);
  }

  return false;
}

/**
 * Get status badge color for schedule status.
 */
export function getStatusColor(status: ScheduleStatus | null): string {
  switch (status) {
    case ScheduleStatus.Success:
      return 'success';
    case ScheduleStatus.Failed:
      return 'error';
    case ScheduleStatus.Partial:
      return 'warning';
    case ScheduleStatus.Running:
      return 'info';
    default:
      return 'neutral';
  }
}

/**
 * Get status icon for schedule status.
 */
export function getStatusIcon(status: ScheduleStatus | null): string {
  switch (status) {
    case ScheduleStatus.Success:
      return 'check-circle';
    case ScheduleStatus.Failed:
      return 'x-circle';
    case ScheduleStatus.Partial:
      return 'alert-triangle';
    case ScheduleStatus.Running:
      return 'loader';
    default:
      return 'help-circle';
  }
}
