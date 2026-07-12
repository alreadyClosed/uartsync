# UARTSYNC
### A tool made to enumerate UART speeds

## How to use:

git clone it & cd in the working directory

```
git clone https://github.com/alreadyClosed/uartsync.git
cd uartsync
```

then install it (as of right now only install-system works for kali support)
```
make install-system
```
And help will list how it works and the arguments avaliable

```
uartsync --help
```
Output:
```
usage: uartsync [-h] [--rates RATES] [--repeat REPEAT] [--timeout TIMEOUT] [--min-bytes MIN_BYTES]
                [--probe-timeout PROBE_TIMEOUT] [--capture-timeout CAPTURE_TIMEOUT] [--retries RETRIES]
                [--retry-delay RETRY_DELAY] [--settle-ms SETTLE_MS] [--threshold THRESHOLD] [--verbose] [--apply]
                [--list]
                [device]

Automatic UART baud rate detection tool

positional arguments:
  device                Serial device path, e.g. /dev/ttyUSB0. If omitted, waits for a new tty node to appear

options:
  -h, --help            show this help message and exit
  --rates RATES         Comma separated list of baud rates to test, or 'all'
  --repeat REPEAT       Number of scan cycles to run
  --timeout TIMEOUT     Hard ceiling in seconds, counted from device detection
  --min-bytes MIN_BYTES
                        Bytes to collect per rate before scoring
  --probe-timeout PROBE_TIMEOUT
                        Milliseconds to wait for any byte activity before marking a rate silent
  --capture-timeout CAPTURE_TIMEOUT
                        Milliseconds ceiling to fill min-bytes once activity is detected
  --retries RETRIES     Retries on device open failure
  --retry-delay RETRY_DELAY
                        Milliseconds between open retries
  --settle-ms SETTLE_MS
                        Delay after setting baud rate before reading
  --threshold THRESHOLD
                        Score threshold for a rate to count as a hit
  --verbose             Show per rate score breakdown
  --apply               Launch an interactive session at the winning rate
  --list                List currently available serial devices and exit

```

##### Expected use: plug the USB-TO-TTL in your device and run the script, it will wait for the specified device (or grab the first one that appears in /dev/ since im not expecting you to plug anything else during use of the tool) and then simply give power to the UART device (PCB, Router whatever)

### To make sure it works as accurately as possible, use many repetitions (only if you know that UART gives off a lot of data) with a big probe-timeout

A good example of the command would be:

```
uartsync /dev/ttyUSB0 --repeat 10 --probe-timeout 1000
```
(probe-timeout is in miliseconds)

or

```
uartsync /dev/ttyUSB0 --repeat 10 --probe-timeout 1000 --min-bytes 10
```

### ⚠️ Warning This isn't very accurate, if UART doesn't give a lot of data for a while, it could be very off. Do not blindly trust the tool without verification. ⚠️

