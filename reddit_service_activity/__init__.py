import logging
import math
import random
import time

import redis

from baseplate import make_metrics_client, config, diagnostics
from baseplate.integration.thrift import BaseplateProcessorEventHandler

from .activity_thrift import ActivityService
from .activity_thrift.ttypes import ActivityCounter, RandomRedisKey

logger = logging.getLogger(__name__)


class Handler(ActivityService.ContextIface):
    key_format = '{activity}/{slice:d}'
    slice_length = 60

    def __init__(self, redis_endpoint, activity_window, fuzz_threshold):
        redis_host, redis_port = redis_endpoint.split(':')
        self.redis = redis.StrictRedis(
            host=redis_host,
            port=redis_port,
        )

        # This is backwards from spladug's example, is that right?
        self.slice_count, remainder = divmod(
            self.slice_length,
            activity_window,
        )

        self.fuzz_threshold = fuzz_threshold

        assert remainder == 0

    @classmethod
    def _current_slice(cls):
        return int(time.time() // cls.slice_length)

    @classmethod
    def _make_key(cls, activity, slice=None, offset=0):
        if slice is None:
            slice = cls._current_slice()
        slice += offset

        return cls.key_format.format(
            activity=activity,
            slice=slice
        )

    def record_activity(self, activity, visitor_id):
        key = self._make_key(activity)
        self.redis.execute_command('PFADD', key, visitor_id)
        # self.redis.execute_command('INCR', key)

    def count_active_visitors(self, activity):
        slice = self._current_slice()
        keys = [
            self._make_key(activity, slice, -i)
            for i in range(self.slice_count)  # is xrange just range on py3?
        ]

        return self.redis.execute_command('PFCOUNT', *keys)
        # key_vals = self.redis.execute_command('MGET', *keys)
        # return sum([int(x) for x in key_vals if x is not None])

    @staticmethod
    def fuzz_activity(count, threshold):
        if count >= threshold:
            return count, False

        decay = math.exp(float(-count) / 60)
        jitter = round(5 * decay)
        return count + random.randint(0, jitter), True

    def is_healthy(self, context):
        # TODO: check that your service has everything it needs to to function
        try:
            self.redis.ping()
        # Might want to switch to something more specific here
        except redis.exceptions.RedisError:
            return False

        return True

    def random_key(self, context):
        random_key = random.randint(0, 10000)
        logging.info(
            'random_key: {random_key}'.format(random_key=random_key)
        )
        random_value = random.randint(0, 10000)
        logging.info(
            'random_value: {random_value}'.format(random_value=random_value)
        )
        self.redis.set(random_key, random_value)
        return RandomRedisKey(
            redis_key=str(random_key),
            redis_value=str(self.redis.get(random_key)),
        )

    def get_activity(self, context, activity):
        active_visitors = self.count_active_visitors(activity)
        safe_count, is_fuzzed = self.fuzz_activity(
            active_visitors,
            self.fuzz_threshold
        )
        return ActivityCounter(
            is_fuzzed=is_fuzzed,
            activity_counter=safe_count,
        )

    def set_activity(self, context, activity, visitor_id):
        self.record_activity(
            activity=activity,
            visitor_id=visitor_id,
        )


def make_processor(app_config):
    cfg = config.parse_config(app_config, {
        'redis_endpoint': config.String,
        'fuzz_threshold': config.Integer,
        'activity_window': config.Integer,
    })

    metrics_client = make_metrics_client(app_config)

    agent = diagnostics.DiagnosticsAgent()
    agent.register(diagnostics.LoggingDiagnosticsObserver())
    agent.register(diagnostics.MetricsDiagnosticsObserver(metrics_client))

    handler = Handler(
        redis_endpoint=cfg.redis_endpoint,
        fuzz_threshold=cfg.fuzz_threshold,
        activity_window=cfg.activity_window,
    )
    processor = ActivityService.ContextProcessor(handler)
    event_handler = BaseplateProcessorEventHandler(logger, agent)
    processor.setEventHandler(event_handler)

    return processor
