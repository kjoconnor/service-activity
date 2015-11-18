include "baseplate.thrift"

struct RandomRedisKey {
	1: required string redis_key;
	2: required string redis_value;
}

struct ActivityCounter {
	1: required bool is_fuzzed;
	2: required i64 activity_counter;
}

service ActivityService extends baseplate.BaseplateService {
	RandomRedisKey random_key(),
	ActivityCounter get_activity(1: string activity),
	oneway void set_activity(
		1: string activity,
		2: string visitor_id,
	),
}
