#!/usr/bin/python
__author__ = 'Markus Bettsteller, markus@bettsteller.de'
import urllib.request
import json
import argparse
import re


class IcingaHost(object):
    def __init__(self, _fqdn, _hostname, _groups, serverfunction, _project, _environment):
        self.fqdn = _fqdn
        self.hostname = _hostname
        self.groups = _groups
        self.serverFunction = serverfunction
        self.project = _project
        self.environment = _environment

    def __get__groups(self):
        return self.__groups

    def __set__groups(self, value):
        if not isinstance(value, list):
            raise TypeError("groups must be a list")
        self.__groups = value

    groups = property(__get__groups, __set__groups)

# parse the commandline args
parser = argparse.ArgumentParser()
parser.add_argument("--graphite", "-g",
                    help="The url to your graphite server for querying.\n Example: --graphite=https://10.12.123.12")
parser.add_argument("--path", "-p",
                    help="The path to the metrics that should be evaluated as hosts.\n Example: --path=collectd.*")
parser.add_argument("--blacklist", "-b",
                    help="egex that you don't want\n Example: -b=\"(localhost+)|(template+)\"\nIf ommited nothing is "
                         "blacklisted")
parser.add_argument("--matchlist", "-m",
                    help="regex that you want\n Example: -m=\"(vm00_dbrent_net+)\"\nIf ommitted everything is matched.")
parser.add_argument("--configpathandname", "-c",
                    help="basename for your configfile\n Example: -c=/etc/icinga2/conf.d/fromGraphite\nWill create two "
                         "files in /etc/incinga2/conf.d: fromGraphiteHosts.conf and fromGraphiteGroups.conf")
args = parser.parse_args()


# graphite server and the path to the data we are looking for is the bare minimum needed
if not (args.graphite and args.path and args.configpathandname):
    parser.error("no arguments for files and / or hosts given")
    exit(1)

# if there is a proxy set by the environment / OS we DO NOT use it!
urllib.request.ProxyHandler({})
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
urllib.request.install_opener(opener)

# assign variables
graphite = args.graphite
path = args.path
configpathandname = args.configpathandname
config = str.split(configpathandname, '/')[-1]
actionURLprefix = graphite + r"/grafana/#/dashboard/script/icinga2.js?server="

# if the optional commandline arguments are not ther make sure they are available as empty string objects
if args.blacklist:
    blacklist = args.blacklist
else:
    blacklist = ""

if args.matchlist:
    matchlist = args.matchlist
else:
    matchlist = ""

# build together the URL for the query
url = "{GRAPHITE}/metrics/find/?query={PATH}&format=treejson".format(GRAPHITE=graphite, PATH=path)

# do the query and get the JSON object
request = urllib.request.Request(url)
response = opener.open(request)
data = json.loads(response.read().decode('utf-8'))

# compile regexes for matches and blacklist
regex_matching = []
try:
    regex_matching = re.compile(matchlist, flags=re.IGNORECASE)
except re.error:
    print("Something is wrong with your regex:" + matchlist + str(re.error.message))

regex_blacklist = []
try:
    regex_blacklist = re.compile(blacklist, flags=re.IGNORECASE)
except re.error:
    print("Something is wrong with your regex:" + blacklist + str(re.error.message))

fqdn_blacklisted = []
fqdn_notMatched = []
fqdn_valid = []

for (fqdn_json) in data:
    fqdn = fqdn_json["text"]

    # if the fqdn is blacklisted we block it and go to the next element
    if blacklist:
        blacklisted = re.search(regex_blacklist, fqdn)
        if blacklisted:
            fqdn_blacklisted.append(blacklisted.string.replace("_", "."))
            continue

    # if the fqdn is matches we put it in our list, else it gos into the not matched list
    matched = re.search(regex_matching, fqdn)
    if matched:
        fqdn_valid.append(matched.string.replace("_", "."))
    else:
        fqdn_notMatched.append(fqdn.replace("_", "."))

# output of blacklisted and not matched host (for logging / user info)
for (fqdn) in fqdn_blacklisted:
    print("Blacklisted: " + fqdn)

for (fqdn) in fqdn_notMatched:
    print("Not matched: " + fqdn)

# get hosts and try to fetch some hostgroups from the hostname
icingaHosts = []
functionmatch = r"([a-zA-Z]*)"
regex_function = re.compile(functionmatch)
for (fqdn) in fqdn_valid:
    hostname = (str.split(fqdn, '.', 1))[0]

    # tryig to guess the project and environment.
    # rule is: functionXXX-project-environment for the hostname
    # else we just throw it in the "fromGraphite" group
    splitted = str.split(hostname, '-')
    project, environment = "", ""
    if len(splitted) == 3:
        functionFound = re.findall(functionmatch, splitted[0])
        if functionFound:
            serverFunction = ""
            for (f) in functionFound:
                if len(f) > 0:
                    serverFunction += f
        if len(serverFunction) < 1:
            serverFunction = "unknownFunction"
        project = splitted[1]
        environment = splitted[2]
        groups = ["fromGraphite", project, environment]
    else:
        groups = ["fromGraphite"]

    host = IcingaHost(_fqdn=fqdn, _hostname=hostname, _groups=groups, _project=project, serverfunction=serverFunction,
                      _environment=environment)
    icingaHosts.append(host)

# get the unique hostgroups
uniqueGroups = []
for (host) in icingaHosts:
    for (group) in host.groups:
        if (not (uniqueGroups.__contains__(group))) and (group is not None):
            uniqueGroups.append(group)

# Create hostgroup list
hostgrouptemplate = """
object HostGroup "{GROUP}" {{
  display_name = "{GROUP}"
}}
"""
hostgroupFile = open(configpathandname + "Groups.conf", 'w')
for (group) in uniqueGroups:
    hostgroupFile.write(hostgrouptemplate.format(GROUP=config + "_" + group))
hostgroupFile.close()

# Create host list
hosttemplate = """
object Host "{HOSTNAME}" {{
  import "generic-host"
  address = "{FQDN}"
  action_url = "{ACTIONURL}"
  vars.os = "Linux"
  vars.generated = "generated"
  vars.project = "{PROJECT}"
  vars.serverFunction = "{FUNCTION}"
  vars.environment = "{ENVIRONMENT}"
  vars.disks["disk"] = {{
  }}
  groups = [{GROUPS}]
}}
"""
hostsFile = open(configpathandname + "Hosts.conf", 'w')
for (host) in icingaHosts:
    groups = ""
    for (group) in host.groups:
        if len(groups) < 1:
            groups += "\"" + config + "_" + group + "\""
        else:
            groups += ",\"" + config + "_" + group + "\""
    hostsFile.write(hosttemplate.format(HOSTNAME=host.hostname, FQDN=host.fqdn, GROUPS=groups,
                                        FUNCTION=host.serverFunction, PROJECT=host.project,
                                        ENVIRONMENT=host.environment,
                                        ACTIONURL=actionURLprefix + host.fqdn.replace(".", "_")))
hostsFile.close()
