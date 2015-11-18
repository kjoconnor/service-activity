# service-activity

start the service: `baseplate-serve --debug example.ini`

Record an activity
==================

```
python3 -m reddit_service_activity.activity_thrift.remote -h localhost:9090 set_activity <activity> <visitor_id>
```


```
python3 -m reddit_service_activity.activity_thrift.remote -h localhost:9090 set_activity /r/theocho 123
```

Get activity count
==================
```
python3 -m reddit_service_activity.activity_thrift.remote -h localhost:9090 get_activity '/r/theocho'
```
