import Redis from 'ioredis';

const globalForRedis = global as unknown as { redis: Redis | undefined };

const redisUrl = process.env.REDIS_URL || process.env.CELERY_BROKER_URL || 'redis://localhost:6379/0';

export const redis =
  globalForRedis.redis ||
  new Redis(redisUrl, {
    maxRetriesPerRequest: null,
    enableReadyCheck: false,
  });

if (process.env.NODE_ENV !== 'production') {
  globalForRedis.redis = redis;
}
