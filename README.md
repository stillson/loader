# loader
a basic load network load generator

# usage

```
usage: loader.py [-h] [-o HOST] [-p PORT] [-z] [-s] [-t TARGET] [-f FILE]

optional arguments:
  -h, --help            show this help message and exit
  -o HOST, --host HOST
  -p PORT, --port PORT
  -z, --zip
  -s, --ssl
  -t TARGET, --target TARGET
  -f FILE, --file FILE
```

Very rough load generating tool. Uses feedback to alter delay times 
sent to child load generating processes. Could be easily adapted to
do almost any kind of load generation.