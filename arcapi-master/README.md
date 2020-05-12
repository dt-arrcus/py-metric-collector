# ArcOS ArcAPI Python Library

The Arrcus ArcAPI Python Library provides a set of client APIs that are capable
of interacting with the ArcOS management plane independent of the underlying
protocol/transport and agnostic to execution location (local/remote).

## Requirements

ArcAPI is bundled with ArcOS starting in v4.1.1.  However, you can run ArcAPI on a remote device as well.  Below are the installation instructions for that.

The ArcAPI Python libraries have a few dependencies depending on which features
may be of importance to the client.

| Component  | Minimum Version |
|------------|-----------------|
| setuptools | 0.6             |
| paramiko   | 1.15.0          |
| lxml       | 3.3.0           |
| pexpect    | 3.2.0           |



## Installation

Currently 2 installation methods are provided for the Python ArcAPI libraries

* Native python setuptools
* Debian package

Depending on where the libraries are to be installed will dictate the
appropriate installation approach.

For ArcOS or Debian/Ubuntu installations, the recommended approach is to
install the Debian package and fulfill the python-lxml dependency either via
distro package management or manually.  Use of Python's pip is not currently
supported as dependencies could result in further compilation requiring the use
of gcc which is not shipped on ArcOS platforms.

**Note: If coming from any previous pre-release version, you must uninstall
that version prior to installation of the current version**

```
root@r1:~# dpkg -i python-arcapi_0.0.0_all.deb
Selecting previously unselected package python-arcapi.
(Reading database ... 218445 files and directories currently installed.)
Preparing to unpack python-arcapi_0.0.0_all.deb ...
Unpacking python-arcapi (0.0.0) ...
Setting up python-arcapi (0.0.0) ...
```

**Note: examples will be installed to `/usr/share/arcapi`**

For installation on other systems, execute the following:

```
$ sudo python setup.py install
```

## Features

While the libraries are built to be protocol/transport agnostic, version 0.0.0
is limited to the `CLI` Handler method only.  This effectively means that all
interaction is automated through the ArcOS CLI and not alternate northbound
interfaces such as NETCONF or RESTCONF.

### Connection manager

The connection `manager` implements the `connect` function which is responsible
for passing parameters to and returning the appropriate `Handler`

### Connection handler

The connection `Handler` implements the following functions:

* command()
* execute()
* get_config()
* load_config()

#### command

`command()` takes in a string command and can be executed within the context of
the ArcOS cli (default) or the underlying bash shell (if `shell=True`).  For
ArcOS CLI based commands, an `encoding` argument can be passed in that is
either xml or json.

Example:
```
result = manager.command(command='show version', encoding=Encoding.XML, cli=True)
```

#### execute

`execute()` takes in a python list of sequential commands to be run.  The
intention is that this is used primarily for configuration purposes and can
only be ran within the context of the ArcOS CLI (e.g. `cli=True`)

Example:
```
config = ['config', 'no int swp10', 'no int swp11', 'commit', 'end']
result = manager.execute(config, cli=True)
```

#### get_config

`get_config()` takes an encoding argument that is either xml or json and can
only be executed within the context of the ArcOS cli

Example:
```
result = manager.get_config(encoding=Encoding.JSON, cli=True)
```

#### load_config

`load_config()` takes a filename argument along with a `load_operation` and can
only be executed within the context of the ArcOS cli.  A load_operation can be
one of (FEED, MERGE, OVERRIDE, REPLACE).  LoadOperation.FEED is only for input
files where the configuration is using CLI syntax as is processed in an
interactive fashion.

Example:
```
result = manager.load_config(filename='r1.conf', load_operation=LoadOperation.FEED, cli=True)
```

## Examples

There are a variety of client [examples](examples/) utilizing both local or
remote connections to the network element.

Some examples are illustrated below:

### Remote
```
$ ./show_command.py --host r1 --user root --cli
Enter Password:

version product-name UNKNOWN
version serial-num UNKNOWN
version mac-addr UNKNOWN
version form-factor UNKNOWN
version num-cpu-cores 2
version cpu-info "Intel Core Processor (Skylake, IBRS)"
version total-memory "4041860 kB"
version sw-version 3.2.1.EFT3
version dependencies dependency
PACKAGE            VERSION
-------------------------------------
python             2.7.9-1
python-yaml        3.11-2
python-prctl       1.1.1-1.1
protobuf           3.2.0
protobuf-go        0.1.arrcus
libevent-2.0-5     2.0.22-stable-1
libjansson4        2.10
libdict            0.3.0
libzmq5            4.2.5.arrcus1
librdkafka1        0.11.0.arrcus1
liblttng-ust0      2.10.0-1~arrcus1
libnl-3-200        3.3.0.arcos1
libnl-cli-3-200    3.3.0.arcos1
libnl-genl-3-200   3.3.0.arcos1
libnl-idiag-3-200  3.3.0.arcos1
libnl-nf-3-200     3.3.0.arcos1
libnl-route-3-200  3.3.0.arcos1
libnl-utils        3.3.0.arcos1
bcmsdk             6.5.12
libcurl3           7.38.0-4+deb8u8
libgtop2-7         2.28.5-2+b1
lldpd              0.9.6.arrcus0
confd              6.6.3-1
libssl1.0.0        1.0.1t-1+deb8u9
libhiredis0.13     0.13.3-2.2
redis-server       3:3.2.8-2~bpo8+1
librtr0            0.6.0
libcre2            0.3.5
libre2-4           20180901+arrcus
python-oom         0.5.arrcus1
python-lzma        0.5.3-2+b1
```
```
$ ./show_command.py --host r1 --user root --cli --xml
Enter Password:

<config xmlns="http://tail-f.com/ns/config/1.0">
  <version xmlns="http://arrcus.com/ns/arrcus-version">
    <product-name>UNKNOWN</product-name>
    <serial-num>UNKNOWN</serial-num>
    <mac-addr>UNKNOWN</mac-addr>
    <form-factor>UNKNOWN</form-factor>
    <num-cpu-cores>2</num-cpu-cores>
    <cpu-info>Intel Core Processor (Skylake, IBRS)</cpu-info>
    <total-memory>4041860 kB</total-memory>
    <sw-version>3.2.1.EFT3</sw-version>
    <dependencies>
      <dependency>
        <package>python</package>
        <version>2.7.9-1</version>
      </dependency>
      <dependency>
        <package>python-yaml</package>
        <version>3.11-2</version>
      </dependency>
      ... (omitted for brevity)
```

```
$ ./show_command.py --host r1 --user root --cli --json
Enter Password:

{
  "data": {
    "arrcus-version:version": {
      "product-name": "UNKNOWN",
      "serial-num": "UNKNOWN",
      "mac-addr": "UNKNOWN",
      "form-factor": "UNKNOWN",
      "num-cpu-cores": 2,
      "cpu-info": "Intel Core Processor (Skylake, IBRS)",
      "total-memory": "4041860 kB",
      "sw-version": "3.2.1.EFT3",
      "dependencies": {
        "dependency": [
          {
            "package": "python",
            "version": "2.7.9-1"
          },
      ... (omitted for brevity)
```

```
$ ./show_command_parse.py --host r1 --user root --cli --xml
Enter Password:
Interface       Description                         Admin Status    Oper Status
-------------------------------------------------------------------------------------
loopback0                                           UP              UP
ma1                                                 UP              UP
swp6            Connection to r2                    UP              UP
swp7                                                UP              UP
```

### Local
```
root@r1:/usr/share/arcapi/examples/local/cli# ./get_config_parse.py --json
Login Banner: ARCOS (c) Arrcus, Inc.
```

```
root@r1:/usr/share/arcapi/examples/local/cli# ./load_config.py --filename ../../configs/interfaces.conf
Message: Commit Successful
```

```
root@r1:/usr/share/arcapi/examples/local/cli# ./show_command_parse.py --json
Interface       Description                         Admin Status    Oper Status
-------------------------------------------------------------------------------------
loopback0                                           UP              UP
ma1                                                 UP              UP
swp6            Connection to r2                    UP              UP
swp7                                                UP              UP
swp10           N/A                                 N/A             N/A
swp11           N/A                                 N/A             N/A
swp12           N/A                                 N/A             N/A
swp13           N/A                                 N/A             N/A
```
